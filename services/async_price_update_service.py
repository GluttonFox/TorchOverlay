"""异步价格更新服务 - 异步执行价格更新以避免阻塞UI"""
import json
import os
import time
import threading
from typing import Optional, Callable
from datetime import datetime
from enum import Enum

from core.logger import get_logger

logger = get_logger(__name__)


class UpdateStatus(Enum):
    """更新状态"""
    IDLE = "idle"  # 空闲
    UPDATING = "updating"  # 更新中
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class AsyncPriceUpdateService:
    """异步价格更新服务

    在后台线程中异步执行价格更新，避免阻塞UI线程。
    支持回调通知和进度查询。
    """

    def __init__(
        self,
        api_url: str = "https://serverp.furtorch.heili.tech/price",
        update_interval_hours: float = 1.0,
        config_path: str = None,
        log_file: str = None
    ):
        """初始化异步价格更新服务

        Args:
            api_url: 价格API地址
            update_interval_hours: 更新间隔（小时）
            config_path: 配置文件路径
            log_file: 日志文件路径
        """
        self._api_url = api_url
        self._update_interval_hours = update_interval_hours
        self._config_path = config_path
        self._log_file = log_file or os.path.join(
            os.path.dirname(__file__), '..', 'price_update.log'
        )

        # 上次更新时间
        self._last_update_time: Optional[datetime] = None
        self._load_last_update_time()

        # 更新状态
        self._status = UpdateStatus.IDLE
        self._status_lock = threading.Lock()

        # 更新结果
        self._last_result: Optional[tuple[bool, str]] = None

        # 更新线程
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # 回调函数
        self._on_start_callback: Optional[Callable[[], None]] = None
        self._on_complete_callback: Optional[Callable[[bool, str], None]] = None
        self._on_error_callback: Optional[Callable[[Exception], None]] = None

        # 统计信息
        self._stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'cancelled_updates': 0,
            'total_items_updated': 0
        }

    def update_prices_async(self, force: bool = False) -> bool:
        """异步更新价格

        Args:
            force: 是否强制更新，忽略时间间隔限制

        Returns:
            是否成功启动更新
        """
        with self._status_lock:
            # 检查是否已经在更新中
            if self._status == UpdateStatus.UPDATING:
                logger.warning("价格更新正在进行中，跳过")
                return False

            # 检查是否可以更新
            if not force and not self._can_update():
                logger.debug("未到更新时间，跳过")
                return False

            # 设置状态
            self._status = UpdateStatus.UPDATING

        # 启动更新线程
        self._stop_event.clear()
        self._update_thread = threading.Thread(
            target=self._update_worker,
            args=(force,),
            daemon=True
        )
        self._update_thread.start()

        logger.info("已启动异步价格更新")
        return True

    def cancel_update(self) -> bool:
        """取消当前更新

        Returns:
            是否成功取消
        """
        with self._status_lock:
            if self._status != UpdateStatus.UPDATING:
                logger.warning("没有正在进行的更新")
                return False

            # 设置停止标志
            self._stop_event.set()
            self._status = UpdateStatus.CANCELLED

        logger.info("已取消价格更新")
        return True

    def get_status(self) -> UpdateStatus:
        """获取更新状态

        Returns:
            更新状态
        """
        with self._status_lock:
            return self._status

    def get_last_result(self) -> Optional[tuple[bool, str]]:
        """获取上次更新结果

        Returns:
            (是否成功, 消息)
        """
        return self._last_result

    def get_last_update_time(self) -> Optional[datetime]:
        """获取上次更新时间

        Returns:
            上次更新时间
        """
        return self._last_update_time

    def is_updating(self) -> bool:
        """检查是否正在更新

        Returns:
            是否正在更新
        """
        return self.get_status() == UpdateStatus.UPDATING

    def can_update(self) -> bool:
        """检查是否可以更新

        Returns:
            是否可以更新
        """
        return self._can_update()

    def set_callbacks(
        self,
        on_start: Optional[Callable[[], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """设置回调函数

        Args:
            on_start: 更新开始时调用
            on_complete: 更新完成时调用，参数为 (是否成功, 消息)
            on_error: 更新出错时调用，参数为异常对象
        """
        self._on_start_callback = on_start
        self._on_complete_callback = on_complete
        self._on_error_callback = on_error

    def get_stats(self) -> dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            **self._stats,
            'last_update_time': self._last_update_time.isoformat() if self._last_update_time else None,
            'current_status': self._status.value,
            'success_rate': (
                self._stats['successful_updates'] / self._stats['total_updates'] * 100
                if self._stats['total_updates'] > 0 else 0.0
            )
        }

    def reset_stats(self) -> None:
        """重置统计信息"""
        self._stats = {
            'total_updates': 0,
            'successful_updates': 0,
            'failed_updates': 0,
            'cancelled_updates': 0,
            'total_items_updated': 0
        }

    def _can_update(self) -> bool:
        """检查是否可以更新

        Returns:
            是否可以更新
        """
        if self._last_update_time is None:
            return True

        hours_since_last_update = (datetime.now() - self._last_update_time).total_seconds() / 3600
        return hours_since_last_update >= self._update_interval_hours

    def _update_worker(self, force: bool) -> None:
        """更新工作线程

        Args:
            force: 是否强制更新
        """
        success = False
        message = ""

        try:
            # 调用开始回调
            if self._on_start_callback:
                try:
                    self._on_start_callback()
                except Exception as e:
                    logger.error(f"开始回调执行失败: {e}")

            # 检查停止标志
            if self._stop_event.is_set():
                self._set_status(UpdateStatus.CANCELLED)
                return

            # 执行更新
            success, message, updated_count = self._do_update()

            # 更新统计信息
            self._stats['total_updates'] += 1
            if success:
                self._stats['successful_updates'] += 1
                self._stats['total_items_updated'] += updated_count
            else:
                self._stats['failed_updates'] += 1

            # 保存更新结果
            self._last_result = (success, message)

            # 调用完成回调
            if self._on_complete_callback:
                try:
                    self._on_complete_callback(success, message)
                except Exception as e:
                    logger.error(f"完成回调执行失败: {e}")

            # 设置状态
            self._set_status(UpdateStatus.SUCCESS if success else UpdateStatus.FAILED)

        except Exception as e:
            logger.error(f"价格更新异常: {e}")
            self._stats['failed_updates'] += 1
            message = f"更新异常: {e}"

            # 调用错误回调
            if self._on_error_callback:
                try:
                    self._on_error_callback(e)
                except Exception as callback_e:
                    logger.error(f"错误回调执行失败: {callback_e}")

            # 保存错误结果
            self._last_result = (False, message)
            self._set_status(UpdateStatus.FAILED)

    def _do_update(self) -> tuple[bool, str, int]:
        """执行价格更新

        Returns:
            (是否成功, 消息, 更新数量)
        """
        try:
            import urllib.request

            self._debug_print(f"正在从 {self._api_url} 获取物价...")

            # 检查停止标志
            if self._stop_event.is_set():
                return False, "更新已取消", 0

            # 发送请求
            request = urllib.request.Request(
                self._api_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))

            # 检查停止标志
            if self._stop_event.is_set():
                return False, "更新已取消", 0

            # API返回的结构是 {"data": {"id": price}}
            if 'data' not in response_data:
                error_msg = "API返回数据格式错误：缺少'data'字段"
                self._debug_print(error_msg)
                return False, error_msg, 0

            data = response_data['data']
            self._debug_print(f"成功获取 {len(data)} 个物品价格")

            # 读取本地 item.json
            item_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')

            # 读取现有数据
            existing_data = {}
            if os.path.exists(item_path):
                with open(item_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # 更新数据
            updated_count = 0
            changed_items = []

            for item_id, api_price in data.items():
                # 检查停止标志
                if self._stop_event.is_set():
                    return False, "更新已取消", 0

                # 跳过初火源质（ID: 100300）
                if item_id == '100300':
                    continue

                if item_id in existing_data:
                    if api_price is not None:
                        old_price = existing_data[item_id].get('Price')

                        # 对比新旧价格
                        if old_price != api_price:
                            existing_data[item_id]['Price'] = api_price
                            updated_count += 1
                            item_name = existing_data[item_id].get('Name', item_id)
                            changed_items.append(f"{item_name}: {old_price} -> {api_price}")
                            self._debug_print(f"  更新: {item_name} {old_price} -> {api_price}")

            # 保存更新后的数据
            with open(item_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

            # 更新最后更新时间
            self._last_update_time = datetime.now()
            self._save_last_update_time()

            self._debug_print(f"成功更新 {updated_count} 个物品价格")

            message = f"成功更新 {updated_count} 个物品价格"

            return True, message, updated_count

        except urllib.error.URLError as e:
            error_msg = f"网络错误: {e}"
            self._debug_print(error_msg)
            return False, error_msg, 0
        except json.JSONDecodeError as e:
            error_msg = f"数据解析错误: {e}"
            self._debug_print(error_msg)
            return False, error_msg, 0
        except Exception as e:
            error_msg = f"更新失败: {e}"
            self._debug_print(error_msg)
            return False, error_msg, 0

    def _set_status(self, status: UpdateStatus) -> None:
        """设置更新状态

        Args:
            status: 新状态
        """
        with self._status_lock:
            self._status = status

    def _debug_print(self, message: str) -> None:
        """调试输出

        Args:
            message: 消息内容
        """
        logger.debug(message)

        # 写入日志文件
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            pass

    def _load_last_update_time(self) -> None:
        """从配置加载上次更新时间"""
        if self._config_path and os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                if 'last_price_update' in config_data and config_data['last_price_update']:
                    self._last_update_time = datetime.fromisoformat(config_data['last_price_update'])
                    self._debug_print(f"已加载上次更新时间: {self._last_update_time.isoformat()}")
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                self._debug_print(f"加载更新时间失败: {e}")
                self._last_update_time = None

    def _save_last_update_time(self) -> None:
        """保存上次更新时间到配置"""
        if self._config_path and self._last_update_time:
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 添加或更新last_price_update字段
                config_data['last_price_update'] = self._last_update_time.isoformat()

                # 保存配置文件
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)

                self._debug_print(f"已保存更新时间到配置文件: {self._last_update_time.isoformat()}")
            except Exception as e:
                logger.error(f"保存更新时间失败: {e}")

    def shutdown(self) -> None:
        """关闭服务"""
        if self.is_updating():
            self.cancel_update()

        # 等待线程结束
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5)

        logger.info("异步价格更新服务已关闭")
