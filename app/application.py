from core.logger import get_logger
from core.thread_pool_manager import ThreadPoolManager
from core.memory_monitor import MemoryMonitor
from app.factories import AppFactory

logger = get_logger(__name__)


class TorchOverlayApplication:
    def __init__(self, enable_memory_monitor: bool = True, enable_thread_pool: bool = True) -> None:
        """初始化应用

        Args:
            enable_memory_monitor: 是否启用内存监控
            enable_thread_pool: 是否启用线程池
        """
        self._factory = AppFactory()
        self._enable_memory_monitor = enable_memory_monitor
        self._enable_thread_pool = enable_thread_pool

        # 管理器引用
        self._memory_monitor: Optional[MemoryMonitor] = None
        self._thread_pool: Optional[ThreadPoolManager] = None

        # 监控服务引用（用于后续启动）
        self._exchange_monitor = None

    def _initialize_managers(self) -> None:
        """初始化管理器"""
        print("=== 初始化管理器 ===")
        print("步骤 1: 检查是否启用线程池...")

        # 初始化线程池
        if self._enable_thread_pool:
            print("  正在创建线程池管理器...")
            self._thread_pool = ThreadPoolManager.get_instance()
            print(f"  ✓ 线程池管理器已创建: {self._thread_pool is not None}")
            logger.info("线程池管理器已启动")
        else:
            print("  - 线程池未启用")

        print("步骤 2: 检查是否启用内存监控...")

        # 初始化内存监控
        if self._enable_memory_monitor:
            print("  正在创建内存监控器...")
            self._memory_monitor = MemoryMonitor.get_instance()
            self._memory_monitor.start()
            print(f"  ✓ 内存监控器已启动: {self._memory_monitor is not None}")
            logger.info("内存监控已启动")
        else:
            print("  - 内存监控未启用")

        print("=== 管理器初始化完成 ===\n")

    def _cleanup_managers(self) -> None:
        """清理管理器"""
        # 停止内存监控
        if self._memory_monitor:
            logger.info("停止内存监控...")
            self._memory_monitor.stop()
            self._memory_monitor = None

        # 关闭线程池
        if self._thread_pool:
            logger.info("关闭线程池...")
            self._thread_pool.shutdown(wait=True)
            self._thread_pool = None

    def run(self) -> None:
        """运行应用"""
        try:
            # 0) 初始化管理器
            self._initialize_managers()

            # 1) 管理员检查与提权
            admin = self._factory.create_admin_service()
            admin.ensure_admin_or_restart()

            # 2) 创建控制器与窗口并运行
            print("=== 创建控制器 ===")
            controller = self._factory.create_controller()
            print("✓ 控制器创建成功")

            # 保存监控服务引用（从控制器中获取）
            self._exchange_monitor = controller._exchange_monitor

            print("=== 创建窗口 ===")
            window = self._factory.create_main_window(controller)
            print("✓ 窗口创建成功")

            # 启动监控服务
            if self._exchange_monitor:
                print("=== 启动监控服务 ===")
                self._exchange_monitor.start()
                print("✓ 监控服务已启动")

            # 附加 UI 并运行
            print("=== 附加 UI ===")
            controller.attach_ui(window)
            print("✓ UI 已附加")

            print("=== 运行窗口 ===")
            window.run()

        except KeyboardInterrupt:
            logger.info("应用被用户中断")
        except Exception as e:
            logger.error(f"应用运行出错: {e}", exc_info=True)
            raise
        finally:
            # 3) 清理管理器
            self._cleanup_managers()
            logger.info("应用已正常退出")
