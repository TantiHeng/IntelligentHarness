"""路径适配器：解析项目内资源路径，不负责读取或校验资源内容。"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def project_path(relative_path: str | Path) -> Path:
    return (PROJECT_ROOT / relative_path).resolve()
