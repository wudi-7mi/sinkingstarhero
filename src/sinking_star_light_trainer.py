# -*- coding: utf-8 -*-
"""
Standalone light ability trainer for Order of the Sinking Star Demo.

This intentionally does not load Cheat Engine, CE Lua, or the CE MCP bridge.
It ports the useful parts of the CT table into a small Tkinter GUI and a
Windows memory patcher implemented with ctypes.
"""

from __future__ import annotations

import ctypes
import math
import os
import struct
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox
from tkinter import ttk
from ctypes import wintypes


APP_NAME = "SinkingStarHero"
APP_VERSION = "0.1.0"
PROCESS_NAME = "sinking_star.exe"

PICK_RVA = 0x2AEF49
GATE_RVA = 0x2AF0CC

PICK_SIGNATURE = bytes.fromhex("49 8D 8C 24 88 03 00 00 EB 3D")
GATE_SIGNATURE = bytes.fromhex(
    "80 7C 24 60 00 75 51 80 7C 24 76 00 74 4A 45 84 F6 74 2C"
)

PICK_PATCH_LEN = len(PICK_SIGNATURE)
GATE_PATCH_LEN = len(GATE_SIGNATURE)

PICK_RETURN_DELTA = 0x2AEF90 - 0x2AEF49
GATE_SKIP_DELTA = 0x2AF124 - 0x2AF0CC
GATE_THROUGH_DELTA = 0x2AF10B - 0x2AF0CC
GATE_R14_CONTINUE_DELTA = 0x2AF0DF - 0x2AF0CC

PLAYER_OPEN = 0x388
PLAYER_THROUGH = 0x389
PLAYER_SMASH = 0x38A
PLAYER_DOUBLE = 0x38B
PLAYER_GATE_LOCK = 0x38F
PLAYER_COORD_OFFSETS = (0x00, 0x04, 0x08)
COORD_AXES = ("x", "y", "z")
COORD_LIMIT = 1_000_000.0

FLAG_DEFS = (
    ("through", "穿墙 / 绿光", "Ctrl+Alt+1", 0x31),
    ("open", "开门 / 红光", "Ctrl+Alt+2", 0x32),
    ("smash", "粉碎 / 黄光", "Ctrl+Alt+3", 0x33),
    ("double", "双倍 / 橙光", "Ctrl+Alt+4", 0x34),
)


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)

SIZE_T = ctypes.c_size_t
ULONG_PTR = ctypes.c_size_t
BYTE = ctypes.c_ubyte
DWORD = wintypes.DWORD
LONG = wintypes.LONG
BOOL = wintypes.BOOL
HANDLE = wintypes.HANDLE
HMODULE = wintypes.HMODULE
LPVOID = wintypes.LPVOID
LPCVOID = wintypes.LPCVOID

MAX_PATH = 260
MAX_MODULE_NAME32 = 255

TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
SYNCHRONIZE = 0x00100000
PROCESS_RIGHTS = (
    PROCESS_QUERY_INFORMATION
    | PROCESS_VM_OPERATION
    | PROCESS_VM_READ
    | PROCESS_VM_WRITE
    | SYNCHRONIZE
)

MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
MEM_RELEASE = 0x00008000

PAGE_EXECUTE_READWRITE = 0x40

WAIT_TIMEOUT = 0x00000102
VK_CONTROL = 0x11
VK_MENU = 0x12


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


kernel32.OpenProcess.argtypes = (DWORD, BOOL, DWORD)
kernel32.OpenProcess.restype = HANDLE
kernel32.CloseHandle.argtypes = (HANDLE,)
kernel32.CloseHandle.restype = BOOL
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
kernel32.ReadProcessMemory.argtypes = (
    HANDLE,
    LPCVOID,
    LPVOID,
    SIZE_T,
    ctypes.POINTER(SIZE_T),
)
kernel32.ReadProcessMemory.restype = BOOL
kernel32.WriteProcessMemory.argtypes = (
    HANDLE,
    LPVOID,
    LPCVOID,
    SIZE_T,
    ctypes.POINTER(SIZE_T),
)
kernel32.WriteProcessMemory.restype = BOOL
kernel32.VirtualAllocEx.argtypes = (HANDLE, LPVOID, SIZE_T, DWORD, DWORD)
kernel32.VirtualAllocEx.restype = LPVOID
kernel32.VirtualFreeEx.argtypes = (HANDLE, LPVOID, SIZE_T, DWORD)
kernel32.VirtualFreeEx.restype = BOOL
kernel32.VirtualProtectEx.argtypes = (
    HANDLE,
    LPVOID,
    SIZE_T,
    DWORD,
    ctypes.POINTER(DWORD),
)
kernel32.VirtualProtectEx.restype = BOOL
kernel32.FlushInstructionCache.argtypes = (HANDLE, LPCVOID, SIZE_T)
kernel32.FlushInstructionCache.restype = BOOL
kernel32.WaitForSingleObject.argtypes = (HANDLE, DWORD)
kernel32.WaitForSingleObject.restype = DWORD
user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
user32.GetAsyncKeyState.restype = ctypes.c_short


class TrainerError(RuntimeError):
    pass


def win_error(message: str) -> TrainerError:
    return TrainerError(f"{message}: Windows error {ctypes.get_last_error()}")


def check_bool(ok: int, message: str) -> None:
    if not ok:
        raise win_error(message)


def is_rel32(src: int, dst: int, instr_len: int = 5) -> bool:
    rel = dst - (src + instr_len)
    return -(2**31) <= rel <= (2**31 - 1)


def rel32(src: int, dst: int, instr_len: int = 5) -> bytes:
    rel = dst - (src + instr_len)
    if not -(2**31) <= rel <= (2**31 - 1):
        raise TrainerError("目标跳转距离超过 rel32 范围")
    return struct.pack("<i", rel)


def make_jmp_patch(src: int, dst: int, length: int) -> bytes:
    if length < 5:
        raise TrainerError("补丁长度不足以写入 JMP")
    return b"\xE9" + rel32(src, dst) + (b"\x90" * (length - 5))


def decode_rel32_jmp(src: int, data: bytes) -> int | None:
    if len(data) < 5 or data[0] != 0xE9:
        return None
    return src + 5 + struct.unpack("<i", data[1:5])[0]


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


class CodeBuilder:
    def __init__(self) -> None:
        self.buf = bytearray()
        self.labels: dict[str, int] = {}
        self.patches: list[tuple[str, int, str | int, int]] = []

    def label(self, name: str) -> None:
        self.labels[name] = len(self.buf)

    def emit(self, data: bytes) -> None:
        self.buf.extend(data)

    def db(self, *values: int) -> None:
        self.buf.extend(values)

    def dq(self, value: int) -> None:
        self.buf.extend(struct.pack("<Q", value))

    def align(self, alignment: int) -> None:
        while len(self.buf) % alignment:
            self.buf.append(0)

    def rip(self, prefix: bytes, label: str, suffix: bytes = b"") -> None:
        self.emit(prefix)
        disp_pos = len(self.buf)
        self.emit(b"\x00\x00\x00\x00")
        self.emit(suffix)
        self.patches.append(("rip", disp_pos, label, len(self.buf)))

    def jmp_label(self, label: str) -> None:
        self.emit(b"\xE9")
        disp_pos = len(self.buf)
        self.emit(b"\x00\x00\x00\x00")
        self.patches.append(("rel_label", disp_pos, label, disp_pos + 4))

    def jcc_label(self, opcode2: int, label: str) -> None:
        self.emit(bytes((0x0F, opcode2)))
        disp_pos = len(self.buf)
        self.emit(b"\x00\x00\x00\x00")
        self.patches.append(("rel_label", disp_pos, label, disp_pos + 4))

    def jmp_abs(self, target: int) -> None:
        self.emit(b"\xE9")
        disp_pos = len(self.buf)
        self.emit(b"\x00\x00\x00\x00")
        self.patches.append(("rel_abs", disp_pos, target, disp_pos + 4))

    def finalize(self, base: int) -> tuple[bytes, dict[str, int]]:
        out = bytearray(self.buf)
        absolute_labels = {name: base + offset for name, offset in self.labels.items()}
        for kind, disp_pos, target, next_off in self.patches:
            if kind == "rip":
                assert isinstance(target, str)
                target_addr = absolute_labels[target]
            elif kind == "rel_label":
                assert isinstance(target, str)
                target_addr = absolute_labels[target]
            elif kind == "rel_abs":
                assert isinstance(target, int)
                target_addr = target
            else:
                raise AssertionError(kind)

            source_next = base + next_off
            disp = target_addr - source_next
            if not -(2**31) <= disp <= (2**31 - 1):
                raise TrainerError("生成的远程代码跳转距离超过 rel32 范围")
            out[disp_pos : disp_pos + 4] = struct.pack("<i", disp)
        return bytes(out), absolute_labels


def build_remote_code(
    remote_base: int,
    pick_return: int,
    gate_skip: int,
    gate_through: int,
    gate_r14_continue: int,
) -> tuple[bytes, dict[str, int]]:
    b = CodeBuilder()

    b.label("pick_hook")
    b.rip(b"\x48\xFF\x05", "pick_count")
    b.rip(b"\x4C\x89\x25", "player_ptr")
    b.rip(b"\x80\x3D", "through_enabled", b"\x00")
    b.jcc_label(0x84, "pick_skip_through")
    b.emit(b"\x41\xC6\x84\x24\x89\x03\x00\x00\x01")
    b.label("pick_skip_through")
    b.rip(b"\x80\x3D", "smash_enabled", b"\x00")
    b.jcc_label(0x84, "pick_skip_smash")
    b.emit(b"\x41\xC6\x84\x24\x8A\x03\x00\x00\x01")
    b.emit(b"\x41\xC6\x84\x24\x8F\x03\x00\x00\x00")
    b.label("pick_skip_smash")
    b.emit(b"\x49\x8D\x8C\x24\x88\x03\x00\x00")
    b.jmp_abs(pick_return)

    b.label("gate_hook")
    b.rip(b"\x48\xFF\x05", "gate_count")
    b.rip(b"\x80\x3D", "through_enabled", b"\x00")
    b.jcc_label(0x84, "gate_original")
    b.rip(b"\x4C\x39\x25", "player_ptr")
    b.jcc_label(0x85, "gate_original")
    b.emit(b"\x80\x7C\x24\x60\x00")
    b.jcc_label(0x85, "gate_force")
    b.emit(b"\x80\x7C\x24\x76\x00")
    b.jcc_label(0x85, "gate_force")
    b.jmp_label("gate_original")

    b.label("gate_force")
    b.rip(b"\x48\xFF\x05", "force_count")
    b.emit(b"\xC6\x44\x24\x60\x00")
    b.emit(b"\xC6\x44\x24\x76\x01")
    b.emit(b"\x41\xB6\x00")
    b.jmp_abs(gate_through)

    b.label("gate_original")
    b.emit(b"\x80\x7C\x24\x60\x00")
    b.jcc_label(0x85, "gate_skip")
    b.emit(b"\x80\x7C\x24\x76\x00")
    b.jcc_label(0x84, "gate_skip")
    b.emit(b"\x45\x84\xF6")
    b.jcc_label(0x84, "gate_through")
    b.jmp_abs(gate_r14_continue)
    b.label("gate_skip")
    b.jmp_abs(gate_skip)
    b.label("gate_through")
    b.jmp_abs(gate_through)

    b.align(8)
    b.label("player_ptr")
    b.dq(0)
    b.label("pick_count")
    b.dq(0)
    b.label("gate_count")
    b.dq(0)
    b.label("force_count")
    b.dq(0)
    b.label("through_enabled")
    b.db(0)
    b.label("open_enabled")
    b.db(0)
    b.label("smash_enabled")
    b.db(0)
    b.label("double_enabled")
    b.db(0)

    return b.finalize(remote_base)


@dataclass
class ModuleInfo:
    base: int
    size: int
    path: str


@dataclass
class HookInfo:
    pick_addr: int
    gate_addr: int
    remote_base: int
    remote_size: int
    labels: dict[str, int]
    original_pick: bytes
    original_gate: bytes
    owns_hook: bool


class ProcessMemory:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.handle = kernel32.OpenProcess(PROCESS_RIGHTS, False, pid)
        if not self.handle:
            raise win_error("无法打开游戏进程，可能需要以管理员身份运行")

    def close(self) -> None:
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None

    def is_alive(self) -> bool:
        return self.handle and kernel32.WaitForSingleObject(self.handle, 0) == WAIT_TIMEOUT

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
            raise win_error(f"读取内存失败 0x{address:X}")
        return bytes(buf)

    def write(self, address: int, data: bytes) -> None:
        if not data:
            return
        buf = (BYTE * len(data)).from_buffer_copy(data)
        written = SIZE_T()
        ok = kernel32.WriteProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            ctypes.byref(buf),
            len(data),
            ctypes.byref(written),
        )
        if not ok or written.value != len(data):
            raise win_error(f"写入内存失败 0x{address:X}")

    def write_code(self, address: int, data: bytes) -> None:
        old = DWORD()
        check_bool(
            kernel32.VirtualProtectEx(
                self.handle,
                ctypes.c_void_p(address),
                len(data),
                PAGE_EXECUTE_READWRITE,
                ctypes.byref(old),
            ),
            f"修改代码页权限失败 0x{address:X}",
        )
        try:
            self.write(address, data)
            kernel32.FlushInstructionCache(self.handle, ctypes.c_void_p(address), len(data))
        finally:
            restore = DWORD()
            kernel32.VirtualProtectEx(
                self.handle, ctypes.c_void_p(address), len(data), old.value, ctypes.byref(restore)
            )

    def read_u64(self, address: int) -> int:
        return struct.unpack("<Q", self.read(address, 8))[0]

    def read_f32(self, address: int) -> float:
        return struct.unpack("<f", self.read(address, 4))[0]

    def write_u8(self, address: int, value: int) -> None:
        self.write(address, bytes((value & 0xFF,)))

    def write_f32(self, address: int, value: float) -> None:
        self.write(address, struct.pack("<f", float(value)))

    def write_flag(self, address: int, enabled: bool) -> None:
        self.write_u8(address, 1 if enabled else 0)

    def read_counter(self, address: int) -> int:
        try:
            return self.read_u64(address)
        except TrainerError:
            return 0

    def alloc_near(self, target: int, size: int) -> int:
        size = align_up(size, 0x1000)
        first = kernel32.VirtualAllocEx(
            self.handle, None, size, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE
        )
        if first:
            first_addr = int(first)
            if is_rel32(target, first_addr):
                return first_addr
            kernel32.VirtualFreeEx(self.handle, ctypes.c_void_p(first_addr), 0, MEM_RELEASE)

        granularity = 0x10000
        max_distance = 0x70000000
        low = max(0x10000, target - max_distance)
        high = min(0x7FFFFFFF0000, target + max_distance)
        seen: set[int] = set()
        for distance in range(0, max_distance, granularity):
            for candidate in (target + distance, target - distance):
                candidate &= ~(granularity - 1)
                if candidate < low or candidate > high or candidate in seen:
                    continue
                seen.add(candidate)
                addr = kernel32.VirtualAllocEx(
                    self.handle,
                    ctypes.c_void_p(candidate),
                    size,
                    MEM_COMMIT | MEM_RESERVE,
                    PAGE_EXECUTE_READWRITE,
                )
                if addr:
                    return int(addr)
        raise TrainerError("无法在游戏代码附近分配远程代码内存")

    def free(self, address: int) -> None:
        if address:
            kernel32.VirtualFreeEx(self.handle, ctypes.c_void_p(address), 0, MEM_RELEASE)

    def scan(self, base: int, size: int, pattern: bytes) -> int | None:
        chunk_size = 0x100000
        tail = b""
        for offset in range(0, size, chunk_size):
            read_size = min(chunk_size, size - offset)
            try:
                data = self.read(base + offset, read_size)
            except TrainerError:
                tail = b""
                continue
            window = tail + data
            found = window.find(pattern)
            if found >= 0:
                return base + offset - len(tail) + found
            tail = window[-(len(pattern) - 1) :]
        return None


def snapshot_processes() -> list[tuple[int, str]]:
    invalid = ctypes.c_void_p(-1).value
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if int(snap) == invalid:
        raise win_error("创建进程快照失败")
    try:
        entry = ProcessEntry32W()
        entry.dwSize = ctypes.sizeof(ProcessEntry32W)
        processes: list[tuple[int, str]] = []
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            processes.append((int(entry.th32ProcessID), entry.szExeFile))
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
        return processes
    finally:
        kernel32.CloseHandle(snap)


def find_process_id(name: str) -> int | None:
    wanted = name.lower()
    for pid, exe in snapshot_processes():
        if exe.lower() == wanted:
            return pid
    return None


def get_module_info(pid: int, module_name: str) -> ModuleInfo:
    invalid = ctypes.c_void_p(-1).value
    snap = kernel32.CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid
    )
    if int(snap) == invalid:
        raise win_error("创建模块快照失败")
    try:
        entry = ModuleEntry32W()
        entry.dwSize = ctypes.sizeof(ModuleEntry32W)
        wanted = module_name.lower()
        ok = kernel32.Module32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szModule.lower() == wanted:
                base = ctypes.cast(entry.modBaseAddr, ctypes.c_void_p).value
                if not base:
                    raise TrainerError("读取模块基址失败")
                return ModuleInfo(int(base), int(entry.modBaseSize), entry.szExePath)
            ok = kernel32.Module32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    raise TrainerError(f"未找到模块 {module_name}")


class LightTrainerBackend:
    def __init__(self) -> None:
        self.pid: int | None = None
        self.mem: ProcessMemory | None = None
        self.module: ModuleInfo | None = None
        self.hook: HookInfo | None = None
        self.last_error = ""
        self.last_attach_attempt = 0.0

    @property
    def attached(self) -> bool:
        return self.mem is not None and self.hook is not None and self.mem.is_alive()

    def _adopt_existing_hook(
        self,
        mem: ProcessMemory,
        pick_addr: int,
        gate_addr: int,
        pick_live: bytes,
        gate_live: bytes,
    ) -> HookInfo | None:
        pick_dst = decode_rel32_jmp(pick_addr, pick_live)
        gate_dst = decode_rel32_jmp(gate_addr, gate_live)
        if pick_dst is None or gate_dst is None:
            return None
        if pick_live[5:] != (b"\x90" * (PICK_PATCH_LEN - 5)):
            return None
        if gate_live[5:] != (b"\x90" * (GATE_PATCH_LEN - 5)):
            return None

        remote_base = pick_dst
        code, labels = build_remote_code(
            remote_base,
            pick_return=pick_addr + PICK_RETURN_DELTA,
            gate_skip=gate_addr + GATE_SKIP_DELTA,
            gate_through=gate_addr + GATE_THROUGH_DELTA,
            gate_r14_continue=gate_addr + GATE_R14_CONTINUE_DELTA,
        )
        if gate_dst != labels["gate_hook"]:
            return None

        code_size = labels["player_ptr"] - remote_base
        if code_size <= 0:
            return None
        try:
            existing_code = mem.read(remote_base, code_size)
        except TrainerError:
            return None
        if existing_code != code[:code_size]:
            return None

        return HookInfo(
            pick_addr=pick_addr,
            gate_addr=gate_addr,
            remote_base=remote_base,
            remote_size=0x4000,
            labels=labels,
            original_pick=PICK_SIGNATURE,
            original_gate=GATE_SIGNATURE,
            owns_hook=False,
        )

    def attach_if_needed(self) -> bool:
        if self.attached:
            return True
        now = time.monotonic()
        if now - self.last_attach_attempt < 1.0:
            return False
        self.last_attach_attempt = now
        self.detach()

        pid = find_process_id(PROCESS_NAME)
        if pid is None:
            self.last_error = ""
            return False

        mem: ProcessMemory | None = None
        remote_base = 0
        pick_addr = 0
        gate_addr = 0
        original_pick = b""
        original_gate = b""
        patched_pick = False
        patched_gate = False
        try:
            mem = ProcessMemory(pid)
            module = get_module_info(pid, PROCESS_NAME)
            pick_addr = mem.scan(module.base, module.size, PICK_SIGNATURE)
            gate_addr = mem.scan(module.base, module.size, GATE_SIGNATURE)
            if pick_addr is None:
                pick_addr = module.base + PICK_RVA
            if gate_addr is None:
                gate_addr = module.base + GATE_RVA

            original_pick = mem.read(pick_addr, PICK_PATCH_LEN)
            original_gate = mem.read(gate_addr, GATE_PATCH_LEN)

            adopted = self._adopt_existing_hook(
                mem, pick_addr, gate_addr, original_pick, original_gate
            )
            if adopted is not None:
                self.pid = pid
                self.mem = mem
                self.module = module
                self.hook = adopted
                self.last_error = ""
                return True

            if original_pick != PICK_SIGNATURE:
                raise TrainerError("玩家能力捕获位置已被其他补丁占用，重启游戏后再试")
            if original_gate != GATE_SIGNATURE:
                raise TrainerError("绿光穿墙位置已被其他补丁占用，重启游戏后再试")

            remote_size = 0x4000
            remote_base = mem.alloc_near(pick_addr, remote_size)
            code, labels = build_remote_code(
                remote_base,
                pick_return=pick_addr + PICK_RETURN_DELTA,
                gate_skip=gate_addr + GATE_SKIP_DELTA,
                gate_through=gate_addr + GATE_THROUGH_DELTA,
                gate_r14_continue=gate_addr + GATE_R14_CONTINUE_DELTA,
            )

            if not is_rel32(pick_addr, labels["pick_hook"]):
                raise TrainerError("pick hook 距离超过 rel32 范围")
            if not is_rel32(gate_addr, labels["gate_hook"]):
                raise TrainerError("gate hook 距离超过 rel32 范围")

            mem.write(remote_base, code)
            mem.write_code(pick_addr, make_jmp_patch(pick_addr, labels["pick_hook"], PICK_PATCH_LEN))
            patched_pick = True
            mem.write_code(gate_addr, make_jmp_patch(gate_addr, labels["gate_hook"], GATE_PATCH_LEN))
            patched_gate = True

            self.pid = pid
            self.mem = mem
            self.module = module
            self.hook = HookInfo(
                pick_addr=pick_addr,
                gate_addr=gate_addr,
                remote_base=remote_base,
                remote_size=remote_size,
                labels=labels,
                original_pick=original_pick,
                original_gate=original_gate,
                owns_hook=True,
            )
            self.last_error = ""
            return True
        except Exception as exc:
            if mem is not None:
                try:
                    if mem.is_alive():
                        if patched_gate and gate_addr and original_gate:
                            mem.write_code(gate_addr, original_gate)
                        if patched_pick and pick_addr and original_pick:
                            mem.write_code(pick_addr, original_pick)
                        if remote_base:
                            mem.free(remote_base)
                except Exception:
                    pass
                try:
                    mem.close()
                except Exception:
                    pass
            self.last_error = str(exc)
            self.pid = None
            self.mem = None
            self.module = None
            self.hook = None
            return False

    def detach(self) -> None:
        mem = self.mem
        hook = self.hook
        if mem and hook:
            try:
                if mem.is_alive() and hook.owns_hook:
                    try:
                        if mem.read(hook.pick_addr, 1) == b"\xE9":
                            mem.write_code(hook.pick_addr, hook.original_pick)
                    except Exception:
                        pass
                    try:
                        if mem.read(hook.gate_addr, 1) == b"\xE9":
                            mem.write_code(hook.gate_addr, hook.original_gate)
                    except Exception:
                        pass
                    try:
                        mem.free(hook.remote_base)
                    except Exception:
                        pass
            finally:
                try:
                    mem.close()
                except Exception:
                    pass
        elif mem:
            try:
                mem.close()
            except Exception:
                pass

        self.pid = None
        self.mem = None
        self.module = None
        self.hook = None

    def label(self, name: str) -> int:
        if not self.hook:
            raise TrainerError("后端尚未连接")
        return self.hook.labels[name]

    def sync_flags(self, flags: dict[str, bool]) -> None:
        if not self.attached or not self.mem:
            return
        for key in ("through", "open", "smash", "double"):
            self.mem.write_flag(self.label(f"{key}_enabled"), flags.get(key, False))

    def keep_player_state(self, flags: dict[str, bool]) -> None:
        if not self.attached or not self.mem:
            return
        self.sync_flags(flags)
        if not any(flags.values()):
            return

        player = self.player_ptr()
        if not player:
            return

        if flags.get("through"):
            self.mem.write_u8(player + PLAYER_THROUGH, 1)
        if flags.get("open"):
            self.mem.write_u8(player + PLAYER_OPEN, 1)
            self.mem.write_u8(player + PLAYER_GATE_LOCK, 0)
        if flags.get("smash"):
            self.mem.write_u8(player + PLAYER_SMASH, 1)
            self.mem.write_u8(player + PLAYER_GATE_LOCK, 0)
        if flags.get("double"):
            self.mem.write_u8(player + PLAYER_DOUBLE, 1)
            self.mem.write_u8(player + PLAYER_GATE_LOCK, 0)

    def player_ptr(self) -> int:
        if not self.attached or not self.mem:
            return 0
        try:
            return self.mem.read_u64(self.label("player_ptr"))
        except TrainerError:
            return 0

    def player_xyz(self) -> tuple[float, float, float]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_ptr()
        if not player:
            raise TrainerError("尚未捕获玩家实体")
        return tuple(self.mem.read_f32(player + offset) for offset in PLAYER_COORD_OFFSETS)

    def write_player_xyz(self, values: tuple[float, float, float]) -> None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_ptr()
        if not player:
            raise TrainerError("尚未捕获玩家实体")
        self.mem.write(player, struct.pack("<fff", *values))

    def status_counters(self) -> tuple[int, int, int]:
        if not self.attached or not self.mem:
            return (0, 0, 0)
        return (
            self.mem.read_counter(self.label("pick_count")),
            self.mem.read_counter(self.label("gate_count")),
            self.mem.read_counter(self.label("force_count")),
        )


class TrainerApp:
    def __init__(
        self,
        debug_log_path: str | None = None,
        auto_close_ms: int | None = None,
    ) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("430x480")
        self.root.minsize(430, 480)
        self.root.configure(bg="#f4f5f1")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.backend = LightTrainerBackend()
        self.vars = {key: tk.BooleanVar(value=False) for key, *_ in FLAG_DEFS}
        self.coord_vars = {axis: tk.StringVar(value="0.000") for axis in COORD_AXES}
        self.coord_step_var = tk.StringVar(value="1.000")
        self.coord_spinboxes: dict[str, ttk.Spinbox] = {}
        self.debounced_hotkeys: set[str] = set()
        self.running = True
        self.debug_log_path = debug_log_path
        self.tick_count = 0

        self._build_style()
        self._build_ui()
        self.debug("app_start")
        self.root.after(100, self.tick)
        if auto_close_ms is not None:
            self.root.after(auto_close_ms, self.close)

    def debug(self, message: str) -> None:
        if not self.debug_log_path:
            return
        hook = self.backend.hook
        player = 0
        if self.backend.attached:
            player = self.backend.player_ptr()
        line = (
            f"{time.strftime('%H:%M:%S')} {message} "
            f"attached={self.backend.attached} "
            f"pid={self.backend.pid} "
            f"owns_hook={hook.owns_hook if hook else None} "
            f"player=0x{player:X} "
            f"error={self.backend.last_error}"
        )
        try:
            with open(self.debug_log_path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f5f1")
        style.configure("Title.TLabel", background="#f4f5f1", foreground="#18201f", font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", background="#f4f5f1", foreground="#2a3130", font=("Segoe UI", 9))
        style.configure("Small.TLabel", background="#f4f5f1", foreground="#69716f", font=("Segoe UI", 8))
        style.configure("TCheckbutton", background="#f4f5f1", foreground="#18201f", font=("Segoe UI", 10))
        style.map("TCheckbutton", background=[("active", "#f4f5f1")])
        style.configure("TButton", font=("Segoe UI", 9))
        style.configure("Coord.TSpinbox", font=("Segoe UI", 9))

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 16, 18, 14))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"{APP_NAME} v{APP_VERSION}", style="Title.TLabel").pack(anchor="w")
        self.game_label = ttk.Label(frame, text="游戏：检测中", style="Status.TLabel")
        self.game_label.pack(anchor="w", pady=(12, 0))
        self.mod_label = ttk.Label(frame, text="修改：未开启", style="Status.TLabel")
        self.mod_label.pack(anchor="w", pady=(4, 0))
        self.player_label = ttk.Label(frame, text="玩家：等待捕获", style="Small.TLabel")
        self.player_label.pack(anchor="w", pady=(4, 12))

        for key, caption, hotkey, _vk in FLAG_DEFS:
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=3)
            swatch = tk.Canvas(row, width=10, height=22, highlightthickness=0, bg="#f4f5f1")
            swatch.pack(side="left", padx=(0, 8))
            color = {
                "through": "#35a853",
                "open": "#d13b34",
                "smash": "#c9a227",
                "double": "#e2752b",
            }[key]
            swatch.create_rectangle(1, 2, 9, 20, fill=color, outline=color)
            cb = ttk.Checkbutton(
                row,
                text=f"{hotkey}    {caption}",
                variable=self.vars[key],
                command=self.on_flags_changed,
            )
            cb.pack(side="left", fill="x", expand=True)

        coord_frame = ttk.Frame(frame)
        coord_frame.pack(fill="x", pady=(14, 0))
        ttk.Label(coord_frame, text="角色坐标", style="Status.TLabel").pack(anchor="w")

        coord_row = ttk.Frame(coord_frame)
        coord_row.pack(fill="x", pady=(8, 0))
        for axis in COORD_AXES:
            group = ttk.Frame(coord_row)
            group.pack(side="left", padx=(0, 8))
            ttk.Label(group, text=axis.upper(), style="Small.TLabel").pack(anchor="w")
            spinbox = ttk.Spinbox(
                group,
                from_=-COORD_LIMIT,
                to=COORD_LIMIT,
                increment=1.0,
                textvariable=self.coord_vars[axis],
                width=10,
                format="%.3f",
                style="Coord.TSpinbox",
            )
            spinbox.pack(anchor="w")
            self.coord_spinboxes[axis] = spinbox

        step_group = ttk.Frame(coord_row)
        step_group.pack(side="left")
        ttk.Label(step_group, text="步进", style="Small.TLabel").pack(anchor="w")
        ttk.Spinbox(
            step_group,
            from_=0.001,
            to=1000.0,
            increment=0.5,
            textvariable=self.coord_step_var,
            width=8,
            format="%.3f",
            command=self.update_coordinate_increment,
            style="Coord.TSpinbox",
        ).pack(anchor="w")
        self.coord_step_var.trace_add("write", self.update_coordinate_increment)

        coord_buttons = ttk.Frame(coord_frame)
        coord_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(coord_buttons, text="读取坐标", command=self.read_coordinates).pack(side="left")
        ttk.Button(coord_buttons, text="写入坐标", command=self.write_coordinates).pack(side="left", padx=(8, 0))
        self.coord_label = ttk.Label(coord_frame, text="", style="Small.TLabel", wraplength=390)
        self.coord_label.pack(anchor="w", pady=(6, 0), fill="x")

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(16, 0))
        ttk.Button(buttons, text="全部关闭", command=self.all_off).pack(side="left")
        ttk.Button(buttons, text="重新连接", command=self.reconnect).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="关于", command=self.show_about).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="退出", command=self.close).pack(side="right")

        self.error_label = ttk.Label(frame, text="", style="Small.TLabel", wraplength=390)
        self.error_label.pack(anchor="w", pady=(14, 0), fill="x")

    def desired_flags(self) -> dict[str, bool]:
        return {key: var.get() for key, var in self.vars.items()}

    def coordinate_step(self) -> float:
        try:
            step = float(self.coord_step_var.get())
        except ValueError:
            return 1.0
        if not math.isfinite(step) or step <= 0:
            return 1.0
        return step

    def update_coordinate_increment(self, *_args: object) -> None:
        step = self.coordinate_step()
        for spinbox in self.coord_spinboxes.values():
            spinbox.configure(increment=step)

    def coordinate_values(self) -> tuple[float, float, float]:
        values: list[float] = []
        for axis in COORD_AXES:
            text = self.coord_vars[axis].get().strip()
            try:
                value = float(text)
            except ValueError as exc:
                raise TrainerError(f"{axis.upper()} 坐标不是有效数字") from exc
            if not math.isfinite(value) or abs(value) > COORD_LIMIT:
                raise TrainerError(f"{axis.upper()} 坐标超出允许范围")
            values.append(value)
        return (values[0], values[1], values[2])

    def set_coordinate_values(self, values: tuple[float, float, float]) -> None:
        for axis, value in zip(COORD_AXES, values):
            self.coord_vars[axis].set(f"{value:.3f}")

    def read_coordinates(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            values = self.backend.player_xyz()
            self.set_coordinate_values(values)
            self.coord_label.configure(text="坐标：已读取")
        except Exception as exc:
            self.coord_label.configure(text=f"坐标：{exc}")

    def write_coordinates(self) -> None:
        try:
            values = self.coordinate_values()
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            self.backend.write_player_xyz(values)
            self.coord_label.configure(text="坐标：已写入")
        except Exception as exc:
            self.coord_label.configure(text=f"坐标：{exc}")

    def on_flags_changed(self) -> None:
        try:
            self.backend.sync_flags(self.desired_flags())
        except Exception as exc:
            self.backend.last_error = str(exc)

    def all_off(self) -> None:
        for var in self.vars.values():
            var.set(False)
        self.on_flags_changed()

    def show_about(self) -> None:
        messagebox.showinfo(
            "关于",
            f"{APP_NAME} v{APP_VERSION}\n\n作者：不是吴昊的wh",
            parent=self.root,
        )

    def reconnect(self) -> None:
        self.backend.detach()
        self.backend.last_attach_attempt = 0.0
        ok = self.backend.attach_if_needed()
        self.debug(f"manual_reconnect ok={ok}")
        self.on_flags_changed()
        self.refresh_labels()

    def hotkeys(self) -> None:
        ctrl = user32.GetAsyncKeyState(VK_CONTROL) & 0x8000
        alt = user32.GetAsyncKeyState(VK_MENU) & 0x8000
        active_now: set[str] = set()
        if ctrl and alt:
            for key, _caption, _hotkey, vk in FLAG_DEFS:
                if user32.GetAsyncKeyState(vk) & 0x8000:
                    active_now.add(key)
                    if key not in self.debounced_hotkeys:
                        self.vars[key].set(not self.vars[key].get())
                        self.on_flags_changed()
        self.debounced_hotkeys = active_now

    def tick(self) -> None:
        if not self.running:
            return
        self.tick_count += 1
        try:
            self.hotkeys()
            if self.backend.attached:
                self.backend.keep_player_state(self.desired_flags())
            else:
                ok = self.backend.attach_if_needed()
                if ok or self.tick_count <= 5 or self.tick_count % 20 == 0:
                    self.debug(f"attach_attempt ok={ok}")
                if self.backend.attached:
                    self.backend.sync_flags(self.desired_flags())
        except Exception as exc:
            self.backend.last_error = str(exc)
            self.debug(f"tick_exception {type(exc).__name__}")
        self.refresh_labels()
        if self.tick_count <= 5 or self.tick_count % 20 == 0:
            self.debug("refresh")
        self.root.after(50, self.tick)

    def refresh_labels(self) -> None:
        flags = self.desired_flags()
        any_enabled = any(flags.values())
        if self.backend.attached:
            assert self.backend.pid is not None
            self.game_label.configure(text=f"游戏：已连接 PID {self.backend.pid}")
            self.mod_label.configure(text="修改：已开启" if any_enabled else "修改：待命")
            player = self.backend.player_ptr()
            if player:
                self.player_label.configure(text=f"玩家：已捕获 0x{player:X}")
            else:
                self.player_label.configure(text="玩家：等待进入能力状态")
            self.error_label.configure(text="")
        else:
            self.game_label.configure(text=f"游戏：等待 {PROCESS_NAME}")
            self.mod_label.configure(text="修改：未连接")
            self.player_label.configure(text="玩家：等待捕获")
            if self.backend.last_error:
                self.error_label.configure(text=f"状态：{self.backend.last_error}")
            else:
                self.error_label.configure(text="先启动游戏，再打开或保持本工具运行。")

    def close(self) -> None:
        self.running = False
        self.debug("app_close")
        self.backend.detach()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_self_test() -> int:
    pick_addr = 0x1402AEF49
    gate_addr = 0x1402AF0CC
    remote_base = 0x140500000
    code, labels = build_remote_code(
        remote_base,
        pick_return=pick_addr + PICK_RETURN_DELTA,
        gate_skip=gate_addr + GATE_SKIP_DELTA,
        gate_through=gate_addr + GATE_THROUGH_DELTA,
        gate_r14_continue=gate_addr + GATE_R14_CONTINUE_DELTA,
    )
    assert labels["pick_hook"] == remote_base
    assert "through_enabled" in labels
    assert len(make_jmp_patch(pick_addr, labels["pick_hook"], PICK_PATCH_LEN)) == PICK_PATCH_LEN
    assert len(make_jmp_patch(gate_addr, labels["gate_hook"], GATE_PATCH_LEN)) == GATE_PATCH_LEN
    print(f"self-test ok: remote_code={len(code)} bytes labels={len(labels)}")

    exe_path = os.path.join(os.getcwd(), PROCESS_NAME)
    if os.path.exists(exe_path):
        with open(exe_path, "rb") as fh:
            data = fh.read()
        pick_count = data.count(PICK_SIGNATURE)
        gate_count = data.count(GATE_SIGNATURE)
        print(f"disk AOB: pick={pick_count} gate={gate_count}")
        if pick_count != 1 or gate_count != 1:
            return 2
    return 0


def run_diagnose() -> int:
    lines: list[str] = []
    pid = find_process_id(PROCESS_NAME)
    lines.append(f"process={PROCESS_NAME}")
    lines.append(f"pid={pid}")
    if pid is not None:
        try:
            mem = ProcessMemory(pid)
            try:
                module = get_module_info(pid, PROCESS_NAME)
                lines.append(f"module_base=0x{module.base:X}")
                lines.append(f"module_size=0x{module.size:X}")
                for name, rva, signature in (
                    ("pick", PICK_RVA, PICK_SIGNATURE),
                    ("gate", GATE_RVA, GATE_SIGNATURE),
                ):
                    addr = module.base + rva
                    live = mem.read(addr, len(signature))
                    lines.append(f"{name}_addr=0x{addr:X}")
                    lines.append(f"{name}_live={live.hex(' ')}")
                    lines.append(f"{name}_matches_original={live == signature}")
                    dst = decode_rel32_jmp(addr, live)
                    if dst is not None:
                        lines.append(f"{name}_jmp_dst=0x{dst:X}")
            finally:
                mem.close()
        except Exception as exc:
            lines.append(f"probe_error={exc}")

    backend = LightTrainerBackend()
    ok = backend.attach_if_needed()
    lines.append(f"backend_attach={ok}")
    lines.append(f"backend_error={backend.last_error}")
    if backend.hook is not None:
        lines.append(f"owns_hook={backend.hook.owns_hook}")
        lines.append(f"remote_base=0x{backend.hook.remote_base:X}")
        lines.append(f"player_ptr=0x{backend.player_ptr():X}")
    backend.detach()

    log_path = os.path.join(os.getcwd(), "SinkingStarHero_diagnose.txt")
    if "--diagnose" in sys.argv:
        index = sys.argv.index("--diagnose")
        if index + 1 < len(sys.argv) and not sys.argv[index + 1].startswith("--"):
            log_path = sys.argv[index + 1]
    with open(log_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return 0 if ok else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return run_self_test()
    if "--diagnose" in sys.argv:
        return run_diagnose()
    debug_log_path = None
    if "--debug-log" in sys.argv:
        index = sys.argv.index("--debug-log")
        if index + 1 < len(sys.argv) and not sys.argv[index + 1].startswith("--"):
            debug_log_path = sys.argv[index + 1]

    auto_close_ms = None
    if "--debug-exit-ms" in sys.argv:
        index = sys.argv.index("--debug-exit-ms")
        if index + 1 < len(sys.argv):
            try:
                auto_close_ms = max(250, int(sys.argv[index + 1]))
            except ValueError:
                auto_close_ms = None

    app = TrainerApp(debug_log_path=debug_log_path, auto_close_ms=auto_close_ms)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
