"""CLI 应用边界：统一调度命令并格式化用户错误，不实现具体命令。"""

import sys
from collections.abc import Sequence

import yaml
from jsonschema import SchemaError, ValidationError
from pydantic import ValidationError as PydanticValidationError

from intelligent_harness.cli.commands import HANDLERS
from intelligent_harness.cli.constants import Command
from intelligent_harness.cli.parser import build_parser


EXPECTED_USER_ERRORS = (
    OSError,
    ValueError,
    KeyError,
    SchemaError,
    ValidationError,
    PydanticValidationError,
    yaml.YAMLError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse CLI arguments, dispatch one command and format expected user errors."""
    args = build_parser().parse_args(argv)
    try:
        HANDLERS[Command(args.command)](args)
    except EXPECTED_USER_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
