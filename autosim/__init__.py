# autosim/__init__.py

__version__ = "0.1.0"

# 对外暴露 run() 函数，用户也可以写 `from autosim import run`
from .app import run

__all__ = ["run"]
