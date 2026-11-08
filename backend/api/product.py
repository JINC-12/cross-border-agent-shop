"""商品生成模块的路由（对外 HTTP 接口）。

作用：定义 POST /api/product/generate（生成商品内容）和
     GET /api/product/list（生成历史列表）两个接口。
位置：backend/api/product.py，属于接口层：
     负责"参数校验 → 调 Agent → 存结果 → 返回 JSON"，
     不包含任何生成逻辑（生成逻辑在 backend/agent/product_agent.py）。

在 /docs 里调试方法：打开 http://127.0.0.1:8000/docs，
找到对应接口 → Try it out → 修改请求体 → Execute 即可。
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.agent.product_agent import run_product_agent
from backend.api.product_store import list_products, save_product

router = APIRouter(prefix="/api/product", tags=["商品生成"])


# ---------------------------------------------------------------------------
# 请求/响应模型（Pydantic）
# 作用：FastAPI 会依据这些模型自动完成参数校验，并生成 /docs 的接口文档。
# 比如 product_name 传空字符串，会直接返回 422 错误和中文提示，不用手写校验代码。
# ---------------------------------------------------------------------------


class ProductGenerateRequest(BaseModel):
    """POST /api/product/generate 的请求体。"""

    product_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="产品名称，例如：保温杯",
        examples=["保温杯"],
    )
    keywords: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="关键词列表，最多 10 个，例如：[\"户外\", \"礼品\"]",
    )
    extra_requirements: str = Field(
        default="",
        max_length=500,
        description="可选：卖家补充要求，例如：强调性价比、目标人群是宝妈",
    )
    language: Literal["zh", "en"] = Field(
        default="zh",
        description="输出语言：zh=简体中文（默认），en=英文",
    )


class ProductGenerateResponse(BaseModel):
    """生成接口的响应结构（同时也是列表接口的单条记录结构）。"""

    id: int = Field(description="商品记录 ID")
    created_at: str = Field(description="创建时间（ISO 格式）")
    product_name: str = Field(description="产品名称")
    keywords: list[str] = Field(description="关键词列表")
    language: str = Field(description="输出语言：zh=简体中文，en=英文")
    task_plan: list[str] = Field(description="Agent 任务拆解计划（可看到思考过程）")
    title: str = Field(description="生成的商品标题")
    selling_points: list[str] = Field(description="卖点列表")
    listing_copy: str = Field(description="listing 详情文案")
    image_prompt: str = Field(description="AI 绘图提示词（英文）")
    content_source: str = Field(
        description="内容来源：llm=真实大模型生成；mock=本地模板模拟"
    )


# ---------------------------------------------------------------------------
# 接口定义
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=ProductGenerateResponse,
    summary="生成商品内容（标题/卖点/文案/绘图提示词）",
)
def generate_product(req: ProductGenerateRequest):
    """调用 LangGraph 商品生成 Agent，生成结果会保存到临时存储。"""
    try:
        result = run_product_agent(
            product_name=req.product_name,
            keywords=req.keywords,
            extra_requirements=req.extra_requirements,
            language=req.language,
        )
    except Exception as exc:
        # Agent 内部意外出错时，返回 500 并带上原因，方便定位
        raise HTTPException(status_code=500, detail=f"商品生成失败：{exc}") from exc

    # 生成结果写入临时存储并返回（带上 id、created_at）
    return save_product(result)


@router.get(
    "/list",
    response_model=list[ProductGenerateResponse],
    summary="商品生成历史列表（新记录在前）",
)
def product_list(
    limit: int = Query(default=20, ge=1, le=100, description="返回条数，1-100"),
):
    """查看历史生成记录。服务重启后数据清空（阶段2为内存存储）。"""
    return list_products(limit)
