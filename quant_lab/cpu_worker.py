"""Private child entry: trusted parent request over stdio, never a UI script.

Only the application-created pipe is used; this is not a file-import API or a
network endpoint. The UI exposes built-in functions, never arbitrary code.
"""

import pickle
import sys


def _binary_stdio(stream, handle_number, mode):
    """Windowed Python/frozen executables may set sys.stdin/stdout to None."""
    if stream is not None:
        return getattr(stream, "buffer", stream)
    import ctypes
    from ctypes import wintypes
    import msvcrt
    import os
    get_handle = ctypes.windll.kernel32.GetStdHandle
    get_handle.argtypes, get_handle.restype = [wintypes.DWORD], wintypes.HANDLE
    handle = get_handle(handle_number)
    if handle in (None, 0, ctypes.c_void_p(-1).value):
        raise RuntimeError("worker pipe unavailable")
    descriptor = msvcrt.open_osfhandle(handle, os.O_BINARY | (os.O_RDONLY if mode == "rb" else os.O_WRONLY))
    return os.fdopen(descriptor, mode)


def main():
    from quant_lab.jobs import _error_message
    try:
        reader = _binary_stdio(sys.stdin, -10, "rb")
        function, args, kwargs = pickle.loads(reader.read())
        output = (True, function(*args, **kwargs))
    except Exception as error:
        output = (False, _error_message(error))
    writer = _binary_stdio(sys.stdout, -11, "wb")
    writer.write(pickle.dumps(output, protocol=pickle.HIGHEST_PROTOCOL))
    writer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
