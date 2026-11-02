from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from cffi import FFI

_CDEF = """
typedef unsigned char GoUint8;
typedef long long GoInt64;
typedef GoInt64 GoInt;
typedef struct { const char *p; ptrdiff_t n; } _GoString_;
typedef _GoString_ GoString;
typedef struct { void *data; GoInt len; GoInt cap; } GoSlice;

extern GoString GetLanguage(GoString p0, GoSlice p1);
extern GoString GetLanguageType(GoString p0);
extern GoUint8 IsBinary(GoSlice data);
extern GoUint8 IsDocumentation(GoString path);
extern GoUint8 IsVendor(GoString path);
extern GoUint8 IsGenerated(GoString path, GoSlice content);
"""

_LIBS_DIR = Path(__file__).parent.parent / "libs"

# go-enry is built as a native c-shared library whose extension is
# platform-specific. `make libenry` emits the matching file into libs/.
_LIB_SUFFIXES = {"darwin": ".dylib", "win32": ".dll"}


def default_lib_name() -> str:
    """Return the platform-appropriate shared-library filename for go-enry."""
    suffix = _LIB_SUFFIXES.get(sys.platform, ".so")
    return f"libenry{suffix}"


def default_lib_path() -> Path:
    """Return the default path to the bundled go-enry shared library."""
    return _LIBS_DIR / default_lib_name()


# Process-wide cache of loaded libraries. The Go runtime inside the c-shared
# library keeps scheduler threads alive, so the handle must never be
# dlclose'd (which cffi does when the lib object is garbage collected) —
# unloading it crashes the process with SIGSEGV.
_lib_cache: dict[str, tuple[FFI, Any]] = {}


def _load_library(lib_path: str) -> tuple[FFI, Any]:
    if lib_path not in _lib_cache:
        ffi = FFI()
        ffi.cdef(_CDEF)
        _lib_cache[lib_path] = (ffi, ffi.dlopen(lib_path))
    return _lib_cache[lib_path]


class Enry:
    def __init__(self, lib_path: str | Path | None = None):
        self._ffi, self._lib = _load_library(
            str(lib_path or default_lib_path())
        )

    def _str_to_go(self, s: str):
        b = s.encode("utf-8")
        c_str = self._ffi.new("char[]", b)
        go_str = self._ffi.new("_GoString_ *", [c_str, len(b)])
        return go_str[0], c_str

    def _bytes_to_go_slice(self, b: bytes):
        data = b if b else b"\x00"
        c_bytes = self._ffi.new("char[]", data)
        go_slice = self._ffi.new("GoSlice *", [c_bytes, len(b), len(b)])
        return go_slice[0], c_bytes

    def _go_str_to_py(self, go_str) -> str:
        n = go_str.n
        if n > 0:
            return self._ffi.unpack(go_str.p, n).decode("utf-8")
        return ""

    def detect(self, filename: str, content: bytes) -> str:
        fname, _cs = self._str_to_go(filename)
        fcontent, _cb = self._bytes_to_go_slice(content)
        return self._go_str_to_py(self._lib.GetLanguage(fname, fcontent))

    def get_language_type(self, language: str) -> str:
        lang, _c = self._str_to_go(language)
        return self._go_str_to_py(self._lib.GetLanguageType(lang))

    def is_binary(self, content: bytes) -> bool:
        c, _cb = self._bytes_to_go_slice(content)
        return bool(self._lib.IsBinary(c))

    def is_documentation(self, filename: str) -> bool:
        fname, _c = self._str_to_go(filename)
        return bool(self._lib.IsDocumentation(fname))

    def is_vendored(self, filename: str) -> bool:
        fname, _c = self._str_to_go(filename)
        return bool(self._lib.IsVendor(fname))

    def is_generated(self, filename: str, content: bytes) -> bool:
        fname, _c = self._str_to_go(filename)
        fcontent, _cb = self._bytes_to_go_slice(content)
        return bool(self._lib.IsGenerated(fname, fcontent))
