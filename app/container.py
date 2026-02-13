"""依赖注入容器 - 轻量级实现"""
from typing import TypeVar, Type, Dict, Any, Callable, Optional, get_type_hints
import inspect


T = TypeVar('T')


class DIContainer:
    """依赖注入容器"""

    def __init__(self) -> None:
        """初始化容器"""
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._instances: Dict[Type, Any] = {}

    def register_singleton(self, interface: Type[T], implementation: Optional[Type[T]] = None) -> None:
        """注册单例

        Args:
            interface: 接口类型
            implementation: 实现类型（如果为None，则interface本身就是实现）
        """
        impl = implementation if implementation is not None else interface
        self._factories[interface] = lambda: self._create_instance(impl)

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """注册工厂函数

        Args:
            interface: 接口类型
            factory: 工厂函数
        """
        self._factories[interface] = factory

    def register_instance(self, interface: Type[T], instance: T) -> None:
        """注册实例

        Args:
            interface: 接口类型
            instance: 实例
        """
        self._singletons[interface] = instance

    def resolve(self, interface: Type[T]) -> T:
        """解析依赖

        Args:
            interface: 接口类型

        Returns:
            实例对象

        Raises:
            ValueError: 如果接口未注册
        """
        # 检查是否已有单例实例
        if interface in self._singletons:
            return self._singletons[interface]

        # 检查是否有工厂
        if interface not in self._factories:
            raise ValueError(f"Interface {interface.__name__} is not registered")

        # 创建实例
        instance = self._factories[interface]()

        # 如果注册为单例，保存实例
        if interface in self._singletons:
            self._singletons[interface] = instance

        return instance

    def _create_instance(self, cls: Type) -> Any:
        """创建类实例，自动注入依赖

        Args:
            cls: 类类型

        Returns:
            实例对象
        """
        # 获取构造函数参数
        signature = inspect.signature(cls.__init__)
        parameters = signature.parameters

        # 准备构造参数
        kwargs = {}
        for param_name, param in parameters.items():
            if param_name == 'self':
                continue

            # 获取参数类型
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                continue

            # 递归解析依赖
            try:
                kwargs[param_name] = self.resolve(param_type)
            except ValueError:
                # 如果无法解析，尝试使用默认值
                if param.default != inspect.Parameter.empty:
                    kwargs[param_name] = param.default
                else:
                    raise

        # 创建实例
        return cls(**kwargs)

    def clear(self) -> None:
        """清空容器"""
        self._singletons.clear()
        self._factories.clear()
        self._instances.clear()
