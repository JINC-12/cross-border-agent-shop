"""MySQL 数据库连接工具。

作用：使用原生 mysql-connector-python 创建数据库连接，连接失败时给出中文排查提示。
位置：backend/db.py，公共基础模块，后续阶段2/3/4 需要落库时直接调用这里。

设计说明：
1. 不使用 SQLAlchemy ORM，保持 SQL 写法的直观性，方便初学者理解。
2. 阶段1只提供"连接"能力，不自动建库建表（MySQL 服务尚未安装）。
3. 连接失败不打印密码，避免密钥泄露到日志里。
"""

import mysql.connector
from mysql.connector import Error

from backend.settings import settings


def _build_config(include_database: bool = True) -> dict:
    """组装 mysql.connector.connect() 需要的参数字典。"""
    config = {
        "host": settings.MYSQL_HOST,
        "port": settings.MYSQL_PORT,
        "user": settings.MYSQL_USER,
        "password": settings.MYSQL_PASSWORD,
        "charset": settings.MYSQL_CHARSET,
        "connection_timeout": 5,  # 连接超时 5 秒，避免没装 MySQL 时请求卡很久
    }
    if include_database:
        config["database"] = settings.MYSQL_DATABASE
    return config


def get_mysql_connection(include_database: bool = True):
    """创建一个 MySQL 连接。

    参数 include_database：是否指定数据库。
        阶段1数据库可能还没建好，可以先传 False 只连 MySQL 服务。

    返回：mysql.connector 的连接对象（用完记得 conn.close()）。
    失败：抛出 RuntimeError，其中包含中文排查步骤，方便定位问题。
    """
    try:
        return mysql.connector.connect(**_build_config(include_database))
    except Error as exc:
        raise RuntimeError(
            "MySQL 连接失败，请按以下步骤排查：\n"
            "1. 确认 MySQL 服务已经启动（Windows 搜索 services.msc，查看带 MySQL 的服务是否“正在运行”）；\n"
            f"2. 检查项目根目录 .env 中的 MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD "
            f"是否正确（当前尝试 {settings.MYSQL_HOST}:{settings.MYSQL_PORT}，用户 {settings.MYSQL_USER}）；\n"
            f"3. 确认数据库 `{settings.MYSQL_DATABASE}` 已经创建（阶段1不会自动建库）；\n"
            f"4. 原始错误信息：{exc}"
        ) from exc


def check_mysql_connection() -> tuple[bool, str]:
    """测试 MySQL 是否可用，返回 (是否成功, 提示信息)。

    用途：健康检查、阶段2接入数据库前的自测。不会因为失败而让程序崩溃。
    """
    try:
        conn = get_mysql_connection()
    except RuntimeError as exc:
        return False, str(exc)

    # 连接成功后执行一条最简单的 SQL，确认账号对数据库有基本访问权限
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        return True, "MySQL 连接正常"
    except Error as exc:
        return False, f"MySQL 已连接，但执行测试 SQL 失败：{exc}"
    finally:
        conn.close()
