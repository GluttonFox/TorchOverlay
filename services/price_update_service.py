"""物价更新服务 - 从远程API获取并更新物价"""
import json
import os
import time
from typing import Optional
from datetime import datetime


class PriceUpdateService:
    """物价更新服务"""

    def __init__(self, config=None):
        self._api_url = "https://serverp.furtorch.heili.tech/price"
        self._update_interval_hours = 1.0  # 更新间隔（小时）
        self._last_update_time = None  # 上次更新时间戳
        self._config = config  # 配置对象，用于持久化更新时间
        self._log_file = os.path.join(os.path.dirname(__file__), '..', 'price_update.log')
        self._force_update = False  # 强制更新（调试用）

        # 从配置加载上次更新时间
        self._load_last_update_time()

    def _debug_print(self, *args, **kwargs):
        """调试输出，同时打印到控制台和日志文件"""
        message = ' '.join(str(arg) for arg in args)
        print(message)

        # 写入日志文件
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            pass  # 忽略日志写入错误

    def _load_last_update_time(self):
        """从配置加载上次更新时间"""
        if self._config:
            try:
                # 直接从config.json文件读取
                config_path = self._config.get_config_path()
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)

                    if 'last_price_update' in config_data and config_data['last_price_update']:
                        self._last_update_time = datetime.fromisoformat(config_data['last_price_update'])
                        self._debug_print(f"已加载上次更新时间: {self._last_update_time.isoformat()}")
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                self._debug_print(f"加载更新时间失败: {e}")
                self._last_update_time = None

    def _save_last_update_time(self):
        """保存上次更新时间到配置"""
        if self._config and self._last_update_time:
            try:
                # 直接读取和修改config.json文件
                config_path = self._config.get_config_path()
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)

                # 添加或更新last_price_update字段
                config_data['last_price_update'] = self._last_update_time.isoformat()

                # 保存配置文件
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)

                self._debug_print(f"已保存更新时间到配置文件: {self._last_update_time.isoformat()}")
            except Exception as e:
                print(f"保存更新时间失败: {e}")

    def get_last_update_time(self) -> Optional[datetime]:
        """获取上次更新时间"""
        return self._last_update_time

    def can_update(self) -> bool:
        """检查是否可以更新（暂时不限制，后续改为1小时限制）"""
        # 暂时不限制更新频率
        return True

        # 后续启用以下代码来限制更新频率
        # if self._last_update_time is None:
        #     return True
        # hours_since_last_update = (datetime.now() - self._last_update_time).total_seconds() / 3600
        # return hours_since_last_update >= self._update_interval_hours

    def update_prices(self) -> tuple[bool, str]:
        """从API更新物价

        Returns:
            (是否成功, 消息)
        """
        try:
            import urllib.request

            self._debug_print(f"正在从 {self._api_url} 获取物价...")

            # 发送请求
            request = urllib.request.Request(
                self._api_url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )

            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = json.loads(response.read().decode('utf-8'))

            # API返回的结构是 {"data": {"id": price}}
            # 需要解析出价格数据
            if 'data' not in response_data:
                error_msg = "API返回数据格式错误：缺少'data'字段"
                self._debug_print(error_msg)
                return False, error_msg

            data = response_data['data']
            self._debug_print(f"成功获取 {len(data)} 个物品价格")

            # 显示前5个物品（用于调试）
            first_5 = list(data.items())[:5]
            self._debug_print(f"前5个物品: {first_5}")

            # 读取本地 item.json
            item_path = os.path.join(os.path.dirname(__file__), '..', 'item.json')

            # 读取现有数据
            existing_data = {}
            if os.path.exists(item_path):
                with open(item_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # 更新数据（只更新价格有变化的物品）
            updated_count = 0
            unchanged_count = 0
            changed_items = []
            not_in_api = []
            no_price_in_api = []

            # 检查10001物品（专门用于调试）
            if '10001' in existing_data:
                self._debug_print(f"[调试] 本地10001价格: {existing_data['10001'].get('Price')} (类型: {type(existing_data['10001'].get('Price')).__name__})")
                if '10001' in data:
                    api_price = data['10001']
                    self._debug_print(f"[调试] API中10001价格: {api_price} (类型: {type(api_price).__name__ if api_price is not None else 'None'})")
                else:
                    self._debug_print(f"[调试] API中没有10001")

            # 强制更新时更新所有在API中的物品
            if self._force_update:
                self._debug_print(f"[调试] 强制更新模式已启用")

            for item_id, api_price in data.items():
                # 跳过初火源质（ID: 100300），其价格固定为1
                if item_id == '100300':
                    continue
                    
                if item_id in existing_data:
                    # API数据结构是 {id: price}，price是数字，不是对象
                    if api_price is not None:
                        old_price = existing_data[item_id].get('Price')

                        # 对比新旧价格（强制更新时跳过对比）
                        if self._force_update or old_price != api_price:
                            existing_data[item_id]['Price'] = api_price
                            updated_count += 1
                            item_name = existing_data[item_id].get('Name', item_id)
                            changed_items.append(f"{item_name}: {old_price} -> {api_price}")
                            self._debug_print(f"  更新: {item_name} {old_price} -> {api_price}")
                            if item_id == '10001':
                                self._debug_print(f"  [关键] 10001已更新!")
                        else:
                            unchanged_count += 1
                            if item_id == '10001':
                                self._debug_print(f"  [关键] 10001价格未变化: {old_price} == {api_price}")
                    else:
                        # API中该物品价格为None
                        no_price_in_api.append(item_id)
                else:
                    # API中新增的物品（本地没有）
                    self._debug_print(f"  新增物品: {item_id} 价格: {api_price}")

            # 检查本地有但API中没有的物品
            for item_id in existing_data:
                if item_id not in data:
                    not_in_api.append(item_id)
            if not_in_api:
                self._debug_print(f"本地有但API中没有的物品: {not_in_api[:10]}")  # 只显示前10个

            if no_price_in_api:
                self._debug_print(f"API中无价格的物品: {no_price_in_api[:10]}")

            # 保存更新后的数据
            with open(item_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

            # 更新最后更新时间
            self._last_update_time = datetime.now()
            self._save_last_update_time()

            self._debug_print(f"成功更新 {updated_count} 个物品价格，{unchanged_count} 个未变化")

            # 简化消息，不显示详细物品列表
            message = f"成功更新 {updated_count} 个物品价格"

            return True, message

        except urllib.error.URLError as e:
            error_msg = f"网络错误: {e}"
            self._debug_print(error_msg)
            return False, error_msg
        except json.JSONDecodeError as e:
            error_msg = f"数据解析错误: {e}"
            self._debug_print(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"更新失败: {e}"
            self._debug_print(error_msg)
            return False, error_msg

    def _debug_print(self, *args, **kwargs):
        """调试输出"""
        print(*args, **kwargs)
