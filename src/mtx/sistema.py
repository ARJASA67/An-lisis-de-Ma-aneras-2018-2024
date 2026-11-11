"""Utilidades del sistema operativo usadas por los scripts (medición de memoria)."""
from __future__ import annotations

import sys


def rss_mb() -> float:
    """Memoria residente máxima del proceso, en MB (Linux reporta KB; Windows, bytes del pico)."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class _Mem(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        m = _Mem()
        m.cb = ctypes.sizeof(m)
        k32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Mem),
                                               wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(m), m.cb):
            raise OSError("GetProcessMemoryInfo falló")
        return m.PeakWorkingSetSize / 2**20
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
