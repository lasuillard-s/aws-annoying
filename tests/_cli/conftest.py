import contextlib
import subprocess
import sys
from collections.abc import Generator

import pytest


@pytest.fixture
def dummy_process() -> Generator[subprocess.Popen[bytes], None, None]:
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        yield proc
    finally:
        with contextlib.suppress(OSError):
            proc.kill()
