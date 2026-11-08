"""backend 包的入口标记文件。

作用：让 backend 成为一个标准 Python 包，这样可以使用 `backend.xxx` 的绝对导入方式。
位置：必须放在 backend 目录下，否则 `uvicorn backend.main:app` 会因为找不到包而报错。
"""
