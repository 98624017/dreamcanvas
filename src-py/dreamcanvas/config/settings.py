from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """应用级配置，读取 `.env` 或系统环境变量。"""

    model_config = SettingsConfigDict(env_prefix="DC_", env_file=".env", extra="ignore")

    phase: str = Field(default="P0", description="当前里程碑阶段标识")
    version: str = Field(default="0.1.0", description="后端版本号")
    log_dir: Path = Field(default=Path.home() / "AppData/Local/DreamCanvas/logs")
    projects_dir: Path = Field(default=Path.home() / "AppData/Roaming/DreamCanvas/projects")
    backups_dir: Path = Field(default=Path.home() / "AppData/Roaming/DreamCanvas/backups")
    python_bin: Path | None = Field(default=None, description="外部 Python 路径覆盖")
    secrets_path: Path = Field(default=Path("config/secrets.enc"), description="加密凭据文件路径")
    secrets_plaintext_path: Path = Field(
        default=Path("config/secrets.local.json"),
        description="明文凭据回退路径，仅限本地开发使用",
    )
    secrets_passphrase: str | None = Field(default=None, description="运行期解密凭据的主口令")


class Settings(AppSettings):
    """冻结后的配置模型。"""


@lru_cache
def get_settings() -> Settings:
    return Settings(**AppSettings().model_dump())
