from app.factories import AppFactory

class TorchOverlayApplication:
    def __init__(self):
        self._factory = AppFactory()

    def run(self):
        # 1) 管理员检查与提权
        admin = self._factory.create_admin_service()
        admin.ensure_admin_or_restart()

        # 2) 创建控制器与窗口并运行
        controller = self._factory.create_controller()
        window = self._factory.create_main_window(controller)

        controller.attach_ui(window)
        window.run()
