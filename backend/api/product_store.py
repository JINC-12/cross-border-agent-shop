"""商品数据的内存临时存储层。

作用：保存商品生成结果，提供"存一条"和"查列表"两个能力，替代真正的数据库。
位置：backend/api/product_store.py，被同目录的 product.py（路由）调用。

为什么用内存存储？
- 阶段2的要求：先不接入 MySQL，用最简单的方式把业务流程跑通。
- 服务重启后数据会丢失，这是预期行为，不是 Bug。

为什么单独拆一个文件？
- 把"数据怎么存"和"接口怎么响应"分开。等阶段3接入 MySQL 时，
  只需要重写本文件内部实现，路由代码一行都不用改（存取函数签名不变）。
- 加了线程锁：FastAPI 处理并发请求时可能同时读写 _products，
  加锁保证 id 自增和写入不会错乱。
"""

import threading
from datetime import datetime

# 内存数据表：{id: 商品记录字典}
_products: dict[int, dict] = {}

# 自增主键，模拟数据库的 AUTO_INCREMENT
_next_id: int = 1

# 线程锁，保证并发下的读写安全
_lock = threading.Lock()


def save_product(record: dict) -> dict:
    """保存一条商品记录，自动分配 id 和创建时间，返回完整记录。"""
    global _next_id
    with _lock:
        # {**record, ...} 是字典合并写法：复制一份再补充字段，避免修改调用方的原字典
        full_record = {
            **record,
            "id": _next_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _products[_next_id] = full_record
        _next_id += 1
    return full_record


def list_products(limit: int = 20) -> list[dict]:
    """按 id 从新到旧返回商品列表，最多 limit 条。"""
    with _lock:
        records = sorted(_products.values(), key=lambda r: r["id"], reverse=True)
    return records[:limit]


def get_product(product_id: int) -> dict | None:
    """按 id 查询单条记录，查不到返回 None（为后续接口预留）。"""
    with _lock:
        return _products.get(product_id)
