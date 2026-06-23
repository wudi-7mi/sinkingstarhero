#!/usr/bin/env python3
"""Read the current level and look up level-entry routes.

This is a read-only helper. It reads the game's current level-set pointer and
level index from memory, then maps that index back to the level name using the
level-set files extracted by ``extract_sinking_star_assets.py``.
"""

from __future__ import annotations

import argparse
import ctypes
import struct
from dataclasses import dataclass
from pathlib import Path
from ctypes import wintypes


PROCESS_NAME = "sinking_star.exe"
CURRENT_LEVEL_SET_RVA = 0x9ACF58
CURRENT_LEVEL_INDEX_RVA = 0x9ACBA0
PENDING_LEVEL_SET_RVA = 0x9ACF60
PENDING_LEVEL_INDEX_RVA = 0x72E070
TRANSITION_STATE_RVA = 0x72E9D0

MAX_PATH = 260
MAX_MODULE_NAME32 = 255
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
DWORD = wintypes.DWORD
LONG = wintypes.LONG
BOOL = wintypes.BOOL
HANDLE = wintypes.HANDLE
HMODULE = wintypes.HMODULE
ULONG_PTR = ctypes.c_size_t
SIZE_T = ctypes.c_size_t
BYTE = ctypes.c_ubyte


class ProcessEntry32W(ctypes.Structure):
    _fields_ = (
        ("dwSize", DWORD),
        ("cntUsage", DWORD),
        ("th32ProcessID", DWORD),
        ("th32DefaultHeapID", ULONG_PTR),
        ("th32ModuleID", DWORD),
        ("cntThreads", DWORD),
        ("th32ParentProcessID", DWORD),
        ("pcPriClassBase", LONG),
        ("dwFlags", DWORD),
        ("szExeFile", wintypes.WCHAR * MAX_PATH),
    )


class ModuleEntry32W(ctypes.Structure):
    _fields_ = (
        ("dwSize", DWORD),
        ("th32ModuleID", DWORD),
        ("th32ProcessID", DWORD),
        ("GlblcntUsage", DWORD),
        ("ProccntUsage", DWORD),
        ("modBaseAddr", ctypes.POINTER(BYTE)),
        ("modBaseSize", DWORD),
        ("hModule", HMODULE),
        ("szModule", wintypes.WCHAR * (MAX_MODULE_NAME32 + 1)),
        ("szExePath", wintypes.WCHAR * MAX_PATH),
    )


kernel32.CreateToolhelp32Snapshot.argtypes = (DWORD, DWORD)
kernel32.CreateToolhelp32Snapshot.restype = HANDLE
kernel32.Process32FirstW.argtypes = (HANDLE, ctypes.POINTER(ProcessEntry32W))
kernel32.Process32FirstW.restype = BOOL
kernel32.Process32NextW.argtypes = (HANDLE, ctypes.POINTER(ProcessEntry32W))
kernel32.Process32NextW.restype = BOOL
kernel32.Module32FirstW.argtypes = (HANDLE, ctypes.POINTER(ModuleEntry32W))
kernel32.Module32FirstW.restype = BOOL
kernel32.Module32NextW.argtypes = (HANDLE, ctypes.POINTER(ModuleEntry32W))
kernel32.Module32NextW.restype = BOOL
kernel32.OpenProcess.argtypes = (DWORD, BOOL, DWORD)
kernel32.OpenProcess.restype = HANDLE
kernel32.CloseHandle.argtypes = (HANDLE,)
kernel32.CloseHandle.restype = BOOL
kernel32.ReadProcessMemory.argtypes = (
    HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    SIZE_T,
    ctypes.POINTER(SIZE_T),
)
kernel32.ReadProcessMemory.restype = BOOL


class ProbeError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModuleInfo:
    base: int
    size: int
    path: str


@dataclass(frozen=True)
class CurrentLevel:
    level_set: str
    level_index: int
    level_name: str
    pending_level_set: str
    pending_level_index: int
    transition_state: int


class ProcessMemory:
    def __init__(self, pid: int) -> None:
        self.handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
        if not self.handle:
            raise ProbeError(f"OpenProcess failed: Windows error {ctypes.get_last_error()}")

    def close(self) -> None:
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def read(self, address: int, size: int) -> bytes:
        buf = (BYTE * size)()
        read = SIZE_T()
        ok = kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            ctypes.byref(buf),
            size,
            ctypes.byref(read),
        )
        if not ok or read.value != size:
            raise ProbeError(f"ReadProcessMemory failed at 0x{address:X}")
        return bytes(buf)

    def u64(self, address: int) -> int:
        return struct.unpack("<Q", self.read(address, 8))[0]

    def string(self, address: int, length: int) -> str:
        if not address or length <= 0:
            return ""
        data = self.read(address, min(length, 256))
        return data.split(b"\0", 1)[0].decode("ascii", errors="replace")


def invalid_handle_value() -> int:
    return ctypes.c_void_p(-1).value


def find_process_id(name: str) -> int:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if int(snap) == invalid_handle_value():
        raise ProbeError("CreateToolhelp32Snapshot(processes) failed")
    try:
        entry = ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(ProcessEntry32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        wanted = name.lower()
        while ok:
            if entry.szExeFile.lower() == wanted:
                return int(entry.th32ProcessID)
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    raise ProbeError(f"{name} is not running")


def get_module_info(pid: int, module_name: str) -> ModuleInfo:
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if int(snap) == invalid_handle_value():
        raise ProbeError("CreateToolhelp32Snapshot(modules) failed")
    try:
        entry = ModuleEntry32W()
        entry.dwSize = ctypes.sizeof(ModuleEntry32W)
        ok = kernel32.Module32FirstW(snap, ctypes.byref(entry))
        wanted = module_name.lower()
        while ok:
            if entry.szModule.lower() == wanted:
                base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
                if not base:
                    raise ProbeError("Could not read module base")
                return ModuleInfo(int(base), int(entry.modBaseSize), entry.szExePath)
            ok = kernel32.Module32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    raise ProbeError(f"module {module_name} not found")


def read_level_set(mem: ProcessMemory, level_set_ptr: int, level_index: int) -> tuple[str, str]:
    name_len = mem.u64(level_set_ptr)
    name_ptr = mem.u64(level_set_ptr + 8)
    level_set_name = mem.string(name_ptr, name_len)

    level_count = mem.u64(level_set_ptr + 56)
    table_ptr = mem.u64(level_set_ptr + 64)
    if level_index < 0 or level_index >= level_count:
        return level_set_name, ""

    entry = table_ptr + level_index * 16
    level_len = mem.u64(entry)
    level_ptr = mem.u64(entry + 8)
    return level_set_name, mem.string(level_ptr, level_len)


def probe_current_level() -> CurrentLevel:
    pid = find_process_id(PROCESS_NAME)
    module = get_module_info(pid, PROCESS_NAME)
    mem = ProcessMemory(pid)
    try:
        level_set_ptr = mem.u64(module.base + CURRENT_LEVEL_SET_RVA)
        level_index = mem.u64(module.base + CURRENT_LEVEL_INDEX_RVA)
        level_set, level_name = read_level_set(mem, level_set_ptr, level_index)

        pending_set_ptr = mem.u64(module.base + PENDING_LEVEL_SET_RVA)
        pending_index = mem.u64(module.base + PENDING_LEVEL_INDEX_RVA)
        pending_set = ""
        if pending_set_ptr:
            pending_set, _pending_name = read_level_set(mem, pending_set_ptr, pending_index)
        transition_state = mem.u64(module.base + TRANSITION_STATE_RVA)
        return CurrentLevel(level_set, level_index, level_name, pending_set, pending_index, transition_state)
    finally:
        mem.close()


def parse_level_set_file(path: Path, known_levels: set[str]) -> list[str]:
    levels: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("[") or line.startswith("*"):
            continue
        name = line.split()[0]
        if name in known_levels:
            levels.append(name)
    return levels


def build_level_lookup(repo_root: Path) -> dict[str, list[tuple[str, int]]]:
    level_index = repo_root / "analysis_out" / "level_index.csv"
    extracted_sets = repo_root / "analysis_out" / "extracted_levels" / "data" / "level_sets"
    if not level_index.exists() or not extracted_sets.exists():
        return {}

    known_levels: set[str] = set()
    for line in level_index.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        if line:
            known_levels.add(line.split(",", 1)[0])

    lookup: dict[str, list[tuple[str, int]]] = {}
    for path in sorted(extracted_sets.glob("*.level_set")):
        level_set = path.stem
        for index, level in enumerate(parse_level_set_file(path, known_levels)):
            lookup.setdefault(level, []).append((level_set, index))
    return lookup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", help="Look up how to reach this level name.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    current = probe_current_level()
    print(f"current_level_set={current.level_set}")
    print(f"current_level_index={current.level_index}")
    print(f"current_level={current.level_name}")
    print(f"pending_level_set={current.pending_level_set}")
    print(f"pending_level_index={current.pending_level_index}")
    print(f"transition_state={current.transition_state}")

    if args.target:
        lookup = build_level_lookup(repo_root)
        matches = lookup.get(args.target, [])
        print()
        print(f"target={args.target}")
        if not matches:
            print("target_found=false")
            print("hint=Run tools\\extract_sinking_star_assets.py first, or check the level name.")
            return 2

        print("target_found=true")
        for level_set, index in matches:
            marker = "current_set" if level_set == current.level_set else "other_set"
            print(f"route={level_set}:{index}:{marker}")
        print(f"recommended_command=:level {args.target}")
        if any(level_set == current.level_set for level_set, _index in matches):
            print("same_set_note=:advance_level can also reach it by changing level index within the current set.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
