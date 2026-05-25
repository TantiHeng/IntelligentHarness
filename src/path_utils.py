import os
from pathlib import Path
from typing import Union


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"


def get_project_root() -> str:
    """获取项目根目录绝对路径。"""
    return str(PROJECT_ROOT)


def get_file_path(relative_path: Union[str, os.PathLike]) -> str:
    """
    获取相对于项目根目录的文件绝对路径。

    示例：
        get_file_path(".env")
        get_file_path("data/marketing_records.db")
    """
    return str((PROJECT_ROOT / relative_path).resolve())


def get_env_path() -> str:
    """获取项目根目录下 .env 文件的绝对路径。"""
    return get_file_path(".env")


if __name__ == "__main__":
    print(f"项目根目录: {PROJECT_ROOT}")
    print(f"src 目录: {SRC_DIR}")
    print(f".env 路径: {get_env_path()}")
