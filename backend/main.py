"""FastAPI 应用入口。

作用：创建 app 实例，注册 CORS 跨域配置和各个路由模块，是 uvicorn 启动的入口文件。
位置：backend/main.py，启动命令 `uvicorn backend.main:app --reload` 指向的就是这里的 app 变量。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.health import router as health_router
from backend.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Agent 驱动的跨境电商自动化平台（分阶段开发）",
)

# ---------------------------------------------------------------------------
# CORS 跨域配置
# 作用：允许阶段5的 Vue 前端（默认 http://localhost:5173）直接调用后端接口。
# 注意：allow_origins 不能用 ["*"] 同时搭配 allow_credentials=True，
#       所以这里从 .env 的 CORS_ORIGINS 读取明确的白名单。
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 注册路由
# 阶段1只有系统探活路由；阶段2开始会继续 include_router 商品模块的路由。
# ---------------------------------------------------------------------------
app.include_router(health_router)
