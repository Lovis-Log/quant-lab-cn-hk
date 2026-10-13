"""Windows Credential Manager only; never fall back to a plaintext file."""

import ctypes
from ctypes import wintypes
import os


TARGET = "QuantLabCNHK/DeepSeek"


class SecureStorageUnavailable(RuntimeError):
    pass


class CREDENTIALW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)), ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


def _api():
    if os.name != "nt":
        raise SecureStorageUnavailable("系统安全存储不可用；密钥仅保留在当前会话。")
    try:
        api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
    except (OSError, AttributeError):
        raise SecureStorageUnavailable("系统安全存储不可用；密钥仅保留在当前会话。") from None
    api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                            ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api


def remember_key(key: str, *, target: str = TARGET) -> None:
    raw = key.encode("utf-16-le")
    if not raw or len(raw) > 512:
        raise SecureStorageUnavailable("密钥长度不适合系统安全存储；已保留会话模式。")
    api = _api()
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    credential = CREDENTIALW()
    credential.Type, credential.Persist = 1, 2  # generic, local-machine persistence for this user
    credential.TargetName, credential.UserName = target, "QuantLab DeepSeek API"
    credential.CredentialBlobSize = len(raw)
    credential.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
    try:
        if not api.CredWriteW(ctypes.byref(credential), 0):
            raise SecureStorageUnavailable("无法使用 Windows 凭据管理器；密钥仅保留在当前会话。")
    finally:
        ctypes.memset(buffer, 0, len(raw))


def load_key(*, target: str = TARGET) -> str | None:
    api = _api()
    pointer = ctypes.POINTER(CREDENTIALW)()
    if not api.CredReadW(target, 1, 0, ctypes.byref(pointer)):
        if ctypes.get_last_error() == 1168:
            return None
        raise SecureStorageUnavailable("无法读取系统凭据；请在当前会话填写密钥。")
    try:
        return ctypes.string_at(pointer.contents.CredentialBlob,
                                pointer.contents.CredentialBlobSize).decode("utf-16-le")
    finally:
        api.CredFree(pointer)


def clear_key(*, target: str = TARGET) -> None:
    api = _api()
    if not api.CredDeleteW(target, 1, 0) and ctypes.get_last_error() != 1168:
        raise SecureStorageUnavailable("会话密钥已清除；系统凭据删除失败，请在 Windows 凭据管理器中检查。")
