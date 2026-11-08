"""商品生成 Agent（LangGraph 实现）。

作用：接收「产品名称 + 关键词」，先用 LangGraph 把任务拆成 4 步流水线，
     依次生成：商品标题 → 卖点 → listing 文案 → AI 绘图提示词，返回结构化 JSON。
位置：backend/agent/product_agent.py，业务核心层。api 层（backend/api/product.py）
     只负责接 HTTP 请求，收到后调用本文件的 run_product_agent()。

运行模式（对初学者很重要）：
1. LLM 模式：.env 里配置了 OPENAI_API_KEY 时，各节点真实调用大模型生成内容。
2. Mock 模式：没配 Key、或调用失败时，自动回退到本地模板生成，保证接口永远可用。
   这样既满足"不接付费接口也能开发调试"，又保留了真实 Agent 的完整流程。

LangGraph 核心概念（3 个词就够入门）：
- State（状态）：一个字典，所有节点共享，相当于"流水线上的工件"。
- Node（节点）：一个函数，接收状态、返回要更新的字段，相当于"一道工序"。
- Edge（边）：把节点按顺序连起来，规定工序的先后。
"""

import re
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from backend.settings import settings

# ---------------------------------------------------------------------------
# 1. 定义状态：整个 Agent 流水线共享的数据结构
# ---------------------------------------------------------------------------


class ProductState(TypedDict):
    """Agent 的全局状态（流水线工件）。

    每个节点函数都会收到它，并把自己负责的字段更新后返回。
    """
    # ---- 输入字段（接口传进来）----
    product_name: str          # 产品名称，例如：保温杯
    keywords: list[str]        # 关键词，例如：["户外", "礼品"]
    extra_requirements: str    # 卖家的补充要求，可以为空

    # ---- 过程字段 ----
    task_plan: list[str]       # 第一个节点拆解出的任务计划

    # ---- 输出字段 ----
    title: str                 # 商品标题
    selling_points: list[str]  # 卖点列表
    listing_copy: str          # listing 详情文案
    image_prompt: str          # AI 绘图提示词（给 Midjourney / DALL·E 用）

    # ---- 标记字段 ----
    # 内容来源："llm" = 真实大模型生成；"mock" = 本地模板模拟。
    # 只要有一个节点回退到了 mock，最终就标记为 mock，方便排查。
    content_source: str


# ---------------------------------------------------------------------------
# 2. LLM 调用与 Mock 生成工具函数
# ---------------------------------------------------------------------------

# 统一的系统提示词：告诉大模型它扮演什么角色
_SYSTEM_PROMPT = (
    "你是一名资深跨境电商文案专家，擅长为 Amazon、Temu、独立站撰写商品内容。"
    "输出要求：简洁、有卖点、符合海外买家阅读习惯。"
)


def _llm_generate(user_prompt: str) -> str | None:
    """调用大模型生成一段文本。

    返回值：
    - 配置了 Key 且调用成功：返回模型输出的字符串；
    - 没配置 Key 或调用失败：返回 None，由调用节点回退到 Mock 生成。
    这样设计的好处：接口永远可用，不会因为没配密钥就报错。
    """
    if not settings.OPENAI_API_KEY:
        return None  # 没配密钥，直接走 Mock
    try:
        llm = ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
            timeout=30,
        )
        response = llm.invoke(
            [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
        )
        return response.content.strip()
    except Exception as exc:  # 网络错误、额度不足、Key 无效等都归到这里
        print(f"[product_agent] LLM 调用失败，本次节点回退 Mock。原因：{exc}")
        return None


def _split_lines(text: str) -> list[str]:
    """把大模型返回的多行文本清洗成干净的卖点列表。

    典型的模型输出是："1. xxx\n2. xxx" 或 "- xxx"，这里统一去掉编号和符号。
    """
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        # 去掉行首的 - * • 数字 点 、 空格 等列表符号
        line = re.sub(r"^[-*•\d.、\s]+", "", line)
        if line:
            lines.append(line)
    return lines


# ------------------------- Mock 生成（模板模拟） -------------------------


def _mock_title(product_name: str, keywords: list[str]) -> str:
    """模拟生成商品标题：核心词 + 关键词 + 营销修饰。"""
    kw = "、".join(keywords[:3]) if keywords else "多场景适用"
    return f"【跨境优选】{product_name}｜{kw}｜2026 新款升级热卖"


def _mock_selling_points(product_name: str, keywords: list[str]) -> list[str]:
    """模拟生成 4 条卖点。"""
    scene = keywords[0] if keywords else "日常"
    return [
        f"优质材料打造，安全耐用，{product_name}品质远超同类竞品",
        f"轻巧便携设计，{scene}场景随心使用，出行无负担",
        "精美包装，自用送礼两相宜，节日礼品首选",
        "海外仓现货直发，7 天无理由退换，售后无忧",
    ]


def _mock_listing(product_name: str, selling_points: list[str]) -> str:
    """模拟生成 listing 文案：开头抓眼球 + 卖点串联 + 行动号召。"""
    points_text = "；".join(selling_points[:3])
    return (
        f"还在为挑选{product_name}发愁？这款产品正是为你准备的！"
        f"{points_text}。"
        f"现在下单即享新品优惠，库存有限，立即抢购，让好物马上出发到你手中！"
    )


def _mock_image_prompt(product_name: str, keywords: list[str]) -> str:
    """模拟生成 AI 绘图提示词。

    绘图模型（Midjourney / DALL·E）对英文提示词效果更好，
    所以模板里主体用产品名，其余用英文风格描述词。
    """
    kw = ", ".join(keywords[:3]) if keywords else "daily use"
    return (
        f"Commercial product photography of {product_name} ({kw}), "
        f"clean white studio background, soft lighting, centered composition, "
        f"high detail, 4k, e-commerce hero image style"
    )


# ---------------------------------------------------------------------------
# 3. 定义节点函数：每个节点 = 一道工序
#    约定：入参是当前状态 state，返回值是"要更新的字段"字典。
#    节点回退 Mock 时，把 content_source 标记为 "mock"。
# ---------------------------------------------------------------------------


def plan_node(state: ProductState) -> dict:
    """节点1：任务拆解。把"生成商品内容"拆成 4 个子任务，写进 task_plan。

    说明：流水线本身已经体现了拆解结果，这里再显式输出一份计划，
         一是让返回结果里能看到 Agent "思考过程"，二是方便前端展示。
    """
    print("[product_agent] 执行节点：plan（任务拆解）")
    name = state["product_name"]
    plan = [
        f"根据产品「{name}」生成跨境电商标题",
        "提炼 4 条商品卖点",
        "撰写 listing 详情文案",
        "生成 AI 绘图提示词",
    ]
    return {"task_plan": plan}


def title_node(state: ProductState) -> dict:
    """节点2：生成商品标题。"""
    print("[product_agent] 执行节点：title（生成标题）")
    name = state["product_name"]
    keywords = state["keywords"]

    user_prompt = (
        f"请为以下产品生成 1 条跨境电商标题（80 字符以内，突出核心卖点，不要堆砌符号）：\n"
        f"产品名称：{name}\n"
        f"关键词：{'、'.join(keywords) if keywords else '无'}"
    )
    if state["extra_requirements"]:
        user_prompt += f"\n卖家补充要求：{state['extra_requirements']}"

    llm_text = _llm_generate(user_prompt)
    if llm_text:
        return {"title": llm_text}

    # Mock 回退
    return {
        "title": _mock_title(name, keywords),
        "content_source": "mock",
    }


def selling_points_node(state: ProductState) -> dict:
    """节点3：生成卖点列表。"""
    print("[product_agent] 执行节点：selling_points（提炼卖点）")
    name = state["product_name"]
    keywords = state["keywords"]

    user_prompt = (
        f"请为产品「{name}」提炼 4 条跨境销售卖点，每条一行，"
        f"每条不超过 25 字，覆盖品质、使用场景、礼品属性、售后。\n"
        f"关键词：{'、'.join(keywords) if keywords else '无'}"
    )
    if state["extra_requirements"]:
        user_prompt += f"\n卖家补充要求：{state['extra_requirements']}"

    llm_text = _llm_generate(user_prompt)
    if llm_text:
        return {"selling_points": _split_lines(llm_text)}

    return {
        "selling_points": _mock_selling_points(name, keywords),
        "content_source": "mock",
    }


def listing_node(state: ProductState) -> dict:
    """节点4：撰写 listing 文案。

    注意：这里会读取上一个节点产出的 selling_points，
    体现了 LangGraph 状态在节点间流转的特点（下游工序用上游的产出）。
    """
    print("[product_agent] 执行节点：listing（撰写文案）")
    name = state["product_name"]
    points = state["selling_points"]

    user_prompt = (
        f"请根据以下卖点，为产品「{name}」写一段 listing 详情文案，"
        f"100 字以内，开头抓眼球，结尾有行动号召：\n卖点：{'；'.join(points)}"
    )
    if state["extra_requirements"]:
        user_prompt += f"\n卖家补充要求：{state['extra_requirements']}"

    llm_text = _llm_generate(user_prompt)
    if llm_text:
        return {"listing_copy": llm_text}

    return {
        "listing_copy": _mock_listing(name, points),
        "content_source": "mock",
    }


def image_prompt_node(state: ProductState) -> dict:
    """节点5：生成 AI 绘图提示词（本流水线最后一个节点）。"""
    print("[product_agent] 执行节点：image_prompt（绘图提示词）")
    name = state["product_name"]
    keywords = state["keywords"]
    title = state["title"]

    user_prompt = (
        f"请为产品「{name}」（标题：{title}）生成一段英文 AI 绘图提示词，"
        f"用于 Midjourney / DALL·E 生成电商主图，只输出提示词本身：\n"
        f"关键词：{'、'.join(keywords) if keywords else '无'}"
    )

    llm_text = _llm_generate(user_prompt)
    if llm_text:
        return {"image_prompt": llm_text}

    return {
        "image_prompt": _mock_image_prompt(name, keywords),
        "content_source": "mock",
    }


# ---------------------------------------------------------------------------
# 4. 组装 LangGraph 流水线
# ---------------------------------------------------------------------------


def build_product_graph():
    """把 5 个节点按顺序连成一条流水线，返回编译好的可执行图。

    执行顺序：START → plan → title → selling_points → listing → image_prompt → END
    这是 LangGraph 最简单的"线性图"，适合入门；
    以后要加"审核不通过就重新生成"这类分支，只需 add_conditional_edges。
    """
    graph = StateGraph(ProductState)

    # 注册节点：第一个参数是节点名，第二个参数是处理函数
    graph.add_node("plan", plan_node)
    graph.add_node("title", title_node)
    graph.add_node("selling_points", selling_points_node)
    graph.add_node("listing", listing_node)
    graph.add_node("image_prompt", image_prompt_node)

    # 连边：规定执行顺序
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "title")
    graph.add_edge("title", "selling_points")
    graph.add_edge("selling_points", "listing")
    graph.add_edge("listing", "image_prompt")
    graph.add_edge("image_prompt", END)

    return graph.compile()  # 编译后才能 invoke


# 模块级编译一次，接口每次请求直接复用，不用重复构建
product_graph = build_product_graph()


# ---------------------------------------------------------------------------
# 5. 对外主入口：给 api 层调用
# ---------------------------------------------------------------------------


def run_product_agent(
    product_name: str, keywords: list[str], extra_requirements: str = ""
) -> dict:
    """运行商品生成 Agent，返回完整结果字典。

    参数来自 HTTP 请求，组装成初始状态后交给图执行；
    invoke 会按边的顺序跑完所有节点，返回最终状态（包含所有字段）。
    """
    initial_state: ProductState = {
        "product_name": product_name.strip(),
        "keywords": [k.strip() for k in keywords if k.strip()],
        "extra_requirements": extra_requirements.strip(),
        "task_plan": [],
        "title": "",
        "selling_points": [],
        "listing_copy": "",
        "image_prompt": "",
        "content_source": "llm",  # 乐观默认，任何节点回退 Mock 都会改写它
    }
    result = product_graph.invoke(initial_state)
    return dict(result)  # 转成普通 dict，方便后续序列化存储
