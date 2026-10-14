import threading
import time
from collections import OrderedDict
from contextlib import contextmanager

from fastapi import HTTPException


class LoginLimiter:
    def __init__(self, limit: int = 8, window: int = 300):
        self.limit = limit
        self.window = window
        self.entries = OrderedDict()
        self.lock = threading.Lock()
        self.workers = threading.BoundedSemaphore(2)

    def check(self, username: str, origin: str, registered: bool = True) -> tuple[str, float]:
        now = time.monotonic()
        keys = (f"account:{username.strip().lower()}" if registered else "unregistered",)
        with self.lock:
            for key in list(self.entries):
                if self.entries[key][0] + self.window <= now:
                    del self.entries[key]
            for key in keys:
                started, attempts = self.entries.get(key, (now, 0))
                if attempts >= self.limit:
                    raise HTTPException(
                        status_code=429,
                        detail="Too many sign-in attempts. Wait a few minutes and retry.",
                        headers={"Retry-After": str(max(1, int(started + self.window - now)))},
                    )
            for key in keys:
                started, attempts = self.entries.get(key, (now, 0))
                self.entries[key] = (started, attempts + 1)
                self.entries.move_to_end(key)
            return keys[0], self.entries[keys[0]][0]

    def release_attempt(self, reservation: tuple[str, float]) -> None:
        key, reserved_at = reservation
        with self.lock:
            if key in self.entries and self.entries[key][0] == reserved_at:
                started, attempts = self.entries[key]
                if attempts <= 1:
                    del self.entries[key]
                else:
                    self.entries[key] = (started, attempts - 1)

    @contextmanager
    def verification(self):
        if not self.workers.acquire(blocking=False):
            raise HTTPException(
                status_code=429,
                detail="Sign-in is busy. Retry shortly.",
                headers={"Retry-After": "1"},
            )
        try:
            yield
        finally:
            self.workers.release()
