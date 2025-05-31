from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import requests
from tqdm import tqdm

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class AbstractDownloader(ABC):
    """Abstract downloader class for downloading files."""

    @abstractmethod
    def download(self, url: str, *, to: Path) -> Path:
        """Download file from URL to path."""


class DummyDownloader(AbstractDownloader):
    """Dummy downloader that does nothing (mainly for testing purposes)."""

    def download(self, url: str, *, to: Path) -> Path:
        """Download file from URL to path."""
        logger.debug("Dummy downloader called for URL (%s) to %s.", url, to)
        return to.absolute()


class TQDMDownloader(AbstractDownloader):
    """Downloader with TQDM progress bar."""

    def download(self, url: str, *, to: Path) -> Path:
        """Download file from URL to path."""
        # https://gist.github.com/yanqd0/c13ed29e29432e3cf3e7c38467f42f51
        logger.info("Downloading file from URL (%s) to %s.", url, to)
        with requests.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            with (
                to.open("wb") as f,
                tqdm(desc=url, total=total_size, unit="iB", unit_scale=True, unit_divisor=1_024) as pbar,
            ):
                for chunk in response.iter_content(chunk_size=8_192):
                    size = f.write(chunk)
                    pbar.update(size)

        return to.absolute()
