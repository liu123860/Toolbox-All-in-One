"""AI 密钥安全存储：Windows DPAPI（当前用户上下文加密），配置文件里不出现明文密钥。"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32
_crypt32.CryptProtectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DATA_BLOB)]
_crypt32.CryptProtectData.restype = wintypes.BOOL
_crypt32.CryptUnprotectData.argtypes = [
    ctypes.POINTER(_DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(_DATA_BLOB),
    ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_DATA_BLOB)]
_crypt32.CryptUnprotectData.restype = wintypes.BOOL
_kernel32.LocalFree.argtypes = [ctypes.c_void_p]
_kernel32.LocalFree.restype = ctypes.c_void_p


def _blob(data: bytes):
    arr = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    return _DATA_BLOB(len(data), ctypes.cast(arr, ctypes.POINTER(ctypes.c_ubyte))), arr


def protect(text: str) -> str:
    if not text:
        return ""
    src, keep = _blob(text.encode("utf-8"))
    out = _DATA_BLOB()
    if not _crypt32.CryptProtectData(ctypes.byref(src), None, None, None, None,
                                     CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
        raise RuntimeError("DPAPI 加密失败")
    raw = ctypes.string_at(out.pbData, out.cbData)
    _kernel32.LocalFree(out.pbData)
    return base64.b64encode(raw).decode("ascii")


def unprotect(token: str) -> str:
    if not token:
        return ""
    src, keep = _blob(base64.b64decode(token))
    out = _DATA_BLOB()
    if not _crypt32.CryptUnprotectData(ctypes.byref(src), None, None, None, None,
                                       CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(out)):
        raise RuntimeError("DPAPI 解密失败（密钥只能在当前 Windows 账户下解开）")
    raw = ctypes.string_at(out.pbData, out.cbData)
    _kernel32.LocalFree(out.pbData)
    return raw.decode("utf-8")
