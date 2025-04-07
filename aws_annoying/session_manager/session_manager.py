from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

import requests
from tqdm import tqdm

from .errors import UnsupportedPlatformError

logger = logging.getLogger(__name__)


class SessionManager:
    """AWS Session Manager plugin manager."""

    def verify_installation(self) -> tuple[bool, Path | None, str | None]:
        """Verify installation of AWS Session Manager plugin.

        Returns:
            3-tuple of boolean flag indicating whether plugin installed, binary path and version string.
        """
        # Find plugin binary
        if not (binary_path_str := shutil.which("session-manager-plugin")):
            return False, None, None

        # Check version
        binary_path = Path(binary_path_str).absolute()
        result_bytes = subprocess.run(  # noqa: S603
            [str(binary_path), "--version"],
            check=True,
            capture_output=True,
        )
        result = result_bytes.stdout.decode().strip()
        if not bool(re.match(r"[\d\.]+", result)):
            return False, binary_path, result

        return True, binary_path, result

    def install(
        self,
        *,
        os: str | None = None,
        linux_distribution: _LinuxDistribution | None = None,
        arch: str | None = None,
        is_root: bool | None = None,
    ) -> None:
        """Install AWS Session Manager plugin.

        Args:
            os: The operating system to install the plugin on. If `None`, will use the current operating system.
            linux_distribution: The Linux distribution to install the plugin on.
                If `None` and current `os` is `"Linux"`, will try to detect the distribution from current system.
            arch: The architecture to install the plugin on. If `None`, will use the current architecture.
            is_root: Whether to run the installation as root. If `None`, will check if the current user is root.
        """
        os = os or platform.system()
        linux_distribution = linux_distribution or _detect_linux_distribution()
        arch = arch or platform.machine()
        is_root = is_root or _is_root()

        if os == "Windows":
            self._install_windows()
        elif os == "Darwin":
            self._install_macos(arch=arch, is_root=is_root)
        elif os == "Linux":
            self._install_linux(linux_distribution=linux_distribution, arch=arch, is_root=is_root)
        else:
            msg = f"Unsupported operating system: {os}"
            raise UnsupportedPlatformError(msg)

    def before_install(self, command: list[str]) -> None:
        """Hook to run before invoking plugin installation command."""

    # https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-windows.html
    def _install_windows(self) -> None:
        """Install session-manager-plugin on Windows via EXE installer."""
        download_url = (
            "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            p = Path(temp_dir)
            exe_installer = _download_file(download_url, p / "SessionManagerPluginSetup.exe")
            command = [str(exe_installer), "/quiet"]
            self.before_install(command)
            subprocess.call(command, cwd=p)  # noqa: S603

    # https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-macos-overview.html
    def _install_macos(self, *, arch: str, is_root: bool) -> None:
        """Install session-manager-plugin on macOS via signed installer."""
        # ! Intel chip will not be supported
        if arch == "x86_64":
            download_url = (
                "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/session-manager-plugin.pkg"
            )
        elif arch == "arm64":
            download_url = (
                "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac_arm64/session-manager-plugin.pkg"
            )
        else:
            msg = f"Architecture {arch} not supported for macOS"
            raise UnsupportedPlatformError(msg)

        with tempfile.TemporaryDirectory() as temp_dir:
            p = Path(temp_dir)
            _download_file(download_url, p / "session-manager-plugin.pkg")

            # Run installer
            command = _command_as_root(
                ["installer", "-pkg", "./session-manager-plugin.pkg", "-target", "/"],
                is_root=is_root,
            )
            self.before_install(command)
            subprocess.call(command, cwd=p)  # noqa: S603

            # Symlink
            command = [
                "ln",
                "-s",
                "/usr/local/sessionmanagerplugin/bin/session-manager-plugin",
                "/usr/local/bin/session-manager-plugin",
            ]
            if not is_root:
                command = ["sudo", *command]

            logger.info("Running %s to create symlink", " ".join(command))
            Path("/usr/local/bin").mkdir(exist_ok=True)
            subprocess.call(command, cwd=p)  # noqa: S603

    # https://docs.aws.amazon.com/systems-manager/latest/userguide/install-plugin-linux-overview.html
    def _install_linux(
        self,
        *,
        linux_distribution: _LinuxDistribution,
        arch: str,
        is_root: bool,
    ) -> None:
        name = linux_distribution.name
        version = linux_distribution.version

        # Debian / Ubuntu
        if name in ("debian", "ubuntu"):
            logger.info("Detected Linux distribution: Debian / Ubuntu")

            # Download installer
            url_map = {
                "x86_64": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb",
                "x86": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_32bit/session-manager-plugin.deb",
                "arm64": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_arm64/session-manager-plugin.deb",
            }
            download_url = url_map.get(arch)
            if not download_url:
                msg = f"Architecture {arch} not supported for distribution {name}"
                raise UnsupportedPlatformError(msg)

            with tempfile.TemporaryDirectory() as temp_dir:
                p = Path(temp_dir)
                _download_file(download_url, p / "session-manager-plugin.deb")

                # Invoke installation command
                command = _command_as_root(["dpkg", "--install", "session-manager-plugin.deb"], is_root=is_root)
                self.before_install(command)
                subprocess.call(command, cwd=p)  # noqa: S603

        # Amazon Linux / RHEL
        elif name in ("amzn", "rhel"):
            logger.info("Detected Linux distribution: Amazon Linux / RHEL")

            # Determine package URL and package manager
            url_map = {
                "x86_64": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_64bit/session-manager-plugin.rpm",
                "x86": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_32bit/session-manager-plugin.rpm",
                "arm64": "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/linux_arm64/session-manager-plugin.rpm",
            }
            package_url = url_map.get(arch)
            if not package_url:
                msg = f"Architecture {arch} not supported for distribution {name}"
                raise UnsupportedPlatformError(msg)

            use_yum = (
                # Amazon Linux 2
                name == "amzn" and version.startswith("2")
            ) or (
                # RHEL 7 Maipo (8 Ootpa / 9 Plow)
                name == "rhel" and "Maipo" in version
            )  # ... else use dnf
            package_manager = "yum" if use_yum else "dnf"

            # Invoke installation command
            command = _command_as_root([package_manager, "install", "-y", package_url], is_root=is_root)
            self.before_install(command)
            subprocess.call(command)  # noqa: S603

        else:
            msg = f"Unsupported distribution: {name}"
            raise UnsupportedPlatformError(msg)


def _command_as_root(command: list[str], *, is_root: bool) -> list[str]:
    """Run command as root."""
    is_root = is_root or _is_root()
    if not is_root:
        command = ["sudo", *command]

    return command


def _is_root() -> bool:
    return os.geteuid() == 0


class _LinuxDistribution(NamedTuple):
    name: str
    version: str


def _detect_linux_distribution() -> _LinuxDistribution:
    """Autodetect current Linux distribution."""
    os_release = _os_release()
    name = os_release.get("ID", "").lower()
    version = os_release.get("VERSION", "")
    return _LinuxDistribution(name=name, version=version)


def _os_release() -> dict[str, str]:
    """Parse `/etc/os-release` file into a dictionary."""
    content = Path("/etc/os-release").read_text()
    return {
        key.strip('"'): value.strip('"')
        for key, value in (line.split("=", 1) for line in content.splitlines() if "=" in line)
    }


# TODO(lasuillard): Move to utils, abstract it into file downloader for switchable downloaders
def _download_file(url: str, path: Path) -> Path:
    """Download file from URL to path."""
    # https://gist.github.com/yanqd0/c13ed29e29432e3cf3e7c38467f42f51
    logger.info("Downloading file from URL (%s) to %s.", url, path)
    with requests.get(url, stream=True, timeout=10) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        with (
            path.open("wb") as f,
            tqdm(
                # Make the URL less verbose in the progress bar
                desc=url.replace("https://s3.amazonaws.com/session-manager-downloads/plugin", "..."),
                total=total_size,
                unit="iB",
                unit_scale=True,
                unit_divisor=1_024,
            ) as pbar,
        ):
            for chunk in response.iter_content(chunk_size=8_192):
                size = f.write(chunk)
                pbar.update(size)

    return path.absolute()
