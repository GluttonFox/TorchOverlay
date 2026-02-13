"""配置加密服务 - 加密和解密配置中的敏感信息"""
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.logger import get_logger
from core.exceptions import ConfigError

logger = get_logger(__name__)


class ConfigEncryptionService:
    """配置加密服务

    使用AES加密算法对配置中的敏感信息进行加密和解密。
    """

    # 需要加密的字段名称
    SENSITIVE_FIELDS = {
        'api_key',
        'secret_key',
        'password',
        'token',
        'access_key',
        'secret_key',
    }

    def __init__(self, master_password: Optional[str] = None):
        """初始化配置加密服务

        Args:
            master_password: 主密码，用于生成加密密钥。
                            如果为None，则使用默认主密码（仅用于开发环境）
        """
        if master_password is None:
            # 开发环境使用固定密钥（不安全，仅用于开发）
            logger.warning("使用默认主密码，不安全！请在生产环境中设置主密码")
            master_password = "TorchOverlayDefaultKey2024"

        self._master_password = master_password
        self._fernet = self._create_fernet()

    def _create_fernet(self) -> Fernet:
        """从主密码创建Fernet加密器

        Returns:
            Fernet加密器实例
        """
        # 使用PBKDF2HMAC从主密码派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'torch_overlay_salt',  # 固定盐值（在生产环境中应该随机生成并保存）
            iterations=480000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._master_password.encode()))
        return Fernet(key)

    def encrypt_value(self, value: str) -> str:
        """加密单个值

        Args:
            value: 要加密的值

        Returns:
            Base64编码的加密值

        Raises:
            ConfigError: 加密失败
        """
        try:
            encrypted = self._fernet.encrypt(value.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise ConfigError(f"加密值失败: {e}")

    def decrypt_value(self, encrypted_value: str) -> str:
        """解密单个值

        Args:
            encrypted_value: 加密的值

        Returns:
            解密后的原始值

        Raises:
            ConfigError: 解密失败
        """
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ConfigError(f"解密值失败: {e}")

    def encrypt_dict(self, config_dict: dict) -> dict:
        """加密配置字典中的敏感字段

        Args:
            config_dict: 配置字典

        Returns:
            包含加密字段的配置字典
        """
        result = {}
        for key, value in config_dict.items():
            if isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self.encrypt_dict(value)
            elif isinstance(value, str) and key in self.SENSITIVE_FIELDS:
                # 加密敏感字段
                result[key] = self.encrypt_value(value)
            else:
                # 保持不变
                result[key] = value
        return result

    def decrypt_dict(self, config_dict: dict) -> dict:
        """解密配置字典中的敏感字段

        Args:
            config_dict: 包含加密字段的配置字典

        Returns:
            解密后的配置字典
        """
        result = {}
        for key, value in config_dict.items():
            if isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self.decrypt_dict(value)
            elif isinstance(value, str) and key in self.SENSITIVE_FIELDS:
                try:
                    # 尝试解密敏感字段
                    result[key] = self.decrypt_value(value)
                except ConfigError:
                    # 解密失败，可能不是加密值，保持原样
                    logger.warning(f"字段 '{key}' 解密失败，保持原样")
                    result[key] = value
            else:
                # 保持不变
                result[key] = value
        return result

    def is_encrypted_value(self, value: str) -> bool:
        """检查值是否是加密值

        Args:
            value: 要检查的值

        Returns:
            是否是加密值
        """
        try:
            # 尝试解密
            decrypted = self.decrypt_value(value)
            # 如果解密成功，再加密回去看是否匹配
            re_encrypted = self.encrypt_value(decrypted)
            return re_encrypted == value
        except Exception:
            return False

    def encrypt_config_file(self, input_path: str, output_path: str) -> None:
        """加密配置文件

        Args:
            input_path: 输入配置文件路径
            output_path: 输出加密配置文件路径

        Raises:
            ConfigError: 加密失败
        """
        import json

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)

            encrypted_dict = self.encrypt_dict(config_dict)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(encrypted_dict, f, indent=4, ensure_ascii=False)

            logger.info(f"配置文件加密成功: {output_path}")
        except Exception as e:
            raise ConfigError(f"加密配置文件失败: {e}")

    def decrypt_config_file(self, input_path: str, output_path: str) -> None:
        """解密配置文件

        Args:
            input_path: 输入加密配置文件路径
            output_path: 输出解密配置文件路径

        Raises:
            ConfigError: 解密失败
        """
        import json

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                encrypted_dict = json.load(f)

            decrypted_dict = self.decrypt_dict(encrypted_dict)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(decrypted_dict, f, indent=4, ensure_ascii=False)

            logger.info(f"配置文件解密成功: {output_path}")
        except Exception as e:
            raise ConfigError(f"解密配置文件失败: {e}")

    def get_encryption_status(self, config_dict: dict) -> dict[str, bool]:
        """获取配置中敏感字段的加密状态

        Args:
            config_dict: 配置字典

        Returns:
            字段名到加密状态的映射
        """
        status = {}

        def check_dict(d: dict, prefix: str = "") -> None:
            for key, value in d.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, dict):
                    check_dict(value, full_key)
                elif isinstance(value, str) and key in self.SENSITIVE_FIELDS:
                    status[full_key] = self.is_encrypted_value(value)

        check_dict(config_dict)
        return status


def get_encryption_service(master_password: Optional[str] = None) -> ConfigEncryptionService:
    """获取配置加密服务单例

    Args:
        master_password: 主密码（仅第一次调用时生效）

    Returns:
        配置加密服务实例
    """
    if not hasattr(get_encryption_service, '_instance'):
        get_encryption_service._instance = ConfigEncryptionService(master_password)
    return get_encryption_service._instance
