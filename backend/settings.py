"""项目统一配置模块。

作用：从项目根目录的 .env 文件读取配置（大模型密钥、MySQL、Redis、CORS 等），
     统一通过 settings 对象访问，避免在代码里硬编码密钥。
位置：backend/settings.py，属于最底层的公共模块，其它模块（db.py、api、agent）都从这里取配置。

注意：
1. .env 文件不会提交到 Git（已在 .gitignore 中忽略），仓库里只保留 .env.example 模板。
2. 所有字段都有默认值，所以即使暂时没有 .env，服务也能正常启动。
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend 的上一级），用于定位 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """全部配置项。pydantic-settings 会自动把 .env 中的同名变量映射到这里。"""

    # ---------- 应用基础配置 ----------
    APP_NAME: str = "cross-border-agent-shop"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "dev"          # 运行环境：dev / test / prod
    DEBUG: bool = True            # 调试模式，开启后接口报错信息更详细

    # 业务接口统一前缀，阶段2的接口会是 /api/product/...
    API_PREFIX: str = "/api"

    # 允许跨域访问的前端地址，多个用英文逗号分隔（Vue 开发服务器默认 5173 端口）
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---------- 大模型配置（阶段2才会真正用到，这里先预留） ----------
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # ---------- MySQL 配置 ----------
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "cross_border_shop"
    MYSQL_CHARSET: str = "utf8mb4"

    # ---------- Redis 配置 ----------
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # pydantic-settings 的全局行为设置
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",   # 读取项目根目录的 .env
        env_file_encoding="utf-8",
        case_sensitive=False,         # 环境变量名大小写不敏感
        extra="ignore",               # .env 里有多余变量时不报错
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的 CORS 字符串转成列表，供 CORSMiddleware 使用。"""
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """带缓存的配置读取函数：整个进程只创建一个 Settings 实例。"""
    return Settings()


# 其它模块直接 `from backend.settings import settings` 即可
settings = get_settings()
