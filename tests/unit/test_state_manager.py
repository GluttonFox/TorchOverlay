"""状态管理器测试"""
import pytest

from core.state_manager import StateManager, AppState, RecognitionState, PriceUpdateState


class TestStateManager:
    """状态管理器测试类"""

    @pytest.fixture
    def state_manager(self):
        """状态管理器fixture"""
        return StateManager()

    def test_initial_state(self, state_manager):
        """测试初始状态"""
        state = state_manager.get_state()
        assert state.recognition_state == RecognitionState.IDLE
        assert state.price_update_state == PriceUpdateState.IDLE
        assert state.ui_window_visible is False
        assert state.config['watch_interval_ms'] == 500
        assert state.config['debug_mode'] is False

    def test_start_recognition(self, state_manager):
        """测试开始识别"""
        state_manager.start_recognition()
        state = state_manager.get_state()
        assert state.recognition_state == RecognitionState.IN_PROGRESS

    def test_complete_recognition_success(self, state_manager):
        """测试识别成功完成"""
        state_manager.start_recognition()
        state_manager.complete_recognition(success=True)

        state = state_manager.get_state()
        assert state.recognition_state == RecognitionState.IDLE

    def test_complete_recognition_failure(self, state_manager):
        """测试识别失败"""
        state_manager.start_recognition()
        state_manager.complete_recognition(success=False, error="识别失败")

        state = state_manager.get_state()
        assert state.recognition_state == RecognitionState.IDLE
        assert state.recognition_error == "识别失败"

    def test_is_recognizing(self, state_manager):
        """测试是否正在识别"""
        assert not state_manager.is_recognizing()

        state_manager.start_recognition()
        assert state_manager.is_recognizing()

        state_manager.complete_recognition(success=True)
        assert not state_manager.is_recognizing()

    def test_get_recognition_state(self, state_manager):
        """测试获取识别状态"""
        assert state_manager.get_recognition_state() == RecognitionState.IDLE

        state_manager.start_recognition()
        assert state_manager.get_recognition_state() == RecognitionState.IN_PROGRESS

    def test_start_price_update(self, state_manager):
        """测试开始价格更新"""
        state_manager.start_price_update()
        state = state_manager.get_state()
        assert state.price_update_state == PriceUpdateState.IN_PROGRESS

    def test_complete_price_update_success(self, state_manager):
        """测试价格更新成功完成"""
        state_manager.start_price_update()
        state_manager.complete_price_update(success=True)

        state = state_manager.get_state()
        assert state.price_update_state == PriceUpdateState.IDLE

    def test_complete_price_update_failure(self, state_manager):
        """测试价格更新失败"""
        state_manager.start_price_update()
        state_manager.complete_price_update(success=False, message="网络错误")

        state = state_manager.get_state()
        assert state.price_update_state == PriceUpdateState.IDLE
        assert state.price_update_message == "网络错误"

    def test_is_updating_price(self, state_manager):
        """测试是否正在更新价格"""
        assert not state_manager.is_updating_price()

        state_manager.start_price_update()
        assert state_manager.is_updating_price()

        state_manager.complete_price_update(success=True)
        assert not state_manager.is_updating_price()

    def test_get_price_update_state(self, state_manager):
        """测试获取价格更新状态"""
        assert state_manager.get_price_update_state() == PriceUpdateState.IDLE

        state_manager.start_price_update()
        assert state_manager.get_price_update_state() == PriceUpdateState.IN_PROGRESS

    def test_set_ui_window_visible(self, state_manager):
        """测试设置UI窗口可见性"""
        assert not state_manager.get_state().ui_window_visible

        state_manager.set_ui_window_visible(True)
        assert state_manager.get_state().ui_window_visible is True

        state_manager.set_ui_window_visible(False)
        assert state_manager.get_state().ui_window_visible is False

    def test_update_config(self, state_manager):
        """测试更新配置"""
        assert state_manager.get_state().config['watch_interval_ms'] == 500
        assert state_manager.get_state().config['debug_mode'] is False

        state_manager.update_config({
            'watch_interval_ms': 1000,
            'debug_mode': True,
            'mystery_gem_mode': 'max'
        })

        state = state_manager.get_state()
        assert state.config['watch_interval_ms'] == 1000
        assert state.config['debug_mode'] is True
        assert state.config['mystery_gem_mode'] == 'max'

    def test_get_config(self, state_manager):
        """测试获取配置"""
        config = state_manager.get_config()
        assert config['watch_interval_ms'] == 500
        assert config['debug_mode'] is False

    def test_state_observer(self, state_manager):
        """测试状态观察者"""
        changes = []

        def observer(old_state, new_state):
            changes.append((old_state.recognition_state, new_state.recognition_state))

        # 添加观察者
        state_manager.add_observer(observer)

        # 触发状态变更
        state_manager.start_recognition()

        assert len(changes) == 1
        assert changes[0][0] == RecognitionState.IDLE
        assert changes[0][1] == RecognitionState.IN_PROGRESS

    def test_multiple_observers(self, state_manager):
        """测试多个观察者"""
        observer1_changes = []
        observer2_changes = []

        def observer1(old_state, new_state):
            observer1_changes.append(new_state.recognition_state)

        def observer2(old_state, new_state):
            observer2_changes.append(new_state.recognition_state)

        # 添加多个观察者
        state_manager.add_observer(observer1)
        state_manager.add_observer(observer2)

        # 触发状态变更
        state_manager.start_recognition()

        assert len(observer1_changes) == 1
        assert len(observer2_changes) == 1

    def test_remove_observer(self, state_manager):
        """测试移除观察者"""
        changes = []

        def observer(old_state, new_state):
            changes.append(new_state.recognition_state)

        # 添加观察者
        state_manager.add_observer(observer)

        # 触发状态变更
        state_manager.start_recognition()
        assert len(changes) == 1

        # 移除观察者
        state_manager.remove_observer(observer)

        # 再次触发状态变更
        state_manager.complete_recognition(success=True)
        # 观察者不会被调用
        assert len(changes) == 1

    def test_single_state_manager_instance(self):
        """测试状态管理器单例"""
        manager1 = StateManager.get_instance()
        manager2 = StateManager.get_instance()

        # 应该是同一个实例
        assert manager1 is manager2

        # 在一个实例中修改状态
        manager1.start_recognition()

        # 在另一个实例中获取状态，应该能看到修改
        assert manager2.is_recognizing()

    def test_reset_state(self, state_manager):
        """测试重置状态"""
        state_manager.start_recognition()
        state_manager.start_price_update()
        state_manager.set_ui_window_visible(True)

        assert state_manager.is_recognizing()
        assert state_manager.is_updating_price()
        assert state_manager.get_state().ui_window_visible

        # 重置状态
        state_manager.reset_state()

        state = state_manager.get_state()
        assert state.recognition_state == RecognitionState.IDLE
        assert state.price_update_state == PriceUpdateState.IDLE
        assert state.ui_window_visible is False
        assert state.recognition_error is None
        assert state.price_update_message is None
