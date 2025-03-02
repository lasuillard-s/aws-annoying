from pathlib import Path

from .command_builder import repeat_options
from .string_ import normalize_console_output

__all__ = ("PRINTENV_PY", "normalize_console_output", "printenv_py", "repeat_options")

PRINTENV_PY = (Path(__file__).parent / "scripts" / "printenv.py").absolute()
