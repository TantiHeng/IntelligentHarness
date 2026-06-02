"""CLI 启动器：仅转交命令行执行入口，不包含参数解析或业务逻辑。"""

from intelligent_harness.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
