"""健康检查相关路由。

作用：提供 GET / 和 GET /health 两个探活接口，用于确认服务是否正常启动、配置是否加载成功。
位置：backend/api/health.py，是 api 层最基础的模块，也在演示"路由文件如何组织"的写法。
"""

from fastapi import APIRouter

from backend.settings import settings

router = APIRouter(tags=["系统"])


@router.get("/", summary="根路径")
def root():
    """访问根路径时返回一句欢迎语，方便浏览器直接确认服务已启动。"""
    return {"msg": "跨境电商Agent项目启动成功！", "docs": "/docs"}


@router.get("/health", summary="健康检查")
def health():
    """健康检查接口：返回服务状态和基础配置信息（不含任何密钥）。

    说明：阶段1 MySQL / Redis 尚未安装，所以这里不去连接数据库，
         只验证"服务能启动 + 配置能读取"，避免健康检查误报红。
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "env": settings.APP_ENV,
    }
