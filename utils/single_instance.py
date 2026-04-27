from __future__ import annotations

import ctypes
import sys


class SingleInstanceGuard:
    ERROR_ALREADY_EXISTS = 183

    def __init__(self, name: str):
        self.name = name
        self._handle = None

    def acquire(self) -> bool:
        if not sys.platform.startswith("win"):
            return True
        try:
            kernel32 = ctypes.windll.kernel32
            self._handle = kernel32.CreateMutexW(None, False, self.name)
            if not self._handle:
                return True
            return kernel32.GetLastError() != self.ERROR_ALREADY_EXISTS
        except Exception:
            return True

    def release(self) -> None:
        if not self._handle or not sys.platform.startswith("win"):
            return
        try:
            ctypes.windll.kernel32.CloseHandle(self._handle)
        except Exception:
            pass
        finally:
            self._handle = None
