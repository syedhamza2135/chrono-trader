"""A small Alpaca market-data client: one shared rate limit, retries, and pagination."""
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from .settings import DATA_URL, alpaca_headers


class RateLimiter:
    """Spaces requests evenly across threads so the whole process stays under the plan's limit."""

    def __init__(self, per_minute):
        self.interval = 60.0 / per_minute
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = self.next_at - now
            self.next_at = max(now, self.next_at) + self.interval
        if delay > 0:
            time.sleep(delay)


LIMITER = RateLimiter(per_minute=180)  # the free plan allows 200 a minute; keep headroom
_headers = None


def get(path, **params):
    global _headers
    _headers = _headers or alpaca_headers()
    url = f"{DATA_URL}{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(7):
        LIMITER.wait()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=_headers), timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as err:
            if err.code in (429, 500, 502, 503, 504):
                time.sleep(min(60, 2**attempt))
                continue
            raise RuntimeError(f"HTTP {err.code} for {path} {params}: {err.read()[:200]!r}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(min(60, 2**attempt))
    raise RuntimeError(f"Gave up on {path} {params} after retries")


def pages(path, **params):
    """Yield each page of a paginated endpoint."""
    token = None
    while True:
        body = get(path, **params, **({"page_token": token} if token else {}))
        yield body
        token = body.get("next_page_token")
        if not token:
            return
