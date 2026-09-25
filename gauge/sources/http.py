"""Polite HTTP for public data sources (standard library only).

SEC requires automated clients to send a User-Agent with contact details and
to stay under 10 requests per second; the client enforces a minimum interval
per host. Downloads are conditional (If-Modified-Since) so daily jobs only
re-fetch files that changed.
"""

from __future__ import annotations

import email.utils
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36"
)
MIN_INTERVAL = {"www.sec.gov": 0.15}  # seconds between requests to one host


class FetchError(RuntimeError):
    pass


class Http:
    def __init__(self, user_agent: str | None = None, timeout: float = 60.0) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self._last: dict[str, float] = {}

    def _agent_for(self, host: str) -> str:
        if host.endswith("sec.gov"):
            if not self.user_agent:
                raise FetchError(
                    "SEC requires a User-Agent with a contact email; set SEC_USER_AGENT "
                    '(e.g. "Gauge research you@example.com")'
                )
            return self.user_agent
        # Some state sites reject non-browser agents; append ours for transparency.
        return f"{BROWSER_UA} {self.user_agent}" if self.user_agent else BROWSER_UA

    def _wait(self, host: str) -> None:
        gap = MIN_INTERVAL.get(host, 0.0)
        elapsed = time.monotonic() - self._last.get(host, 0.0)
        if elapsed < gap:
            time.sleep(gap - elapsed)
        self._last[host] = time.monotonic()

    def _request(self, url: str, headers: dict[str, str] | None = None):
        host = urlparse(url).netloc
        self._wait(host)
        req = urllib.request.Request(
            url, headers={"User-Agent": self._agent_for(host), **(headers or {})}
        )
        return urllib.request.urlopen(req, timeout=self.timeout)

    def get(self, url: str) -> bytes:
        try:
            with self._request(url) as resp:
                return resp.read()
        except urllib.error.URLError as e:
            raise FetchError(f"GET {url} failed: {e}") from e

    def download(self, url: str, dest: Path, *, only_if_newer: bool = True) -> bool:
        """Download to ``dest``. Returns False when the server says it has not changed."""
        headers = {}
        if only_if_newer and dest.exists():
            headers["If-Modified-Since"] = email.utils.formatdate(dest.stat().st_mtime, usegmt=True)
        try:
            resp = self._request(url, headers)
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return False
            raise FetchError(f"GET {url} failed: HTTP {e.code}") from e
        except urllib.error.URLError as e:
            raise FetchError(f"GET {url} failed: {e}") from e
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        with resp, open(tmp, "wb") as f:
            while chunk := resp.read(1 << 20):
                f.write(chunk)
        os.replace(tmp, dest)
        return True
