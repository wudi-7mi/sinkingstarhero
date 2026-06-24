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
import webbrowser
from dataclasses import dataclass
from tkinter import ttk
from ctypes import wintypes


APP_NAME = "SinkingStarHero"
APP_VERSION = "0.4.0"
GITHUB_REPOSITORY_URL = "https://github.com/wudi-7mi/sinkingstarhero"
PROCESS_NAME = "sinking_star.exe"
WINDOW_WIDTH = 920
WINDOW_HEIGHT = 860
WINDOW_MIN_WIDTH = 760
WINDOW_MIN_HEIGHT = 560

OPEN_CONSOLE_ARG = "-open_console"
OPEN_CONSOLE_STRING_RVA = 0x6407C8
OPEN_CONSOLE_TABLE_RVA = 0x5C0EE0
OPEN_CONSOLE_FIELD_OFFSET = 0x11
PLAYTEST_FLAG_RVA = 0x9ACB82
RUNNING_PACKAGED_FLAG_RVA = 0x72EF17

CURRENT_LEVEL_SET_RVA = 0x9ACF58
CURRENT_LEVEL_INDEX_RVA = 0x9ACBA0
PENDING_LEVEL_SET_RVA = 0x9ACF60
PENDING_LEVEL_INDEX_RVA = 0x72E070
TRANSITION_STATE_RVA = 0x72E9D0
TRANSITION_PHASE_RVA = 0x9AECD0
TRANSITION_DELAY_RVA = 0x9AC2E0
TRANSITION_PROGRESS_RVA = 0x9AC2E8
LEVEL_SET_CATALOG_CAPACITY_RVA = 0xEF2340
LEVEL_SET_CATALOG_TABLE_RVA = 0xEF2368
LEVEL_SET_CATALOG_ENTRY_SIZE = 0x20
MAX_LEVEL_SET_CATALOG_ENTRIES = 4096
MAX_LEVELS_PER_SET = 1024
TRANSITION_STATE_SWITCH_LEVEL = 4
TRANSITION_PHASE_REQUESTED = 3
CURRENT_CAMPAIGN_NAME_RVA = 0x9AC8F0
CAMPAIGN_LOAD_RVA = 0x048880
CAMPAIGN_SAVE_CURRENT_RVA = 0x154860
ENTITY_MANAGER_SAVE_RVA = 0x1B5EA0
SAVE_QUEUE_COUNT_RVA = 0x9ACC98
RELOAD_SAVE_SETTLE_FRAMES = 60
MAIN_LOOP_RELOAD_HOOK_RVA = 0x1CA8B3
MAIN_LOOP_RELOAD_HOOK_SIGNATURE = bytes.fromhex("48 8B 05 F6 40 56 00")
MAIN_LOOP_RELOAD_HOOK_LEN = len(MAIN_LOOP_RELOAD_HOOK_SIGNATURE)
MAIN_LOOP_RELOAD_RETURN_DELTA = MAIN_LOOP_RELOAD_HOOK_LEN
POST_UPDATE_STATE_RVA = 0x72E9B0

RELOAD_STATUS_IDLE = 0
RELOAD_STATUS_QUEUED = 1
RELOAD_STATUS_RUNNING = 2
RELOAD_STATUS_OK = 3
RELOAD_STATUS_NO_CAMPAIGN = 4
RELOAD_STATUS_BUSY = 5
RELOAD_STATUS_SAVING = 6
RELOAD_STATUS_WAITING_SAVE = 7
RELOAD_STATUS_LOADING = 8
RELOAD_STATUS_MESSAGES = {
    RELOAD_STATUS_IDLE: "空闲",
    RELOAD_STATUS_QUEUED: "已排队",
    RELOAD_STATUS_RUNNING: "执行中",
    RELOAD_STATUS_OK: "已执行",
    RELOAD_STATUS_NO_CAMPAIGN: "当前存档名未知",
    RELOAD_STATUS_BUSY: "游戏正在过渡中",
    RELOAD_STATUS_SAVING: "正在保存当前状态",
    RELOAD_STATUS_WAITING_SAVE: "等待保存落盘",
    RELOAD_STATUS_LOADING: "正在重新加载",
}

LEVEL_STATUS_MAP_PTR_RVA = 0x9ACE80
LEVEL_STATUS_MAP_CAPACITY = 0x08
LEVEL_STATUS_MAP_TABLE = 0x30
LEVEL_STATUS_MAP_ENTRY_SIZE = 0x20
LEVEL_STATUS_MAP_ENTRY_HASH = 0x00
LEVEL_STATUS_MAP_ENTRY_KEY_LEN = 0x08
LEVEL_STATUS_MAP_ENTRY_KEY_PTR = 0x10
LEVEL_STATUS_MAP_ENTRY_FLAGS = 0x18
LEVEL_STATUS_HASH_MIN_USED = 2
LEVEL_STATUS_SOLVED_FLAG = 0x01
MAX_LEVEL_STATUS_ENTRIES = 4096

LEVEL_SET_NAME_LEN = 0x00
LEVEL_SET_NAME_PTR = 0x08
LEVEL_SET_COUNT = 0x38
LEVEL_SET_TABLE = 0x40
LEVEL_SET_ENTRY_SIZE = 0x10

BUILTIN_LEVEL_SETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "heroes1",
        (
            "heroes1_1",
            "heroes1_2_v2",
            "heroes1_3",
            "heroes1_4",
            "heroes1_4.5",
            "heroes1_5_v2",
            "heroes1_7_v2",
            "heroes1_6",
            "heroes1_7.5",
            "heroes1_8_v2",
            "heroes1_10_inv_v4_b",
            "heroes1_9",
            "heroes1_11_v2",
            "heroes1_13_v2",
            "heroes1_12_v2_alt",
            "heroes1_15",
            "heroes1_16_v3",
            "heroes1_17",
            "heroes1_18",
            "heroes1_19_jail",
            "heroes1_21_v3",
        ),
    ),
    (
        "heroes2",
        (
            "heroes2_2b",
            "heroes2_2",
            "heroes2_thief_goblin",
            "heroes2_3_v2",
            "heroes2_5_altE",
            "heroes2_5_no_crystal",
            "heroes2_5.5v5",
            "heroes2_6_v3",
            "heroes2_9",
            "heroes2_10a_intro",
            "heroes2_10a",
            "heroes2_3monster",
            "heroes2_10",
            "heroes2_11_v2_easier",
            "heroes2_12_v2",
            "heroes2_11_v2",
            "heroes2_10.5",
            "one_fire_v2",
            "heroes2_13",
            "heroes2_14",
            "heroes2_15",
            "heroes2_reprise",
            "heroes2_16v4",
            "heroes2_18",
            "mosh_pit_small",
            "heroes2_17_intro",
            "heroes2_17",
            "heroes2_20",
            "heroes2_21b",
            "heroes2_22_v2",
        ),
    ),
    (
        "heroes3",
        (
            "heroes3_10",
            "heroes3_11_v2",
            "druid_and_dragon",
            "wizard_and_druid_alt_5",
            "heroes3_15_v4",
            "heroes3_1_v3",
            "heroes3_2_v4",
            "heroes3_3_v2",
            "heroes3_4",
            "heroes3_5",
        ),
    ),
    (
        "heroes_and_water",
        (
            "dipping_your_toes_in",
            "crystal_bridges",
            "push_and_pull_zach",
            "quadrants_follow_up",
            "quadrants",
            "drowner",
            "surrounded",
            "dont_push_the_button",
            "detonator",
            "a_wiz_out_of_water",
            "island_hopping",
            "dunk_tank_alt",
            "gully_alt",
            "easy_situation_v2",
            "one_vs_three",
        ),
    ),
    ("intro", ("intro",)),
    (
        "mirror",
        (
            "mirror_1",
            "mirror_2",
            "mirror_3",
            "mirror_4",
            "mirror_5",
            "mirror_6_alt",
            "mirror_7",
            "mirror_8_v5",
            "mirror_11",
            "mirror_12",
            "mirror_13",
            "mirror_14",
            "mirror_15",
            "mirror_19",
            "mirror_17",
            "mirror_sink",
            "mirror_20",
            "mirror_18",
            "mirror_21",
            "mirror_22_v2",
            "mirror_factory_v2",
            "mirror_pals",
            "walk_it_over",
            "mirror_10_alt2",
            "mundane_mirror",
            "mirror_10_b_v2",
            "mirror_10_d",
        ),
    ),
    ("overworld", ("overworld",)),
    ("promesst1_and_2", ("promesst1_streamlined",)),
    ("worlds_collide", ("worlds_collide_heroes_and_mirrors_v3",)),
)

BUILTIN_EXTRA_LEVEL_NAMES = (
    "env_corral",
    "ingame_glyphs",
    "ingame_particles",
    "menu",
    "menu_demo_startup",
    "preload_material_scene",
)

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
PLAYER_LEVEL = 0xF0
PLAYER_COORD_OFFSETS = (0x00, 0x04, 0x08)
PLAYER_THETA_TARGET = 0x33C
FRONT_GRID_STEP = 1.0
COORD_AXES = ("x", "y", "z")
COORD_LIMIT = 1_000_000.0

ENTITY_ID = 0x100
ENTITY_TYPE = 0x108
ENTITY_THETA_CURRENT = 0x44
ENTITY_THETA_TARGET = 0x48
ENTITY_MESH = 0x88
ENTITY_ORIENTATION_Z = 0x20
ENTITY_ORIENTATION_W = 0x24
ENTITY_TYPE_ID = 0x04
ENTITY_TYPE_SIZE = 0x08
ENTITY_TYPE_NAME_LEN = 0x10
ENTITY_TYPE_NAME = 0x18
ENTITY_KIND_ENTITY = 7
CURRENT_ENTITY_MANAGER_RVA = 0x9ACB50
LEVEL_OBJECT_COUNT = 0x370
LEVEL_OBJECT_ARRAY = 0x378
MAX_LEVEL_OBJECT_COUNT = 20000
MAX_ENTITY_TYPE_NAME_LEN = 96
OBJECT_SCOPE_ALL = "全部区域"
OBJECT_SCOPE_RADIUS = "附近半径"
OBJECT_RADIUS_DEFAULT = 8.0
OBJECT_APPEARANCE_MAX_LEN = 256
ENTITY_FILE_MAGIC = b"enty"
PACKAGE_MAGIC = b"simp"
PACKAGE_TOC_MAGIC = b"toc!"
SPAWN_COORD_FIELD_IDS = {
    "base_x": 0x0000,
    "base_y": 0x0001,
    "base_z": 0x0002,
    "out_x": 0x0021,
    "out_y": 0x0022,
    "out_z": 0x0023,
}

RUNTIME_CONTEXT_RVA = 0x731110
SPAWN_DYNAMIC_ENTITY_ID_RVA = 0x72E034
SPAWN_DYNAMIC_ENTITY_ID_MASK = 0x3FD00000
SPAWN_CREATE_ENTITY_RVA = 0x347900
SPAWN_INIT_ENTITY_RVA = 0x0FFF60
SPAWN_REGISTER_ENTITY_RVA = 0x2A39D0
SPAWN_APPLY_DIFF_RVA = 0x17B410
SPAWN_REMOTE_BLOCK_SIZE = 0x4000
SPAWN_REMOTE_TIMEOUT_MS = 5000
SPAWN_REQ_CTX = 0x00
SPAWN_REQ_MANAGER = 0x08
SPAWN_REQ_TYPE = 0x10
SPAWN_REQ_ENTITY_ID = 0x18
SPAWN_REQ_X = 0x1C
SPAWN_REQ_Y = 0x20
SPAWN_REQ_Z = 0x24
SPAWN_REQ_STATUS = 0x28
SPAWN_REQ_OUT_ENTITY = 0x30
SPAWN_REQ_BEFORE_COUNT = 0x38
SPAWN_REQ_AFTER_COUNT = 0x40
SPAWN_REQ_CREATE_FUNC = 0x48
SPAWN_REQ_INIT_FUNC = 0x50
SPAWN_REQ_REGISTER_FUNC = 0x58
SPAWN_REQ_APPLY_DIFF_FUNC = 0x60
SPAWN_REQ_DIFF_SIZE = 0x68
SPAWN_REQ_DIFF_PTR = 0x70
SPAWN_REQ_HEADER_VALUE = 0x78
SPAWN_REQ_TYPE_AUX = 0x80
SPAWN_REQ_SIZE = 0x90
SPAWN_STATUS_OK = 0
SPAWN_STATUS_NO_PARAM = 1
SPAWN_STATUS_NO_CONTEXT = 2
SPAWN_STATUS_NO_MANAGER = 3
SPAWN_STATUS_NO_TYPE = 4
SPAWN_STATUS_CREATE_FAILED = 5
SPAWN_STATUS_APPLY_FAILED = 6
SPAWN_STATUS_MESSAGES = {
    SPAWN_STATUS_OK: "ok",
    SPAWN_STATUS_NO_PARAM: "远程参数为空",
    SPAWN_STATUS_NO_CONTEXT: "运行时上下文为空",
    SPAWN_STATUS_NO_MANAGER: "对象管理器为空",
    SPAWN_STATUS_NO_TYPE: "对象类型为空",
    SPAWN_STATUS_CREATE_FAILED: "游戏构造函数未返回实体",
    SPAWN_STATUS_APPLY_FAILED: "对象属性 diff 应用失败",
}

LEVEL_FREEZER_COUNT = 0x7E0
LEVEL_FREEZER_ARRAY = 0x7E8
FREEZER_ID = ENTITY_ID
FREEZER_TYPE = ENTITY_TYPE
FREEZER_OPENED = 0x338
FREEZER_TYPE_RVA = 0x5C70C0
FREEZER_OPEN_RADIUS = 8.0
MAX_FREEZER_COUNT = 4096
OPEN_FREEZER_HOTKEY = ("open_freezer", "Ctrl+Alt+5", 0x35)

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
PROCESS_CREATE_THREAD = 0x0002
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
SYNCHRONIZE = 0x00100000
PROCESS_RIGHTS = (
    PROCESS_QUERY_INFORMATION
    | PROCESS_CREATE_THREAD
    | PROCESS_VM_OPERATION
    | PROCESS_VM_READ
    | PROCESS_VM_WRITE
    | SYNCHRONIZE
)

MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
MEM_RELEASE = 0x00008000

PAGE_EXECUTE_READWRITE = 0x40

WAIT_OBJECT_0 = 0x00000000
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
kernel32.CreateRemoteThread.argtypes = (
    HANDLE,
    LPVOID,
    SIZE_T,
    LPVOID,
    LPVOID,
    DWORD,
    ctypes.POINTER(DWORD),
)
kernel32.CreateRemoteThread.restype = HANDLE
kernel32.GetExitCodeThread.argtypes = (HANDLE, ctypes.POINTER(DWORD))
kernel32.GetExitCodeThread.restype = BOOL
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
    post_update_return: int,
    campaign_load: int,
    campaign_save_current: int,
    entity_manager_save: int,
    runtime_context: int,
    current_entity_manager: int,
    pending_level_set: int,
    transition_phase: int,
    save_queue_count: int,
    post_update_state: int,
) -> tuple[bytes, dict[str, int]]:
    b = CodeBuilder()

    def mov_rax_imm(value: int) -> None:
        b.emit(b"\x48\xB8" + struct.pack("<Q", value))

    def mov_rcx_imm(value: int) -> None:
        b.emit(b"\x48\xB9" + struct.pack("<Q", value))

    def mov_rdx_imm(value: int) -> None:
        b.emit(b"\x48\xBA" + struct.pack("<Q", value))

    def set_reload_status(status: int) -> None:
        b.rip(b"\xC7\x05", "reload_status", struct.pack("<I", status))

    def clear_reload_request() -> None:
        b.rip(b"\xC6\x05", "reload_requested", b"\x00")

    def set_reload_phase(phase: int) -> None:
        b.rip(b"\xC6\x05", "reload_phase", bytes((phase,)))

    def set_reload_wait_frames(frames: int) -> None:
        b.rip(b"\xC7\x05", "reload_wait_frames", struct.pack("<I", frames))

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

    b.label("post_update_hook")
    b.rip(b"\x48\xFF\x05", "post_update_count")
    b.emit(b"\x51")
    b.emit(b"\x52")
    b.emit(b"\x41\x50")
    b.emit(b"\x41\x51")
    b.emit(b"\x41\x52")
    b.emit(b"\x41\x53")
    b.emit(b"\x48\x81\xEC\x80\x00\x00\x00")
    b.emit(b"\x0F\x11\x44\x24\x20")
    b.emit(b"\x0F\x11\x4C\x24\x30")
    b.emit(b"\x0F\x11\x54\x24\x40")
    b.emit(b"\x0F\x11\x5C\x24\x50")
    b.emit(b"\x0F\x11\x64\x24\x60")
    b.emit(b"\x0F\x11\x6C\x24\x70")

    b.rip(b"\x80\x3D", "reload_phase", b"\x00")
    b.jcc_label(0x85, "reload_continue_phase")

    b.rip(b"\x80\x3D", "reload_requested", b"\x00")
    b.jcc_label(0x84, "post_update_no_reload")

    mov_rax_imm(transition_phase)
    b.emit(b"\x48\x83\x38\x02")
    b.jcc_label(0x82, "reload_begin_save")
    clear_reload_request()
    set_reload_status(RELOAD_STATUS_BUSY)
    b.jmp_label("post_update_no_reload")

    b.label("reload_begin_save")
    b.rip(b"\x48\x83\x3D", "campaign_name_len", b"\x00")
    b.jcc_label(0x84, "reload_no_campaign")
    b.rip(b"\x48\x83\x3D", "campaign_name_ptr", b"\x00")
    b.jcc_label(0x84, "reload_no_campaign")

    clear_reload_request()
    set_reload_status(RELOAD_STATUS_SAVING)
    set_reload_wait_frames(0)
    b.rip(b"\xC6\x05", "reload_out_bool", b"\x00")

    mov_rcx_imm(runtime_context)
    mov_rax_imm(campaign_save_current)
    b.emit(b"\xFF\xD0")

    mov_rax_imm(current_entity_manager)
    b.emit(b"\x48\x8B\x10")
    b.emit(b"\x48\x85\xD2")
    b.jcc_label(0x84, "reload_skip_entity_save")
    mov_rcx_imm(runtime_context)
    b.emit(b"\x45\x33\xC0")
    mov_rax_imm(entity_manager_save)
    b.emit(b"\xFF\xD0")
    b.label("reload_skip_entity_save")

    set_reload_phase(1)
    set_reload_status(RELOAD_STATUS_WAITING_SAVE)
    b.jmp_label("post_update_no_reload")

    b.label("reload_continue_phase")
    b.rip(b"\x80\x3D", "reload_phase", b"\x01")
    b.jcc_label(0x84, "reload_wait_save")
    set_reload_phase(0)
    set_reload_wait_frames(0)
    b.jmp_label("post_update_no_reload")

    b.label("reload_wait_save")
    mov_rax_imm(transition_phase)
    b.emit(b"\x48\x83\x38\x02")
    b.jcc_label(0x82, "reload_check_save_queue")
    set_reload_status(RELOAD_STATUS_BUSY)
    b.jmp_label("post_update_no_reload")

    b.label("reload_check_save_queue")
    mov_rax_imm(save_queue_count)
    b.emit(b"\x48\x83\x38\x00")
    b.jcc_label(0x84, "reload_save_queue_empty")
    set_reload_wait_frames(0)
    set_reload_status(RELOAD_STATUS_WAITING_SAVE)
    b.jmp_label("post_update_no_reload")

    b.label("reload_save_queue_empty")
    b.rip(b"\xFF\x05", "reload_wait_frames")
    b.rip(b"\x83\x3D", "reload_wait_frames", bytes((RELOAD_SAVE_SETTLE_FRAMES,)))
    b.jcc_label(0x82, "reload_still_settling")
    b.jmp_label("reload_do_load")

    b.label("reload_still_settling")
    set_reload_status(RELOAD_STATUS_WAITING_SAVE)
    b.jmp_label("post_update_no_reload")

    b.label("reload_do_load")
    b.rip(b"\x48\x83\x3D", "campaign_name_len", b"\x00")
    b.jcc_label(0x84, "reload_no_campaign")
    b.rip(b"\x48\x83\x3D", "campaign_name_ptr", b"\x00")
    b.jcc_label(0x84, "reload_no_campaign")

    set_reload_status(RELOAD_STATUS_LOADING)
    b.rip(b"\xC6\x05", "reload_out_bool", b"\x00")

    mov_rax_imm(pending_level_set)
    b.emit(b"\x48\xC7\x00\x00\x00\x00\x00")
    mov_rax_imm(transition_phase)
    b.emit(b"\x48\xC7\x00\x00\x00\x00\x00")

    mov_rcx_imm(runtime_context)
    b.rip(b"\x48\x8D\x15", "campaign_name_len")
    b.emit(b"\x41\xB8\x01\x00\x00\x00")
    b.rip(b"\x4C\x8D\x0D", "reload_out_bool")
    mov_rax_imm(campaign_load)
    b.emit(b"\xFF\xD0")
    set_reload_phase(0)
    set_reload_wait_frames(0)
    set_reload_status(RELOAD_STATUS_OK)
    b.rip(b"\x48\xFF\x05", "reload_done_count")
    b.jmp_label("post_update_no_reload")

    b.label("reload_no_campaign")
    clear_reload_request()
    set_reload_phase(0)
    set_reload_wait_frames(0)
    set_reload_status(RELOAD_STATUS_NO_CAMPAIGN)
    b.label("post_update_no_reload")
    b.emit(b"\x0F\x10\x6C\x24\x70")
    b.emit(b"\x0F\x10\x64\x24\x60")
    b.emit(b"\x0F\x10\x5C\x24\x50")
    b.emit(b"\x0F\x10\x54\x24\x40")
    b.emit(b"\x0F\x10\x4C\x24\x30")
    b.emit(b"\x0F\x10\x44\x24\x20")
    b.emit(b"\x48\x81\xC4\x80\x00\x00\x00")
    b.emit(b"\x41\x5B")
    b.emit(b"\x41\x5A")
    b.emit(b"\x41\x59")
    b.emit(b"\x41\x58")
    b.emit(b"\x5A")
    b.emit(b"\x59")
    mov_rax_imm(post_update_state)
    b.emit(b"\x48\x8B\x00")
    b.jmp_abs(post_update_return)

    b.align(8)
    b.label("player_ptr")
    b.dq(0)
    b.label("pick_count")
    b.dq(0)
    b.label("gate_count")
    b.dq(0)
    b.label("force_count")
    b.dq(0)
    b.label("post_update_count")
    b.dq(0)
    b.label("reload_request_count")
    b.dq(0)
    b.label("reload_done_count")
    b.dq(0)
    b.label("through_enabled")
    b.db(0)
    b.label("open_enabled")
    b.db(0)
    b.label("smash_enabled")
    b.db(0)
    b.label("double_enabled")
    b.db(0)
    b.label("reload_requested")
    b.db(0)
    b.label("reload_phase")
    b.db(0)
    b.label("reload_out_bool")
    b.db(0)
    b.align(4)
    b.label("reload_status")
    b.emit(struct.pack("<I", RELOAD_STATUS_IDLE))
    b.label("reload_wait_frames")
    b.emit(struct.pack("<I", 0))
    b.align(8)
    b.label("campaign_name_len")
    b.dq(0)
    b.label("campaign_name_ptr")
    b.dq(0)
    b.label("campaign_name_buffer")
    b.emit(b"\x00" * 256)

    return b.finalize(remote_base)

def build_runtime_spawn_code(remote_base: int) -> tuple[bytes, dict[str, int]]:
    b = CodeBuilder()

    def set_status(status: int) -> None:
        b.emit(b"\xC7\x46" + bytes((SPAWN_REQ_STATUS,)) + struct.pack("<I", status))

    def fail_label(name: str, status: int) -> None:
        b.label(name)
        set_status(status)
        b.emit(b"\xB8" + struct.pack("<I", status))
        b.jmp_label("spawn_cleanup")

    def store_one_axis(src_disp: int, *dst_disps: int) -> None:
        b.emit(b"\xF3\x0F\x10\x46" + bytes((src_disp,)))
        for dst_disp in dst_disps:
            if dst_disp == 0:
                b.emit(b"\xF3\x0F\x11\x03")
            elif 0 <= dst_disp <= 0x7F:
                b.emit(b"\xF3\x0F\x11\x43" + bytes((dst_disp,)))
            else:
                b.emit(b"\xF3\x0F\x11\x83" + struct.pack("<i", dst_disp))

    def store_coordinates() -> None:
        store_one_axis(SPAWN_REQ_X, 0x00, 0xA0, 0x1D8)
        store_one_axis(SPAWN_REQ_Y, 0x04, 0xA4, 0x1DC)
        store_one_axis(SPAWN_REQ_Z, 0x08, 0xA8, 0x1E0)

    def call_apply_diff() -> None:
        b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_APPLY_DIFF_FUNC,)))
        b.emit(b"\x48\x85\xC0")
        b.jcc_label(0x84, "skip_apply_diff")
        b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_DIFF_SIZE,)))
        b.emit(b"\x48\x89\x4C\x24\x50")
        b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_DIFF_PTR,)))
        b.emit(b"\x48\x89\x4C\x24\x58")
        b.emit(b"\xC6\x44\x24\x60\x00")
        b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_CTX,)))
        b.emit(b"\x48\x8B\x93" + struct.pack("<i", ENTITY_TYPE))
        b.emit(b"\x49\x89\xD8")
        b.emit(b"\x45\x31\xC9")
        b.emit(b"\x48\x8D\x44\x24\x50")
        b.emit(b"\x48\x89\x44\x24\x20")
        b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_HEADER_VALUE,)))
        b.emit(b"\x48\x89\x44\x24\x28")
        b.emit(b"\x48\x8B\x86" + struct.pack("<i", SPAWN_REQ_TYPE_AUX))
        b.emit(b"\x48\x89\x44\x24\x30")
        b.emit(b"\x48\xC7\x44\x24\x38\x00\x00\x00\x00")
        b.emit(b"\x48\xC7\x44\x24\x40\x01\x00\x00\x00")
        b.emit(b"\x48\x8D\x44\x24\x60")
        b.emit(b"\x48\x89\x44\x24\x48")
        b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_APPLY_DIFF_FUNC,)))
        b.emit(b"\xFF\xD0")
        b.emit(b"\x80\x7C\x24\x60\x00")
        b.jcc_label(0x84, "fail_apply_failed")
        b.label("skip_apply_diff")

    b.label("spawn_entry")
    b.emit(b"\x53")  # push rbx
    b.emit(b"\x56")  # push rsi
    b.emit(b"\x57")  # push rdi
    b.emit(b"\x48\x81\xEC\x80\x00\x00\x00")
    b.emit(b"\x48\x89\xCE")
    b.emit(b"\x48\x85\xF6")
    b.jcc_label(0x84, "fail_no_param")

    set_status(0xFFFFFFFF)
    b.emit(b"\x48\xC7\x46" + bytes((SPAWN_REQ_OUT_ENTITY,)) + b"\x00\x00\x00\x00")
    b.emit(b"\x48\xC7\x46" + bytes((SPAWN_REQ_BEFORE_COUNT,)) + b"\x00\x00\x00\x00")
    b.emit(b"\x48\xC7\x46" + bytes((SPAWN_REQ_AFTER_COUNT,)) + b"\x00\x00\x00\x00")

    b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_CTX,)))
    b.emit(b"\x48\x85\xC9")
    b.jcc_label(0x84, "fail_no_context")
    b.emit(b"\x48\x8B\x56" + bytes((SPAWN_REQ_MANAGER,)))
    b.emit(b"\x48\x85\xD2")
    b.jcc_label(0x84, "fail_no_manager")
    b.emit(b"\x4C\x8B\x46" + bytes((SPAWN_REQ_TYPE,)))
    b.emit(b"\x4D\x85\xC0")
    b.jcc_label(0x84, "fail_no_type")

    b.emit(b"\x48\x8B\x82" + struct.pack("<i", LEVEL_OBJECT_COUNT))
    b.emit(b"\x48\x89\x46" + bytes((SPAWN_REQ_BEFORE_COUNT,)))
    b.emit(b"\x44\x8B\x4E" + bytes((SPAWN_REQ_ENTITY_ID,)))
    b.emit(b"\x48\x8D\x46" + bytes((SPAWN_REQ_OUT_ENTITY,)))
    b.emit(b"\x48\x89\x44\x24\x20")
    b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_CREATE_FUNC,)))
    b.emit(b"\xFF\xD0")

    b.emit(b"\x48\x8B\x5E" + bytes((SPAWN_REQ_OUT_ENTITY,)))
    b.emit(b"\x48\x85\xDB")
    b.jcc_label(0x84, "fail_create_failed")

    b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_CTX,)))
    b.emit(b"\x48\x89\xDA")
    b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_INIT_FUNC,)))
    b.emit(b"\xFF\xD0")

    call_apply_diff()
    store_coordinates()

    b.emit(b"\x48\x8B\x4E" + bytes((SPAWN_REQ_CTX,)))
    b.emit(b"\x48\x8B\x56" + bytes((SPAWN_REQ_MANAGER,)))
    b.emit(b"\x49\x89\xD8")
    b.emit(b"\x48\x8B\x46" + bytes((SPAWN_REQ_REGISTER_FUNC,)))
    b.emit(b"\xFF\xD0")

    store_coordinates()

    b.emit(b"\x8B\x83" + struct.pack("<i", ENTITY_ID))
    b.emit(b"\x89\x46" + bytes((SPAWN_REQ_ENTITY_ID,)))
    b.emit(b"\x48\x8B\x56" + bytes((SPAWN_REQ_MANAGER,)))
    b.emit(b"\x48\x8B\x82" + struct.pack("<i", LEVEL_OBJECT_COUNT))
    b.emit(b"\x48\x89\x46" + bytes((SPAWN_REQ_AFTER_COUNT,)))
    set_status(SPAWN_STATUS_OK)
    b.emit(b"\x31\xC0")
    b.jmp_label("spawn_cleanup")

    b.label("fail_no_param")
    b.emit(b"\xB8" + struct.pack("<I", SPAWN_STATUS_NO_PARAM))
    b.jmp_label("spawn_cleanup")
    fail_label("fail_no_context", SPAWN_STATUS_NO_CONTEXT)
    fail_label("fail_no_manager", SPAWN_STATUS_NO_MANAGER)
    fail_label("fail_no_type", SPAWN_STATUS_NO_TYPE)
    fail_label("fail_create_failed", SPAWN_STATUS_CREATE_FAILED)
    fail_label("fail_apply_failed", SPAWN_STATUS_APPLY_FAILED)

    b.label("spawn_cleanup")
    b.emit(b"\x48\x81\xC4\x80\x00\x00\x00")
    b.emit(b"\x5F")
    b.emit(b"\x5E")
    b.emit(b"\x5B")
    b.emit(b"\xC3")

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
    post_update_addr: int
    remote_base: int
    remote_size: int
    labels: dict[str, int]
    original_pick: bytes
    original_gate: bytes
    original_post_update: bytes
    owns_hook: bool


@dataclass
class FreezerOpenResult:
    address: int
    freezer_id: int
    distance: float
    position: tuple[float, float, float]


@dataclass
class EntityTypeInfo:
    address: int
    type_id: int
    type_size: int
    name: str


@dataclass(frozen=True)
class SpawnableEntityType:
    name: str
    address: int
    type_id: int
    type_size: int
    live_count: int
    package_count: int
    level_count: int = 0
    runtime: bool = False


@dataclass(frozen=True)
class SpawnEntityTemplate:
    level_name: str
    entity_type: str
    entity_id: int
    header_value: int
    type_aux: int
    diff: bytes


@dataclass(frozen=True)
class PackageEntityTypeSummary:
    name: str
    record_count: int
    level_count: int


@dataclass
class CoordinateObject:
    address: int
    source: str
    index: int
    entity_id: int
    type_info: EntityTypeInfo
    position: tuple[float, float, float]
    direction: float | None
    appearance: str
    distance: float
    is_player: bool


@dataclass
class LevelState:
    level_set: str
    level_index: int
    level_name: str
    pending_level_set: str
    pending_level_index: int
    transition_state: int
    transition_phase: int


@dataclass(frozen=True)
class RuntimeLevelRoute:
    level_set: str
    level_index: int
    level_name: str
    level_set_ptr: int


@dataclass(frozen=True)
class LevelSwitchResult:
    level_set: str
    level_index: int
    level_name: str
    level_set_ptr: int
    transition_state: int
    transition_phase: int


@dataclass(frozen=True)
class LevelCompletion:
    level_name: str
    flags: int

    @property
    def solved(self) -> bool:
        return bool(self.flags & LEVEL_STATUS_SOLVED_FLAG)


@dataclass
class ConsoleSwitchInfo:
    open_console_string: str
    open_console_table_offset: int
    playtest_enabled: bool
    running_packaged: bool


@dataclass(frozen=True)
class PackageEntry:
    name: str
    offset: int
    size: int


@dataclass(frozen=True)
class EntityFileType:
    name: str
    aux: int


@dataclass(frozen=True)
class EntityFileRecord:
    entity_id: int
    type_index: int
    diff: bytes


@dataclass
class EntityFilePayload:
    version: int
    header_value: int
    types: list[EntityFileType]
    records: list[EntityFileRecord]


@dataclass(frozen=True)
class EntitySpawnResult:
    level_name: str
    entity_type: str
    template_id: int
    new_id: int
    output_path: str
    old_record_count: int
    new_record_count: int
    old_package_size: int
    new_package_size: int
    patch_counts: dict[str, int]


@dataclass(frozen=True)
class RuntimeEntitySpawnResult:
    entity_type: str
    entity_id: int
    address: int
    position: tuple[float, float, float]
    before_count: int
    after_count: int
    listed: bool
    template_level: str = ""
    template_id: int = 0


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

    def read_u32(self, address: int) -> int:
        return struct.unpack("<I", self.read(address, 4))[0]

    def read_u8(self, address: int) -> int:
        return self.read(address, 1)[0]

    def read_f32(self, address: int) -> float:
        return struct.unpack("<f", self.read(address, 4))[0]

    def write_u64(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))

    def write_u32(self, address: int, value: int) -> None:
        self.write(address, struct.pack("<I", value & 0xFFFFFFFF))

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

    def alloc(self, size: int, protection: int = PAGE_EXECUTE_READWRITE) -> int:
        size = align_up(size, 0x1000)
        address = kernel32.VirtualAllocEx(
            self.handle,
            None,
            size,
            MEM_COMMIT | MEM_RESERVE,
            protection,
        )
        if not address:
            raise win_error("无法分配远程内存")
        return int(address)

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

    def execute(self, address: int, parameter: int = 0, timeout_ms: int = 5000) -> int:
        thread_id = DWORD()
        thread = kernel32.CreateRemoteThread(
            self.handle,
            None,
            0,
            ctypes.c_void_p(address),
            ctypes.c_void_p(parameter),
            0,
            ctypes.byref(thread_id),
        )
        if not thread:
            raise win_error(f"无法启动远程线程 0x{address:X}")
        try:
            wait = kernel32.WaitForSingleObject(thread, timeout_ms)
            if wait == WAIT_TIMEOUT:
                raise TrainerError("远程代码执行超时")
            if wait != WAIT_OBJECT_0:
                raise win_error("等待远程线程失败")
            exit_code = DWORD()
            check_bool(kernel32.GetExitCodeThread(thread, ctypes.byref(exit_code)), "读取远程线程结果失败")
            return int(exit_code.value)
        finally:
            kernel32.CloseHandle(thread)

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


def repo_root_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read_le_u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_le_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_le_u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def parse_entities_payload(data: bytes) -> EntityFilePayload:
    if data[:4] != ENTITY_FILE_MAGIC:
        raise TrainerError("entities payload 不是 enty 格式")

    cursor = 4
    version = read_le_u16(data, cursor)
    cursor += 2
    header_value = read_le_u64(data, cursor)
    cursor += 8
    type_count = read_le_u64(data, cursor)
    cursor += 8

    types: list[EntityFileType] = []
    for _index in range(type_count):
        name_len = read_le_u64(data, cursor)
        cursor += 8
        name = data[cursor : cursor + name_len].decode("ascii", errors="replace")
        cursor += name_len
        aux = read_le_u64(data, cursor)
        cursor += 8
        types.append(EntityFileType(name=name, aux=aux))

    record_count = read_le_u32(data, cursor)
    cursor += 4
    records: list[EntityFileRecord] = []
    for _index in range(record_count):
        entity_id = read_le_u32(data, cursor)
        cursor += 4
        type_index = read_le_u16(data, cursor)
        cursor += 2
        diff_size = read_le_u32(data, cursor)
        cursor += 4
        diff = data[cursor : cursor + diff_size]
        cursor += diff_size
        records.append(EntityFileRecord(entity_id=entity_id, type_index=type_index, diff=diff))

    if cursor != len(data):
        raise TrainerError("entities payload 结尾存在未解析数据")
    return EntityFilePayload(
        version=version,
        header_value=header_value,
        types=types,
        records=records,
    )


def build_entities_payload(payload: EntityFilePayload) -> bytes:
    out = bytearray()
    out += ENTITY_FILE_MAGIC
    out += struct.pack("<H", payload.version)
    out += struct.pack("<Q", payload.header_value)
    out += struct.pack("<Q", len(payload.types))
    for item in payload.types:
        name = item.name.encode("ascii", errors="replace")
        out += struct.pack("<Q", len(name))
        out += name
        out += struct.pack("<Q", item.aux)

    out += struct.pack("<I", len(payload.records))
    for record in payload.records:
        out += struct.pack("<IHI", record.entity_id, record.type_index, len(record.diff))
        out += record.diff
    return bytes(out)


def entity_file_type_name(payload: EntityFilePayload, record: EntityFileRecord) -> str:
    if record.type_index >= len(payload.types):
        return ""
    return payload.types[record.type_index].name


def entity_type_package_counts(package_data: bytes) -> dict[str, int]:
    return {
        item.name: item.record_count
        for item in entity_type_package_summaries(package_data)
    }


def entity_type_package_summaries(package_data: bytes) -> list[PackageEntityTypeSummary]:
    _toc_offset, entries = parse_package(package_data)
    counts: dict[str, int] = {}
    levels_by_type: dict[str, set[str]] = {}
    for entry in entries:
        if not entry.name.startswith("data-common/") or not entry.name.endswith(".entities"):
            continue
        level_name = entry.name[len("data-common/") : -len(".entities")]
        try:
            payload = parse_entities_payload(package_data[entry.offset : entry.offset + entry.size])
        except TrainerError:
            continue
        for record in payload.records:
            name = entity_file_type_name(payload, record)
            if name:
                counts[name] = counts.get(name, 0) + 1
                levels_by_type.setdefault(name, set()).add(level_name)
    return [
        PackageEntityTypeSummary(
            name=name,
            record_count=count,
            level_count=len(levels_by_type.get(name, set())),
        )
        for name, count in sorted(counts.items(), key=lambda item: item[0].lower())
    ]


def entity_spawn_templates(
    package_data: bytes,
    wanted_type: str,
) -> list[SpawnEntityTemplate]:
    wanted = wanted_type.lower()
    _toc_offset, entries = parse_package(package_data)
    templates: list[SpawnEntityTemplate] = []
    for entry in entries:
        if not entry.name.startswith("data-common/") or not entry.name.endswith(".entities"):
            continue
        try:
            payload = parse_entities_payload(package_data[entry.offset : entry.offset + entry.size])
        except TrainerError:
            continue
        level_name = entry.name[len("data-common/") : -len(".entities")]
        for record in payload.records:
            if record.type_index >= len(payload.types):
                continue
            entity_type = payload.types[record.type_index]
            if entity_type.name.lower() != wanted:
                continue
            templates.append(
                SpawnEntityTemplate(
                    level_name=level_name,
                    entity_type=entity_type.name,
                    entity_id=record.entity_id,
                    header_value=payload.header_value,
                    type_aux=entity_type.aux,
                    diff=record.diff,
                )
            )
    return templates


def choose_spawn_entity_id(payload: EntityFilePayload) -> int:
    used = {record.entity_id for record in payload.records}
    candidate = max(used, default=0) + 1
    while candidate in used:
        candidate += 1
    if candidate > 0xFFFFFFFF:
        raise TrainerError("没有可用的 u32 实体 ID")
    return candidate


def encode_spawn_float(value: float) -> bytes:
    return b"\x00\x00\x00\x00" + struct.pack("<f", value)


def patch_spawn_float_field(diff: bytearray, field_id: int, value: float) -> int:
    encoded = encode_spawn_float(value)
    patches = 0
    if field_id == 0:
        if len(diff) >= 10 and read_le_u16(diff, 0) == 0:
            diff[2:10] = encoded
            patches += 1

    token = b"\xFD" + struct.pack("<H", field_id)
    start = 0
    while True:
        index = diff.find(token, start)
        if index < 0:
            return patches
        value_offset = index + len(token)
        if value_offset + 8 <= len(diff):
            diff[value_offset : value_offset + 8] = encoded
            patches += 1
        start = index + 1


def patch_spawn_coordinates(
    diff: bytes,
    values: tuple[float, float, float],
) -> tuple[bytes, dict[str, int]]:
    x, y, z = values
    patched = bytearray(diff)
    counts = {
        "base_x": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["base_x"], x),
        "out_x": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["out_x"], x),
        "base_y": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["base_y"], y),
        "out_y": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["out_y"], y),
        "base_z": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["base_z"], z),
        "out_z": patch_spawn_float_field(patched, SPAWN_COORD_FIELD_IDS["out_z"], z),
    }
    return bytes(patched), counts


def read_spawn_float_field(diff: bytes, field_id: int) -> float | None:
    if field_id == 0:
        if len(diff) >= 10 and read_le_u16(diff, 0) == 0:
            return struct.unpack("<f", diff[6:10])[0]

    token = b"\xFD" + struct.pack("<H", field_id)
    index = diff.find(token)
    if index < 0:
        return None
    value_offset = index + len(token)
    if value_offset + 8 > len(diff):
        return None
    return struct.unpack("<f", diff[value_offset + 4 : value_offset + 8])[0]


def read_spawn_string_field(diff: bytes, field_id: int) -> str:
    token = b"\xFD" + struct.pack("<H", field_id)
    if field_id == 0:
        index = 0
        value_offset = 2
    else:
        index = diff.find(token)
        if index < 0:
            return ""
        value_offset = index + len(token)
    if value_offset + 16 > len(diff):
        return ""
    old_size = read_le_u64(diff, value_offset)
    new_size_offset = value_offset + 8 + old_size
    if new_size_offset + 8 > len(diff):
        return ""
    new_size = read_le_u64(diff, new_size_offset)
    text_offset = new_size_offset + 8
    if text_offset + new_size > len(diff) or new_size > 512:
        return ""
    return diff[text_offset : text_offset + new_size].decode("ascii", errors="replace")


def spawn_template_position_text(template: SpawnEntityTemplate) -> str:
    values = [
        read_spawn_float_field(template.diff, SPAWN_COORD_FIELD_IDS[axis])
        for axis in ("base_x", "base_y", "base_z")
    ]
    if any(value is None for value in values):
        return ""
    return ", ".join(f"{value:.1f}" for value in values if value is not None)


def spawn_template_direction_text(template: SpawnEntityTemplate) -> str:
    theta = read_spawn_float_field(template.diff, 0x000E)
    if theta is None:
        theta = read_spawn_float_field(template.diff, 0x000D)
    return "" if theta is None else f"{theta:.0f} deg"


def spawn_template_appearance_text(template: SpawnEntityTemplate) -> str:
    mesh = read_spawn_string_field(template.diff, 0x001F)
    if len(mesh) > 36:
        mesh = mesh[:33] + "..."
    return mesh


def parse_package(data: bytes) -> tuple[int, list[PackageEntry]]:
    if data[:4] != PACKAGE_MAGIC:
        raise TrainerError("levels.package 不是 simp 格式")
    toc_offset = data.rfind(PACKAGE_TOC_MAGIC)
    if toc_offset < 0:
        raise TrainerError("levels.package 未找到 toc!")

    count = read_le_u64(data, toc_offset + 8)
    cursor = toc_offset + 0x40
    entries: list[PackageEntry] = []
    for _index in range(count):
        name_len = read_le_u32(data, cursor)
        cursor += 4
        name = data[cursor : cursor + name_len].decode("ascii", errors="replace")
        cursor += name_len
        if cursor >= len(data) or data[cursor] != 0:
            raise TrainerError(f"package TOC 条目 {name!r} 未正确结尾")
        cursor += 1
        size = read_le_u64(data, cursor)
        cursor += 8
        offset = read_le_u64(data, cursor)
        cursor += 8
        entries.append(PackageEntry(name=name, offset=offset, size=size))
    return toc_offset, entries


def rebuild_package(data: bytes, replacements: dict[str, bytes]) -> bytes:
    toc_offset, entries = parse_package(data)
    first_payload_offset = min(entry.offset for entry in entries)
    out = bytearray(data[:first_payload_offset])
    new_entries: list[PackageEntry] = []

    for entry in entries:
        payload = replacements.get(entry.name)
        if payload is None:
            payload = data[entry.offset : entry.offset + entry.size]
        new_entries.append(PackageEntry(name=entry.name, offset=len(out), size=len(payload)))
        out += payload

    toc_header = bytearray(data[toc_offset : toc_offset + 0x40])
    struct.pack_into("<Q", toc_header, 8, len(new_entries))
    out += toc_header
    for entry in new_entries:
        name = entry.name.encode("ascii", errors="replace")
        out += struct.pack("<I", len(name))
        out += name
        out += b"\x00"
        out += struct.pack("<QQ", entry.size, entry.offset)
    return bytes(out)


def sanitize_filename_part(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return cleaned.strip("._") or "item"


def normalize_degrees(value: float) -> float:
    return ((value + 180.0) % 360.0) - 180.0


def angle_distance_degrees(a: float, b: float) -> float:
    return abs(normalize_degrees(a - b))


def cardinal_direction_from_degrees(value: float) -> tuple[float, float]:
    angle = normalize_degrees(value)
    candidates = (
        (0.0, (1.0, 0.0)),
        (90.0, (0.0, 1.0)),
        (180.0, (-1.0, 0.0)),
        (-90.0, (0.0, -1.0)),
    )
    return min(candidates, key=lambda item: angle_distance_degrees(angle, item[0]))[1]


def parse_level_set_file(path: str, known_levels: set[str]) -> list[str]:
    levels: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.split("#", 1)[0].strip()
            if not line or line.startswith("[") or line.startswith("*"):
                continue
            name = line.split()[0]
            if name in known_levels:
                levels.append(name)
    return levels


def builtin_level_lookup() -> dict[str, list[tuple[str, int]]]:
    lookup: dict[str, list[tuple[str, int]]] = {
        name: [] for _level_set, levels in BUILTIN_LEVEL_SETS for name in levels
    }
    for name in BUILTIN_EXTRA_LEVEL_NAMES:
        lookup.setdefault(name, [])
    for level_set, levels in BUILTIN_LEVEL_SETS:
        for index, level in enumerate(levels):
            lookup.setdefault(level, []).append((level_set, index))
    return lookup


def build_level_lookup(root_dir: str | None = None) -> dict[str, list[tuple[str, int]]]:
    lookup = builtin_level_lookup()
    root = root_dir or repo_root_dir()
    level_index_path = os.path.join(root, "analysis_out", "level_index.csv")
    level_set_dir = os.path.join(
        root,
        "analysis_out",
        "extracted_levels",
        "data",
        "level_sets",
    )
    if not os.path.exists(level_index_path) or not os.path.isdir(level_set_dir):
        return lookup

    known_levels: set[str] = set()
    with open(level_index_path, "r", encoding="utf-8", errors="replace") as fh:
        next(fh, None)
        for line in fh:
            line = line.strip()
            if not line:
                continue
            level = line.split(",", 1)[0].strip()
            if level:
                known_levels.add(level)

    for level in known_levels:
        lookup.setdefault(level, [])
    for filename in sorted(os.listdir(level_set_dir)):
        if not filename.endswith(".level_set"):
            continue
        path = os.path.join(level_set_dir, filename)
        level_set = os.path.splitext(filename)[0]
        for index, level in enumerate(parse_level_set_file(path, known_levels)):
            route = (level_set, index)
            routes = lookup.setdefault(level, [])
            if route not in routes:
                routes.append(route)
    return lookup


def ordered_level_names(level_routes: dict[str, list[tuple[str, int]]]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for _level_set, levels in BUILTIN_LEVEL_SETS:
        for level in levels:
            if level in level_routes and level not in seen:
                names.append(level)
                seen.add(level)
    for level in sorted(level_routes):
        if level not in seen:
            names.append(level)
            seen.add(level)
    return names


def level_completion_text(completion: LevelCompletion | None) -> str:
    if completion is None:
        return "未记录"
    return "已完成" if completion.solved else "未完成"


class LightTrainerBackend:
    def __init__(self) -> None:
        self.pid: int | None = None
        self.mem: ProcessMemory | None = None
        self.module: ModuleInfo | None = None
        self.hook: HookInfo | None = None
        self.type_cache: dict[int, EntityTypeInfo] = {}
        self.spawnable_type_cache: list[SpawnableEntityType] = []
        self.spawnable_type_cache_key: tuple[int, int] | None = None
        self.spawn_template_cache: dict[str, list[SpawnEntityTemplate]] = {}
        self.object_appearance_allocations: dict[int, int] = {}
        self.last_error = ""
        self.last_attach_attempt = 0.0

    @property
    def attached(self) -> bool:
        return self.mem is not None and self.hook is not None and self.mem.is_alive()

    def _build_remote_hook(
        self,
        remote_base: int,
        module_base: int,
        pick_addr: int,
        gate_addr: int,
        post_update_addr: int,
    ) -> tuple[bytes, dict[str, int]]:
        return build_remote_code(
            remote_base,
            pick_return=pick_addr + PICK_RETURN_DELTA,
            gate_skip=gate_addr + GATE_SKIP_DELTA,
            gate_through=gate_addr + GATE_THROUGH_DELTA,
            gate_r14_continue=gate_addr + GATE_R14_CONTINUE_DELTA,
            post_update_return=post_update_addr + MAIN_LOOP_RELOAD_RETURN_DELTA,
            campaign_load=module_base + CAMPAIGN_LOAD_RVA,
            campaign_save_current=module_base + CAMPAIGN_SAVE_CURRENT_RVA,
            entity_manager_save=module_base + ENTITY_MANAGER_SAVE_RVA,
            runtime_context=module_base + RUNTIME_CONTEXT_RVA,
            current_entity_manager=module_base + CURRENT_ENTITY_MANAGER_RVA,
            pending_level_set=module_base + PENDING_LEVEL_SET_RVA,
            transition_phase=module_base + TRANSITION_PHASE_RVA,
            save_queue_count=module_base + SAVE_QUEUE_COUNT_RVA,
            post_update_state=module_base + POST_UPDATE_STATE_RVA,
        )

    def _adopt_existing_hook(
        self,
        mem: ProcessMemory,
        module_base: int,
        pick_addr: int,
        gate_addr: int,
        post_update_addr: int,
        pick_live: bytes,
        gate_live: bytes,
        post_update_live: bytes,
    ) -> HookInfo | None:
        pick_dst = decode_rel32_jmp(pick_addr, pick_live)
        gate_dst = decode_rel32_jmp(gate_addr, gate_live)
        post_update_dst = decode_rel32_jmp(post_update_addr, post_update_live)
        if pick_dst is None or gate_dst is None or post_update_dst is None:
            return None
        if pick_live[5:] != (b"\x90" * (PICK_PATCH_LEN - 5)):
            return None
        if gate_live[5:] != (b"\x90" * (GATE_PATCH_LEN - 5)):
            return None
        if post_update_live[5:] != (b"\x90" * (MAIN_LOOP_RELOAD_HOOK_LEN - 5)):
            return None

        remote_base = pick_dst
        code, labels = self._build_remote_hook(
            remote_base,
            module_base,
            pick_addr,
            gate_addr,
            post_update_addr,
        )
        if gate_dst != labels["gate_hook"]:
            return None
        if post_update_dst != labels["post_update_hook"]:
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
            post_update_addr=post_update_addr,
            remote_base=remote_base,
            remote_size=0x4000,
            labels=labels,
            original_pick=PICK_SIGNATURE,
            original_gate=GATE_SIGNATURE,
            original_post_update=MAIN_LOOP_RELOAD_HOOK_SIGNATURE,
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
        post_update_addr = 0
        original_pick = b""
        original_gate = b""
        original_post_update = b""
        patched_pick = False
        patched_gate = False
        patched_post_update = False
        try:
            mem = ProcessMemory(pid)
            module = get_module_info(pid, PROCESS_NAME)
            pick_addr = mem.scan(module.base, module.size, PICK_SIGNATURE)
            gate_addr = mem.scan(module.base, module.size, GATE_SIGNATURE)
            post_update_addr = mem.scan(module.base, module.size, MAIN_LOOP_RELOAD_HOOK_SIGNATURE)
            if pick_addr is None:
                pick_addr = module.base + PICK_RVA
            if gate_addr is None:
                gate_addr = module.base + GATE_RVA
            if post_update_addr is None:
                post_update_addr = module.base + MAIN_LOOP_RELOAD_HOOK_RVA

            original_pick = mem.read(pick_addr, PICK_PATCH_LEN)
            original_gate = mem.read(gate_addr, GATE_PATCH_LEN)
            original_post_update = mem.read(post_update_addr, MAIN_LOOP_RELOAD_HOOK_LEN)

            adopted = self._adopt_existing_hook(
                mem,
                module.base,
                pick_addr,
                gate_addr,
                post_update_addr,
                original_pick,
                original_gate,
                original_post_update,
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
            if original_post_update != MAIN_LOOP_RELOAD_HOOK_SIGNATURE:
                raise TrainerError("主循环读档挂点已被其他补丁占用，重启游戏后再试")

            remote_size = 0x5000
            remote_base = mem.alloc_near(pick_addr, remote_size)
            code, labels = self._build_remote_hook(
                remote_base,
                module.base,
                pick_addr,
                gate_addr,
                post_update_addr,
            )

            if not is_rel32(pick_addr, labels["pick_hook"]):
                raise TrainerError("pick hook 距离超过 rel32 范围")
            if not is_rel32(gate_addr, labels["gate_hook"]):
                raise TrainerError("gate hook 距离超过 rel32 范围")
            if not is_rel32(post_update_addr, labels["post_update_hook"]):
                raise TrainerError("reload hook 距离超过 rel32 范围")

            mem.write(remote_base, code)
            mem.write_code(pick_addr, make_jmp_patch(pick_addr, labels["pick_hook"], PICK_PATCH_LEN))
            patched_pick = True
            mem.write_code(gate_addr, make_jmp_patch(gate_addr, labels["gate_hook"], GATE_PATCH_LEN))
            patched_gate = True
            mem.write_code(
                post_update_addr,
                make_jmp_patch(post_update_addr, labels["post_update_hook"], MAIN_LOOP_RELOAD_HOOK_LEN),
            )
            patched_post_update = True

            self.pid = pid
            self.mem = mem
            self.module = module
            self.hook = HookInfo(
                pick_addr=pick_addr,
                gate_addr=gate_addr,
                post_update_addr=post_update_addr,
                remote_base=remote_base,
                remote_size=remote_size,
                labels=labels,
                original_pick=original_pick,
                original_gate=original_gate,
                original_post_update=original_post_update,
                owns_hook=True,
            )
            self.last_error = ""
            return True
        except Exception as exc:
            if mem is not None:
                try:
                    if mem.is_alive():
                        if patched_post_update and post_update_addr and original_post_update:
                            mem.write_code(post_update_addr, original_post_update)
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
                        if mem.read(hook.post_update_addr, 1) == b"\xE9":
                            mem.write_code(hook.post_update_addr, hook.original_post_update)
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
        self.type_cache.clear()
        self.spawnable_type_cache = []
        self.spawnable_type_cache_key = None
        self.spawn_template_cache = {}
        self.object_appearance_allocations = {}

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

    def read_c_string(self, address: int, max_len: int = 96) -> str:
        if not self.mem or not address:
            return ""
        data = bytearray()
        for offset in range(max_len):
            try:
                value = self.mem.read_u8(address + offset)
            except TrainerError:
                break
            if value == 0:
                break
            data.append(value)
        return data.decode("ascii", errors="replace")

    def read_len_string(self, address: int, length: int, max_len: int = 256) -> str:
        if not self.mem or not address or length <= 0:
            return ""
        data = self.mem.read(address, min(int(length), max_len))
        return data.split(b"\0", 1)[0].decode("ascii", errors="replace")

    def object_type_info(self, address: int) -> EntityTypeInfo:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        type_info = self.entity_type_info(self.mem.read_u64(address + ENTITY_TYPE))
        if not type_info.name:
            raise TrainerError(f"目标不是可识别实体 0x{address:X}")
        return type_info

    def object_direction(self, address: int) -> float | None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        self.object_type_info(address)
        return self.read_object_direction(address)

    def read_object_direction(self, address: int) -> float | None:
        if not self.mem:
            return None
        for offset in (ENTITY_THETA_TARGET, ENTITY_THETA_CURRENT):
            try:
                value = self.mem.read_f32(address + offset)
            except TrainerError:
                continue
            if math.isfinite(value):
                return normalize_degrees(value)
        return None

    def write_object_direction(self, address: int, value: float) -> None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        self.object_type_info(address)
        if not math.isfinite(value):
            raise TrainerError("朝向不是有效数字")
        theta = normalize_degrees(value)
        self.mem.write_f32(address + ENTITY_THETA_CURRENT, theta)
        self.mem.write_f32(address + ENTITY_THETA_TARGET, theta)

    def object_appearance(self, address: int) -> str:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        self.object_type_info(address)
        return self.read_object_appearance(address)

    def read_object_appearance(self, address: int) -> str:
        if not self.mem:
            return ""
        try:
            mesh_ptr = self.mem.read_u64(address + ENTITY_MESH)
        except TrainerError:
            return ""
        return self.read_c_string(mesh_ptr, OBJECT_APPEARANCE_MAX_LEN)

    def write_object_appearance(self, address: int, value: str) -> None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        self.object_type_info(address)
        try:
            data = value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise TrainerError("外观只支持 ASCII 资源名") from exc
        if len(data) > OBJECT_APPEARANCE_MAX_LEN:
            raise TrainerError(f"外观资源名不能超过 {OBJECT_APPEARANCE_MAX_LEN} 字节")

        new_ptr = self.mem.alloc(len(data) + 1)
        old_alloc = self.object_appearance_allocations.get(address, 0)
        try:
            self.mem.write(new_ptr, data + b"\0")
            self.mem.write_u64(address + ENTITY_MESH, new_ptr)
            self.object_appearance_allocations[address] = new_ptr
            if old_alloc and old_alloc != new_ptr:
                try:
                    self.mem.free(old_alloc)
                except Exception:
                    pass
        except Exception:
            try:
                self.mem.free(new_ptr)
            except Exception:
                pass
            raise

    def read_level_set(self, level_set_ptr: int, level_index: int) -> tuple[str, str, int]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        if not level_set_ptr:
            return ("", "", 0)

        name_len = self.mem.read_u64(level_set_ptr + LEVEL_SET_NAME_LEN)
        name_ptr = self.mem.read_u64(level_set_ptr + LEVEL_SET_NAME_PTR)
        level_set_name = self.read_len_string(name_ptr, name_len)

        level_count = self.mem.read_u64(level_set_ptr + LEVEL_SET_COUNT)
        table_ptr = self.mem.read_u64(level_set_ptr + LEVEL_SET_TABLE)
        if level_index < 0 or level_index >= level_count or not table_ptr:
            return (level_set_name, "", int(level_count))

        entry = table_ptr + level_index * LEVEL_SET_ENTRY_SIZE
        level_len = self.mem.read_u64(entry)
        level_ptr = self.mem.read_u64(entry + 8)
        level_name = self.read_len_string(level_ptr, level_len)
        return (level_set_name, level_name, int(level_count))

    def runtime_level_set_catalog(self) -> dict[str, int]:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        capacity = self.mem.read_u64(base + LEVEL_SET_CATALOG_CAPACITY_RVA)
        table_ptr = self.mem.read_u64(base + LEVEL_SET_CATALOG_TABLE_RVA)
        if capacity <= 0 or capacity > MAX_LEVEL_SET_CATALOG_ENTRIES or not table_ptr:
            raise TrainerError("运行时关卡集 catalog 尚不可用")

        catalog: dict[str, int] = {}
        for index in range(int(capacity)):
            entry = table_ptr + index * LEVEL_SET_CATALOG_ENTRY_SIZE
            try:
                entry_hash = self.mem.read_u32(entry)
                if entry_hash == 0:
                    continue
                key_len = self.mem.read_u64(entry + 8)
                key_ptr = self.mem.read_u64(entry + 16)
                level_set_ptr = self.mem.read_u64(entry + 24)
            except TrainerError:
                continue
            if not level_set_ptr:
                continue

            name = self.read_len_string(key_ptr, key_len, 128)
            if not name:
                try:
                    name, _level_name, _count = self.read_level_set(level_set_ptr, -1)
                except TrainerError:
                    name = ""
            if name:
                catalog[name] = level_set_ptr

        if not catalog:
            raise TrainerError("运行时关卡集 catalog 为空")
        return catalog

    def runtime_level_routes(self) -> dict[str, list[RuntimeLevelRoute]]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")

        routes: dict[str, list[RuntimeLevelRoute]] = {}
        for catalog_name, level_set_ptr in self.runtime_level_set_catalog().items():
            try:
                level_set_name, _level_name, level_count = self.read_level_set(level_set_ptr, -1)
                table_ptr = self.mem.read_u64(level_set_ptr + LEVEL_SET_TABLE)
            except TrainerError:
                continue
            if level_count <= 0 or level_count > MAX_LEVELS_PER_SET or not table_ptr:
                continue

            level_set_name = level_set_name or catalog_name
            for index in range(level_count):
                try:
                    entry = table_ptr + index * LEVEL_SET_ENTRY_SIZE
                    level_len = self.mem.read_u64(entry)
                    level_ptr = self.mem.read_u64(entry + 8)
                    level_name = self.read_len_string(level_ptr, level_len)
                except TrainerError:
                    continue
                if not level_name:
                    continue
                routes.setdefault(level_name, []).append(
                    RuntimeLevelRoute(
                        level_set=level_set_name,
                        level_index=index,
                        level_name=level_name,
                        level_set_ptr=level_set_ptr,
                    )
                )
        return routes

    def level_completion_states(self) -> dict[str, LevelCompletion]:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        status_ptr = self.mem.read_u64(base + LEVEL_STATUS_MAP_PTR_RVA)
        if not status_ptr:
            return {}

        capacity = self.mem.read_u64(status_ptr + LEVEL_STATUS_MAP_CAPACITY)
        table_ptr = self.mem.read_u64(status_ptr + LEVEL_STATUS_MAP_TABLE)
        if capacity <= 0 or not table_ptr:
            return {}
        if capacity > MAX_LEVEL_STATUS_ENTRIES:
            raise TrainerError(f"关卡完成状态表过大：capacity={capacity}")

        states: dict[str, LevelCompletion] = {}
        for index in range(int(capacity)):
            entry = table_ptr + index * LEVEL_STATUS_MAP_ENTRY_SIZE
            try:
                entry_hash = self.mem.read_u32(entry + LEVEL_STATUS_MAP_ENTRY_HASH)
                if entry_hash < LEVEL_STATUS_HASH_MIN_USED:
                    continue
                key_len = self.mem.read_u64(entry + LEVEL_STATUS_MAP_ENTRY_KEY_LEN)
                key_ptr = self.mem.read_u64(entry + LEVEL_STATUS_MAP_ENTRY_KEY_PTR)
                flags = self.mem.read_u8(entry + LEVEL_STATUS_MAP_ENTRY_FLAGS)
            except TrainerError:
                continue
            if key_len <= 0 or key_len > 256 or not key_ptr:
                continue

            level_name = self.read_len_string(key_ptr, key_len, 256)
            if level_name:
                states[level_name] = LevelCompletion(level_name=level_name, flags=flags)
        return states

    def resolve_runtime_level_route(self, target: str) -> RuntimeLevelRoute:
        target = target.strip()
        if not target:
            raise TrainerError("请输入或选择目标关卡名")
        if any(ch.isspace() for ch in target):
            raise TrainerError("目标关卡名不能包含空白字符")

        routes = self.runtime_level_routes().get(target, [])
        if not routes:
            raise TrainerError(f"运行时 catalog 中未找到关卡 {target}")

        try:
            current = self.current_level_state()
        except TrainerError:
            current = None
        routes = sorted(
            routes,
            key=lambda route: (
                0 if current and route.level_set == current.level_set else 1,
                route.level_set,
                route.level_index,
            ),
        )
        return routes[0]

    def request_level_route_switch(self, route: RuntimeLevelRoute) -> LevelSwitchResult:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        phase = self.mem.read_u64(base + TRANSITION_PHASE_RVA)
        if phase >= 2:
            raise TrainerError(f"游戏正在过渡中（phase={phase}），稍后再试")

        self.mem.write_u64(base + PENDING_LEVEL_SET_RVA, route.level_set_ptr)
        self.mem.write_u64(base + PENDING_LEVEL_INDEX_RVA, route.level_index)
        self.mem.write_u64(base + TRANSITION_STATE_RVA, TRANSITION_STATE_SWITCH_LEVEL)
        self.mem.write_f32(base + TRANSITION_DELAY_RVA, 0.0)
        self.mem.write_f32(base + TRANSITION_PROGRESS_RVA, 0.0)
        self.mem.write_u64(base + TRANSITION_PHASE_RVA, TRANSITION_PHASE_REQUESTED)

        return LevelSwitchResult(
            level_set=route.level_set,
            level_index=route.level_index,
            level_name=route.level_name,
            level_set_ptr=route.level_set_ptr,
            transition_state=TRANSITION_STATE_SWITCH_LEVEL,
            transition_phase=TRANSITION_PHASE_REQUESTED,
        )

    def request_level_switch(self, target: str) -> LevelSwitchResult:
        return self.request_level_route_switch(self.resolve_runtime_level_route(target))

    def current_runtime_level_route(self) -> RuntimeLevelRoute:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        level_set_ptr = self.mem.read_u64(base + CURRENT_LEVEL_SET_RVA)
        level_index = self.mem.read_u64(base + CURRENT_LEVEL_INDEX_RVA)
        level_set, level_name, _level_count = self.read_level_set(level_set_ptr, level_index)
        if not level_set_ptr or not level_name:
            raise TrainerError("当前关卡未知")

        return RuntimeLevelRoute(
            level_set=level_set,
            level_index=int(level_index),
            level_name=level_name,
            level_set_ptr=level_set_ptr,
        )

    def current_campaign_name(self) -> str:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        name_len = self.mem.read_u64(self.module.base + CURRENT_CAMPAIGN_NAME_RVA)
        name_ptr = self.mem.read_u64(self.module.base + CURRENT_CAMPAIGN_NAME_RVA + 8)
        name = self.read_len_string(name_ptr, name_len, 256)
        if not name:
            raise TrainerError("当前存档名未知，不能重载")
        return name

    def reload_current_save_status(self) -> int:
        if not self.attached or not self.mem:
            return RELOAD_STATUS_IDLE
        return self.mem.read_u32(self.label("reload_status"))

    def reload_current_save_status_text(self) -> str:
        status = self.reload_current_save_status()
        return RELOAD_STATUS_MESSAGES.get(status, f"状态 {status}")

    def queue_current_save_reload(self) -> str:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        campaign_name = self.current_campaign_name()
        try:
            name_data = campaign_name.encode("ascii")
        except UnicodeEncodeError as exc:
            raise TrainerError("当前存档名包含非 ASCII 字符，不能安全重载") from exc
        if len(name_data) >= 256:
            raise TrainerError("当前存档名过长，不能安全重载")

        phase = self.mem.read_u64(self.module.base + TRANSITION_PHASE_RVA)
        if phase >= 2:
            raise TrainerError(f"游戏正在过渡中（phase={phase}），稍后再试")

        buffer_addr = self.label("campaign_name_buffer")
        self.mem.write(buffer_addr, name_data + b"\0" + (b"\0" * (255 - len(name_data))))
        self.mem.write_u64(self.label("campaign_name_len"), len(name_data))
        self.mem.write_u64(self.label("campaign_name_ptr"), buffer_addr)
        self.mem.write_u32(self.label("reload_status"), RELOAD_STATUS_QUEUED)
        self.mem.write_u8(self.label("reload_requested"), 1)
        current_count = self.mem.read_counter(self.label("reload_request_count"))
        self.mem.write_u64(self.label("reload_request_count"), current_count + 1)
        return campaign_name

    def current_level_state(self) -> LevelState:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        level_set_ptr = self.mem.read_u64(base + CURRENT_LEVEL_SET_RVA)
        level_index = self.mem.read_u64(base + CURRENT_LEVEL_INDEX_RVA)
        level_set, level_name, _level_count = self.read_level_set(level_set_ptr, level_index)

        pending_set_ptr = self.mem.read_u64(base + PENDING_LEVEL_SET_RVA)
        pending_index = self.mem.read_u64(base + PENDING_LEVEL_INDEX_RVA)
        pending_level_set = ""
        if pending_set_ptr:
            pending_level_set, _pending_level_name, _pending_count = self.read_level_set(
                pending_set_ptr,
                pending_index,
            )
        transition_state = self.mem.read_u64(base + TRANSITION_STATE_RVA)
        transition_phase = self.mem.read_u64(base + TRANSITION_PHASE_RVA)

        return LevelState(
            level_set=level_set,
            level_index=int(level_index),
            level_name=level_name,
            pending_level_set=pending_level_set,
            pending_level_index=int(pending_index),
            transition_state=int(transition_state),
            transition_phase=int(transition_phase),
        )

    def game_root_dir(self) -> str:
        if self.module:
            return os.path.dirname(self.module.path)

        candidates = [
            os.path.dirname(repo_root_dir()),
            os.getcwd(),
            os.path.dirname(os.getcwd()),
            os.path.dirname(os.path.dirname(os.getcwd())),
        ]
        seen: set[str] = set()
        for path in candidates:
            path = os.path.abspath(path)
            if path in seen:
                continue
            seen.add(path)
            if os.path.exists(os.path.join(path, "data", "levels.package")):
                return path
        raise TrainerError("尚未连接游戏，且无法从当前目录推断游戏安装目录")

    def levels_package_path(self) -> str:
        path = os.path.join(self.game_root_dir(), "data", "levels.package")
        if not os.path.exists(path):
            raise TrainerError(f"未找到 levels.package：{path}")
        return path

    def spawn_output_dir(self) -> str:
        game_root = self.game_root_dir()
        candidates = [
            os.path.join(game_root, "sinkinghero", "analysis_out"),
            os.path.join(game_root, "analysis_out"),
            os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)),
        ]
        for path in candidates:
            try:
                os.makedirs(path, exist_ok=True)
                return path
            except OSError:
                continue
        raise TrainerError("无法创建输出目录")

    def create_spawn_package_copy(
        self,
        template_type: str,
        template_id: int,
        values: tuple[float, float, float],
    ) -> EntitySpawnResult:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        if not template_type:
            raise TrainerError("选中对象没有可识别类型")
        if not all(math.isfinite(value) and abs(value) <= COORD_LIMIT for value in values):
            raise TrainerError("目标坐标超出允许范围")

        level = self.current_level_state()
        if not level.level_name:
            raise TrainerError("当前关卡名未知")

        package_path = self.levels_package_path()
        with open(package_path, "rb") as fh:
            package_data = fh.read()

        entry_name = f"data-common/{level.level_name}.entities"
        _toc_offset, entries = parse_package(package_data)
        entry = next((item for item in entries if item.name == entry_name), None)
        if entry is None:
            raise TrainerError(f"levels.package 中没有 {entry_name}")

        entities_data = package_data[entry.offset : entry.offset + entry.size]
        payload = parse_entities_payload(entities_data)
        old_record_count = len(payload.records)
        template = None
        for record in payload.records:
            if record.entity_id != template_id:
                continue
            if entity_file_type_name(payload, record) != template_type:
                continue
            template = record
            break
        if template is None:
            raise TrainerError(
                f"当前关卡资源里找不到 {template_type} 0x{template_id:X}，"
                "可换一个同类型对象做模板"
            )

        new_id = choose_spawn_entity_id(payload)
        diff, patch_counts = patch_spawn_coordinates(template.diff, values)
        payload.records.append(
            EntityFileRecord(
                entity_id=new_id,
                type_index=template.type_index,
                diff=diff,
            )
        )
        patched_entities = build_entities_payload(payload)
        patched_package = rebuild_package(package_data, {entry_name: patched_entities})

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_name = (
            f"levels_{sanitize_filename_part(level.level_name)}_"
            f"{sanitize_filename_part(template_type)}_{new_id:08X}_{timestamp}.package"
        )
        output_path = os.path.join(self.spawn_output_dir(), out_name)
        with open(output_path, "wb") as fh:
            fh.write(patched_package)

        return EntitySpawnResult(
            level_name=level.level_name,
            entity_type=template_type,
            template_id=template_id,
            new_id=new_id,
            output_path=output_path,
            old_record_count=old_record_count,
            new_record_count=len(payload.records),
            old_package_size=len(package_data),
            new_package_size=len(patched_package),
            patch_counts=patch_counts,
        )

    def console_switch_info(self) -> ConsoleSwitchInfo:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        return ConsoleSwitchInfo(
            open_console_string=self.read_c_string(base + OPEN_CONSOLE_STRING_RVA, 64),
            open_console_table_offset=OPEN_CONSOLE_FIELD_OFFSET,
            playtest_enabled=bool(self.mem.read_u8(base + PLAYTEST_FLAG_RVA)),
            running_packaged=bool(self.mem.read_u8(base + RUNNING_PACKAGED_FLAG_RVA)),
        )

    def entity_type_info(self, type_ptr: int) -> EntityTypeInfo:
        if type_ptr in self.type_cache:
            return self.type_cache[type_ptr]
        if not self.attached or not self.mem or not self.module:
            return EntityTypeInfo(type_ptr, 0, 0, "")
        if not (self.module.base <= type_ptr < self.module.base + self.module.size):
            return EntityTypeInfo(type_ptr, 0, 0, "")
        try:
            kind = self.mem.read_u32(type_ptr)
            if kind != ENTITY_KIND_ENTITY:
                return EntityTypeInfo(type_ptr, 0, 0, "")
            type_id = self.mem.read_u32(type_ptr + ENTITY_TYPE_ID)
            type_size = self.mem.read_u32(type_ptr + ENTITY_TYPE_SIZE)
            name_ptr = self.mem.read_u64(type_ptr + ENTITY_TYPE_NAME)
            name = self.read_c_string(name_ptr)
        except TrainerError:
            return EntityTypeInfo(type_ptr, 0, 0, "")
        info = EntityTypeInfo(type_ptr, type_id, type_size, name)
        self.type_cache[type_ptr] = info
        return info

    def package_entity_type_counts(self) -> dict[str, int]:
        package_path = self.levels_package_path()
        with open(package_path, "rb") as fh:
            return entity_type_package_counts(fh.read())

    def package_entity_type_summaries(self) -> list[PackageEntityTypeSummary]:
        package_path = self.levels_package_path()
        with open(package_path, "rb") as fh:
            return entity_type_package_summaries(fh.read())

    def scan_entity_type_table(self) -> list[EntityTypeInfo]:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        base = self.module.base
        module_end = base + self.module.size
        found: dict[int, EntityTypeInfo] = {}
        chunk_size = 0x100000
        tail = b""
        tail_base = base
        for chunk_offset in range(0, self.module.size, chunk_size):
            read_size = min(chunk_size, self.module.size - chunk_offset)
            chunk_base = base + chunk_offset
            try:
                chunk = self.mem.read(chunk_base, read_size)
            except TrainerError:
                tail = b""
                tail_base = chunk_base + read_size
                continue
            data = tail + chunk
            data_base = tail_base if tail else chunk_base
            scan_end = max(0, len(data) - 0x20 + 1)
            for offset in range(0, scan_end, 8):
                if read_le_u32(data, offset) != ENTITY_KIND_ENTITY:
                    continue
                type_id = read_le_u32(data, offset + ENTITY_TYPE_ID)
                type_size = read_le_u32(data, offset + ENTITY_TYPE_SIZE)
                name_len = read_le_u64(data, offset + ENTITY_TYPE_NAME_LEN)
                name_ptr = read_le_u64(data, offset + ENTITY_TYPE_NAME)
                if not (0 < type_id < 0x10000):
                    continue
                if not (0x80 <= type_size <= 0x4000):
                    continue
                if not (0 < name_len <= MAX_ENTITY_TYPE_NAME_LEN):
                    continue
                if not (base <= name_ptr < module_end):
                    continue
                try:
                    name = self.read_len_string(name_ptr, int(name_len), MAX_ENTITY_TYPE_NAME_LEN)
                except TrainerError:
                    continue
                if not name or len(name) != name_len:
                    continue
                if not all(ch.isalnum() or ch in "._-" for ch in name):
                    continue

                address = data_base + offset
                info = EntityTypeInfo(address, type_id, type_size, name)
                cached = found.get(type_id)
                if cached is None or address < cached.address:
                    found[type_id] = info
                    self.type_cache[address] = info

            tail = data[-0x20:]
            tail_base = data_base + len(data) - len(tail)

        return sorted(found.values(), key=lambda item: item.name.lower())

    def current_entity_type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        try:
            objects = self.coordinate_objects()
        except TrainerError:
            return counts
        for record in objects:
            name = record.type_info.name
            if name:
                counts[name] = counts.get(name, 0) + 1
        return counts

    def spawnable_entity_types(self, refresh: bool = False) -> list[SpawnableEntityType]:
        cache_key = (self.pid or 0, self.module.base if self.module else 0)
        if not refresh and self.spawnable_type_cache and self.spawnable_type_cache_key == cache_key:
            return self.spawnable_type_cache

        live_counts = self.current_entity_type_counts() if self.attached else {}
        package_summaries: dict[str, PackageEntityTypeSummary] = {}
        try:
            package_summaries = {
                item.name: item for item in self.package_entity_type_summaries()
            }
        except TrainerError:
            package_summaries = {}

        runtime_types = {}
        if self.attached and self.mem and self.module:
            runtime_types = {
                info.name: info for info in self.scan_entity_type_table() if info.name
            }
        all_names = set(package_summaries) | set(runtime_types) | set(live_counts)
        if not all_names:
            raise TrainerError("尚未连接游戏，且未能读取 levels.package 实体目录")
        types = []
        seen_names: set[str] = set()
        for name in sorted(all_names, key=str.lower):
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            info = runtime_types.get(name)
            package = package_summaries.get(name)
            types.append(
                SpawnableEntityType(
                    name=name,
                    address=info.address if info else 0,
                    type_id=info.type_id if info else 0,
                    type_size=info.type_size if info else 0,
                    live_count=live_counts.get(name, 0),
                    package_count=package.record_count if package else 0,
                    level_count=package.level_count if package else 0,
                    runtime=info is not None,
                )
            )

        types.sort(
            key=lambda item: (
                item.package_count == 0,
                not item.runtime,
                item.name.lower(),
            )
        )
        self.spawnable_type_cache = types
        self.spawnable_type_cache_key = cache_key
        return types

    def spawn_templates_for_type(self, entity_type: str) -> list[SpawnEntityTemplate]:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        if not entity_type:
            return []
        cache_key = entity_type.lower()
        templates = self.spawn_template_cache.get(cache_key)
        if templates is None:
            package_path = self.levels_package_path()
            with open(package_path, "rb") as fh:
                templates = entity_spawn_templates(fh.read(), entity_type)
            self.spawn_template_cache[cache_key] = templates

        current_level = ""
        try:
            current_level = self.current_level_state().level_name
        except TrainerError:
            current_level = ""
        return sorted(
            templates,
            key=lambda item: (
                bool(current_level) and item.level_name != current_level,
                item.level_name.lower(),
                item.entity_id,
                len(item.diff),
            ),
        )

    def current_level_ptr(self) -> int:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        level = 0
        if self.module:
            level = self.mem.read_u64(self.module.base + CURRENT_ENTITY_MANAGER_RVA)
        if not level:
            player = self.player_ptr()
            if player:
                level = self.mem.read_u64(player + PLAYER_LEVEL)
        if not level:
            raise TrainerError("尚未找到当前关卡")
        return level

    def player_entity_ptr(self) -> int:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_ptr()
        if player:
            return player

        level = self.current_level_ptr()
        count = self.mem.read_u64(level + LEVEL_OBJECT_COUNT)
        array = self.mem.read_u64(level + LEVEL_OBJECT_ARRAY)
        if count <= 0 or not array:
            raise TrainerError("当前关卡没有对象列表")
        if count > MAX_LEVEL_OBJECT_COUNT:
            raise TrainerError(f"对象数量异常：{count}")

        for index in range(int(count)):
            try:
                address = self.mem.read_u64(array + index * 8)
                if not address:
                    continue
                type_info = self.entity_type_info(self.mem.read_u64(address + ENTITY_TYPE))
                if type_info.name == "Guy":
                    return address
            except TrainerError:
                continue
        raise TrainerError("尚未捕获玩家实体，且当前对象列表没有 Guy")

    def player_xyz(self) -> tuple[float, float, float]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_entity_ptr()
        return tuple(self.mem.read_f32(player + offset) for offset in PLAYER_COORD_OFFSETS)

    def player_front_xyz(self) -> tuple[float, float, float]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_entity_ptr()
        px, py, pz = (self.mem.read_f32(player + offset) for offset in PLAYER_COORD_OFFSETS)
        theta = self.mem.read_f32(player + PLAYER_THETA_TARGET)
        if not math.isfinite(theta):
            z = self.mem.read_f32(player + ENTITY_ORIENTATION_Z)
            w = self.mem.read_f32(player + ENTITY_ORIENTATION_W)
            if not math.isfinite(z) or not math.isfinite(w) or abs(z) + abs(w) < 1e-6:
                raise TrainerError("无法识别玩家朝向")
            theta = math.degrees(2.0 * math.atan2(z, w))

        dx, dy = cardinal_direction_from_degrees(theta)
        return (
            float(round(px + dx * FRONT_GRID_STEP)),
            float(round(py + dy * FRONT_GRID_STEP)),
            pz,
        )

    def write_player_xyz(self, values: tuple[float, float, float]) -> None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        player = self.player_entity_ptr()
        self.mem.write(player, struct.pack("<fff", *values))

    def coordinate_objects(self) -> list[CoordinateObject]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")

        try:
            player = self.player_entity_ptr()
            px, py, pz = (self.mem.read_f32(player + offset) for offset in PLAYER_COORD_OFFSETS)
        except TrainerError:
            player = 0
            px, py, pz = (0.0, 0.0, 0.0)
        level = self.current_level_ptr()
        count = self.mem.read_u64(level + LEVEL_OBJECT_COUNT)
        array = self.mem.read_u64(level + LEVEL_OBJECT_ARRAY)
        if count <= 0 or not array:
            raise TrainerError("当前关卡没有对象列表")
        if count > MAX_LEVEL_OBJECT_COUNT:
            raise TrainerError(f"对象数量异常：{count}")

        objects: list[CoordinateObject] = []
        seen: set[int] = set()
        for index in range(count):
            try:
                address = self.mem.read_u64(array + index * 8)
                if not address or address in seen:
                    continue
                seen.add(address)
                type_info = self.entity_type_info(self.mem.read_u64(address + ENTITY_TYPE))
                if not type_info.name:
                    continue
                x, y, z = (
                    self.mem.read_f32(address + offset) for offset in PLAYER_COORD_OFFSETS
                )
                if not all(math.isfinite(value) and abs(value) <= COORD_LIMIT for value in (x, y, z)):
                    continue
                try:
                    entity_id = self.mem.read_u32(address + ENTITY_ID)
                except TrainerError:
                    entity_id = 0
                direction = self.read_object_direction(address)
                appearance = self.read_object_appearance(address)
                distance = math.sqrt((x - px) * (x - px) + (y - py) * (y - py) + (z - pz) * (z - pz))
                objects.append(
                    CoordinateObject(
                        address=address,
                        source=f"+0x{LEVEL_OBJECT_COUNT:X}",
                        index=index,
                        entity_id=entity_id,
                        type_info=type_info,
                        position=(x, y, z),
                        direction=direction,
                        appearance=appearance,
                        distance=distance,
                        is_player=address == player,
                    )
                )
            except TrainerError:
                continue

        return sorted(
            objects,
            key=lambda item: (
                not item.is_player,
                item.distance,
                item.type_info.name.lower(),
                item.index,
            ),
        )

    def write_object_xyz(self, address: int, values: tuple[float, float, float]) -> None:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        if not all(math.isfinite(value) and abs(value) <= COORD_LIMIT for value in values):
            raise TrainerError("对象坐标超出允许范围")
        self.object_type_info(address)
        self.mem.write(address, struct.pack("<fff", *values))

    def object_xyz(self, address: int) -> tuple[float, float, float]:
        if not self.attached or not self.mem:
            raise TrainerError("尚未连接游戏")
        self.object_type_info(address)
        return tuple(self.mem.read_f32(address + offset) for offset in PLAYER_COORD_OFFSETS)

    def next_runtime_entity_id(self, manager: int) -> int:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")

        counter_addr = self.module.base + SPAWN_DYNAMIC_ENTITY_ID_RVA
        counter = self.mem.read_u32(counter_addr) & 0x000FFFFF
        count = self.mem.read_u64(manager + LEVEL_OBJECT_COUNT)
        array = self.mem.read_u64(manager + LEVEL_OBJECT_ARRAY)
        if count > MAX_LEVEL_OBJECT_COUNT:
            raise TrainerError(f"对象数量异常：{count}")

        used: set[int] = set()
        if array:
            for index in range(int(count)):
                try:
                    address = self.mem.read_u64(array + index * 8)
                    if address:
                        used.add(self.mem.read_u32(address + ENTITY_ID))
                except TrainerError:
                    continue

        for _attempt in range(0x100000):
            entity_id = SPAWN_DYNAMIC_ENTITY_ID_MASK | counter
            counter = (counter + 1) & 0x000FFFFF
            if entity_id not in used:
                self.mem.write_u32(counter_addr, counter)
                return entity_id
        raise TrainerError("没有可用的动态实体 ID")

    def spawn_runtime_entity(
        self,
        type_info: EntityTypeInfo | SpawnableEntityType,
        values: tuple[float, float, float],
        template: SpawnEntityTemplate,
    ) -> RuntimeEntitySpawnResult:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        if not type_info.name or not type_info.address:
            raise TrainerError("选中对象没有可识别类型")
        if not (self.module.base <= type_info.address < self.module.base + self.module.size):
            raise TrainerError(f"对象类型地址异常 0x{type_info.address:X}")
        if not all(math.isfinite(value) and abs(value) <= COORD_LIMIT for value in values):
            raise TrainerError("目标坐标超出允许范围")

        if template.entity_type.lower() != type_info.name.lower():
            raise TrainerError(
                f"属性模板类型不匹配：{template.entity_type} != {type_info.name}"
            )
        if not template.diff:
            raise TrainerError("属性模板 diff 为空，不能可靠生成")

        diff, _patch_counts = patch_spawn_coordinates(template.diff, values)
        manager = self.current_level_ptr()
        before_live = self.mem.read_u64(manager + LEVEL_OBJECT_COUNT)
        if before_live > MAX_LEVEL_OBJECT_COUNT:
            raise TrainerError(f"对象数量异常：{before_live}")
        entity_id = self.next_runtime_entity_id(manager)

        remote_base = 0
        try:
            remote_size = max(
                SPAWN_REMOTE_BLOCK_SIZE,
                align_up(0x1000 + SPAWN_REQ_SIZE + len(diff) + 0x100, 0x1000),
            )
            remote_base = self.mem.alloc(remote_size)
            code, _labels = build_runtime_spawn_code(remote_base)
            request_addr = remote_base + align_up(len(code), 16)
            diff_addr = request_addr + align_up(SPAWN_REQ_SIZE, 16)
            if diff_addr + len(diff) > remote_base + remote_size:
                raise TrainerError("即时生成远程代码块过小")

            request = bytearray(SPAWN_REQ_SIZE)
            base = self.module.base
            struct.pack_into("<Q", request, SPAWN_REQ_CTX, base + RUNTIME_CONTEXT_RVA)
            struct.pack_into("<Q", request, SPAWN_REQ_MANAGER, manager)
            struct.pack_into("<Q", request, SPAWN_REQ_TYPE, type_info.address)
            struct.pack_into("<I", request, SPAWN_REQ_ENTITY_ID, entity_id)
            struct.pack_into("<fff", request, SPAWN_REQ_X, *values)
            struct.pack_into("<I", request, SPAWN_REQ_STATUS, 0xFFFFFFFF)
            struct.pack_into("<Q", request, SPAWN_REQ_CREATE_FUNC, base + SPAWN_CREATE_ENTITY_RVA)
            struct.pack_into("<Q", request, SPAWN_REQ_INIT_FUNC, base + SPAWN_INIT_ENTITY_RVA)
            struct.pack_into("<Q", request, SPAWN_REQ_REGISTER_FUNC, base + SPAWN_REGISTER_ENTITY_RVA)
            struct.pack_into("<Q", request, SPAWN_REQ_APPLY_DIFF_FUNC, base + SPAWN_APPLY_DIFF_RVA)
            struct.pack_into("<Q", request, SPAWN_REQ_DIFF_SIZE, len(diff))
            struct.pack_into("<Q", request, SPAWN_REQ_DIFF_PTR, diff_addr)
            struct.pack_into("<Q", request, SPAWN_REQ_HEADER_VALUE, template.header_value)
            struct.pack_into("<Q", request, SPAWN_REQ_TYPE_AUX, template.type_aux)

            self.mem.write(remote_base, code)
            self.mem.write(request_addr, bytes(request))
            self.mem.write(diff_addr, diff)
            exit_code = self.mem.execute(
                remote_base,
                request_addr,
                timeout_ms=SPAWN_REMOTE_TIMEOUT_MS,
            )
            response = self.mem.read(request_addr, SPAWN_REQ_SIZE)
        finally:
            if remote_base:
                self.mem.free(remote_base)

        status = struct.unpack_from("<I", response, SPAWN_REQ_STATUS)[0]
        if exit_code != SPAWN_STATUS_OK or status != SPAWN_STATUS_OK:
            status_text = SPAWN_STATUS_MESSAGES.get(status, f"status={status}")
            raise TrainerError(f"即时生成失败：{status_text}，线程返回 {exit_code}")

        entity_address = struct.unpack_from("<Q", response, SPAWN_REQ_OUT_ENTITY)[0]
        before_count = struct.unpack_from("<Q", response, SPAWN_REQ_BEFORE_COUNT)[0]
        after_count = struct.unpack_from("<Q", response, SPAWN_REQ_AFTER_COUNT)[0]
        entity_id = struct.unpack_from("<I", response, SPAWN_REQ_ENTITY_ID)[0]
        if not entity_address:
            raise TrainerError("即时生成失败：未返回实体地址")

        live_after = self.mem.read_u64(manager + LEVEL_OBJECT_COUNT)
        if live_after > MAX_LEVEL_OBJECT_COUNT:
            raise TrainerError(f"生成后对象数量异常：{live_after}")
        listed = live_after > before_live
        if after_count and after_count != live_after:
            after_count = live_after
        elif not after_count:
            after_count = live_after

        position = tuple(self.mem.read_f32(entity_address + offset) for offset in PLAYER_COORD_OFFSETS)
        return RuntimeEntitySpawnResult(
            entity_type=type_info.name,
            entity_id=entity_id,
            address=entity_address,
            position=(position[0], position[1], position[2]),
            before_count=int(before_count or before_live),
            after_count=int(after_count),
            listed=listed,
            template_level=template.level_name,
            template_id=template.entity_id,
        )

    def open_nearest_freezer(self, max_distance: float = FREEZER_OPEN_RADIUS) -> FreezerOpenResult:
        if not self.attached or not self.mem or not self.module:
            raise TrainerError("尚未连接游戏")
        player = self.player_ptr()
        if not player:
            raise TrainerError("尚未捕获玩家实体")

        px, py, pz = (self.mem.read_f32(player + offset) for offset in PLAYER_COORD_OFFSETS)
        level = self.mem.read_u64(player + PLAYER_LEVEL)
        if not level:
            raise TrainerError("尚未找到当前关卡")

        count = self.mem.read_u64(level + LEVEL_FREEZER_COUNT)
        array = self.mem.read_u64(level + LEVEL_FREEZER_ARRAY)
        if count <= 0 or not array:
            raise TrainerError("当前关卡没有笼子列表")
        if count > MAX_FREEZER_COUNT:
            raise TrainerError(f"笼子数量异常：{count}")

        freezer_type = self.module.base + FREEZER_TYPE_RVA
        best: FreezerOpenResult | None = None
        for index in range(count):
            try:
                freezer = self.mem.read_u64(array + index * 8)
                if not freezer:
                    continue
                if self.mem.read_u64(freezer + FREEZER_TYPE) != freezer_type:
                    continue
                if self.mem.read_u8(freezer + FREEZER_OPENED):
                    continue

                fx, fy, fz = (
                    self.mem.read_f32(freezer + offset) for offset in PLAYER_COORD_OFFSETS
                )
                if not all(math.isfinite(value) for value in (fx, fy, fz)):
                    continue

                dx = fx - px
                dy = fy - py
                dz = fz - pz
                distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                if best is None or distance < best.distance:
                    freezer_id = self.mem.read_u32(freezer + FREEZER_ID)
                    best = FreezerOpenResult(
                        address=freezer,
                        freezer_id=freezer_id,
                        distance=distance,
                        position=(fx, fy, fz),
                    )
            except TrainerError:
                continue

        if best is None:
            raise TrainerError("附近没有未打开的笼子")
        if best.distance > max_distance:
            raise TrainerError(
                f"最近未打开笼子距离 {best.distance:.2f}，超过 {max_distance:.1f}"
            )

        self.mem.write_u8(best.address + FREEZER_OPENED, 1)
        return best

    def status_counters(self) -> tuple[int, int, int]:
        if not self.attached or not self.mem:
            return (0, 0, 0)
        return (
            self.mem.read_counter(self.label("pick_count")),
            self.mem.read_counter(self.label("gate_count")),
            self.mem.read_counter(self.label("force_count")),
        )

    def reload_counters(self) -> tuple[int, int, int]:
        if not self.attached or not self.mem:
            return (0, 0, RELOAD_STATUS_IDLE)
        return (
            self.mem.read_counter(self.label("reload_request_count")),
            self.mem.read_counter(self.label("reload_done_count")),
            self.mem.read_u32(self.label("reload_status")),
        )


class TrainerApp:
    def __init__(
        self,
        debug_log_path: str | None = None,
        auto_close_ms: int | None = None,
    ) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.root.configure(bg="#f4f5f1")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.backend = LightTrainerBackend()
        self.vars = {key: tk.BooleanVar(value=False) for key, *_ in FLAG_DEFS}
        self.coord_vars = {axis: tk.StringVar(value="0.000") for axis in COORD_AXES}
        self.coord_step_var = tk.StringVar(value="1.000")
        self.coord_spinboxes: dict[str, ttk.Spinbox] = {}
        self.object_filter_var = tk.StringVar(value="全部")
        self.object_scope_var = tk.StringVar(value=OBJECT_SCOPE_ALL)
        self.object_radius_var = tk.StringVar(value=f"{OBJECT_RADIUS_DEFAULT:.3f}")
        self.object_coord_vars = {axis: tk.StringVar(value="0.000") for axis in COORD_AXES}
        self.object_direction_var = tk.StringVar(value="")
        self.object_appearance_var = tk.StringVar(value="")
        self.object_records: list[CoordinateObject] = []
        self.object_record_by_address: dict[int, CoordinateObject] = {}
        self.object_tree: ttk.Treeview | None = None
        self.object_filter_combo: ttk.Combobox | None = None
        self.object_scope_combo: ttk.Combobox | None = None
        self.object_radius_spinbox: ttk.Spinbox | None = None
        self.object_status_label: ttk.Label | None = None
        self.object_edit_label: ttk.Label | None = None
        self.object_spawn_label: ttk.Label | None = None
        self.spawn_filter_var = tk.StringVar()
        self.spawn_type_records: list[SpawnableEntityType] = []
        self.spawn_type_by_name: dict[str, SpawnableEntityType] = {}
        self.spawn_type_tree: ttk.Treeview | None = None
        self.spawn_template_records: list[SpawnEntityTemplate] = []
        self.spawn_template_by_iid: dict[str, SpawnEntityTemplate] = {}
        self.spawn_template_tree: ttk.Treeview | None = None
        self.level_routes = build_level_lookup()
        self.level_names = ordered_level_names(self.level_routes)
        self.level_completion_states: dict[str, LevelCompletion] = {}
        self.level_current_state: LevelState | None = None
        self.level_current_var = tk.StringVar(value="未读取")
        self.level_pending_var = tk.StringVar(value="未读取")
        self.level_transition_var = tk.StringVar(value="未读取")
        self.level_target_var = tk.StringVar()
        self.level_route_var = tk.StringVar(value="")
        self.level_completion_var = tk.StringVar(value="完成状态：未读取")
        self.level_status_label: ttk.Label | None = None
        self.level_tree: ttk.Treeview | None = None
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
        style.configure("Treeview", font=("Consolas", 9), rowheight=22)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=(18, 16, 18, 14))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"{APP_NAME} v{APP_VERSION}", style="Title.TLabel").pack(anchor="w")
        self.game_label = ttk.Label(frame, text="游戏：检测中", style="Status.TLabel")
        self.game_label.pack(anchor="w", pady=(12, 0))
        self.mod_label = ttk.Label(frame, text="修改：未开启", style="Status.TLabel")
        self.mod_label.pack(anchor="w", pady=(4, 0))
        self.player_label = ttk.Label(frame, text="玩家：等待捕获", style="Small.TLabel")
        self.player_label.pack(anchor="w", pady=(4, 2))
        self.capture_hint_label = ttk.Label(
            frame,
            text="提示：移动一下主角，工具才能捕获主角地址。",
            style="Small.TLabel",
        )
        self.capture_hint_label.pack(anchor="w", pady=(0, 8))

        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, pady=(4, 0))

        main_tab = ttk.Frame(notebook, padding=(8, 10, 8, 8))
        object_tab = ttk.Frame(notebook, padding=(8, 10, 8, 8))
        level_tab = ttk.Frame(notebook, padding=(8, 10, 8, 8))
        notebook.add(main_tab, text="能力")
        notebook.add(object_tab, text="对象")
        notebook.add(level_tab, text="关卡")

        self._build_main_tab(main_tab)
        self._build_object_tab(object_tab)
        self._build_level_tab(level_tab)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="全部关闭", command=self.all_off).pack(side="left")
        ttk.Button(buttons, text="重新连接", command=self.reconnect).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="关于", command=self.show_about).pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="退出", command=self.close).pack(side="right")

        self.error_label = ttk.Label(frame, text="", style="Small.TLabel", wraplength=840)
        self.error_label.pack(anchor="w", pady=(8, 0), fill="x")

    def _build_main_tab(self, frame: ttk.Frame) -> None:
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

        freezer_frame = ttk.Frame(frame)
        freezer_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(freezer_frame, text="金属笼子", style="Status.TLabel").pack(anchor="w")
        freezer_buttons = ttk.Frame(freezer_frame)
        freezer_buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(
            freezer_buttons,
            text=f"{OPEN_FREEZER_HOTKEY[1]}  打开面前笼子",
            command=self.open_freezer,
        ).pack(side="left")
        self.freezer_label = ttk.Label(freezer_frame, text="", style="Small.TLabel", wraplength=390)
        self.freezer_label.pack(anchor="w", pady=(4, 0), fill="x")

    def _build_object_tab(self, frame: ttk.Frame) -> None:
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="类型", style="Small.TLabel").pack(side="left")
        self.object_filter_combo = ttk.Combobox(
            toolbar,
            textvariable=self.object_filter_var,
            values=("全部",),
            width=20,
            state="readonly",
        )
        self.object_filter_combo.pack(side="left", padx=(6, 8))
        self.object_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.populate_object_tree())
        ttk.Label(toolbar, text="范围", style="Small.TLabel").pack(side="left")
        self.object_scope_combo = ttk.Combobox(
            toolbar,
            textvariable=self.object_scope_var,
            values=(OBJECT_SCOPE_ALL, OBJECT_SCOPE_RADIUS),
            width=12,
            state="readonly",
        )
        self.object_scope_combo.pack(side="left", padx=(6, 8))
        self.object_scope_combo.bind("<<ComboboxSelected>>", self.on_object_scope_changed)
        ttk.Label(toolbar, text="半径", style="Small.TLabel").pack(side="left")
        self.object_radius_spinbox = ttk.Spinbox(
            toolbar,
            from_=1.0,
            to=500.0,
            increment=1.0,
            textvariable=self.object_radius_var,
            width=7,
            format="%.3f",
            command=self.populate_object_tree,
            style="Coord.TSpinbox",
        )
        self.object_radius_spinbox.pack(side="left", padx=(6, 8))
        self.object_radius_var.trace_add("write", lambda *_args: self.populate_object_tree())
        self.update_object_radius_state()
        ttk.Button(toolbar, text="刷新对象", command=self.refresh_objects).pack(side="left")
        self.object_status_label = ttk.Label(toolbar, text="", style="Small.TLabel")
        self.object_status_label.pack(side="left", padx=(10, 0))

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill="x", pady=(8, 0))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("mark", "source", "type", "id", "position", "direction", "distance")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", height=10)
        headings = {
            "mark": "",
            "source": "数组",
            "type": "类型",
            "id": "ID",
            "position": "坐标",
            "direction": "朝向",
            "distance": "距离",
        }
        widths = {
            "mark": 26,
            "source": 64,
            "type": 150,
            "id": 96,
            "position": 230,
            "direction": 74,
            "distance": 78,
        }
        for column in columns:
            tree.heading(column, text=headings[column])
            tree.column(
                column,
                width=widths[column],
                minwidth=widths[column],
                anchor="w",
                stretch=column == "type",
            )

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree.bind("<<TreeviewSelect>>", self.on_object_selected)
        self.object_tree = tree

        editor = ttk.Frame(frame)
        editor.pack(fill="x", pady=(10, 0))
        ttk.Label(editor, text="选中坐标", style="Status.TLabel").pack(side="left", padx=(0, 10))
        for axis in COORD_AXES:
            group = ttk.Frame(editor)
            group.pack(side="left", padx=(0, 8))
            ttk.Label(group, text=axis.upper(), style="Small.TLabel").pack(anchor="w")
            ttk.Spinbox(
                group,
                from_=-COORD_LIMIT,
                to=COORD_LIMIT,
                increment=1.0,
                textvariable=self.object_coord_vars[axis],
                width=11,
                format="%.3f",
                style="Coord.TSpinbox",
            ).pack(anchor="w")
        ttk.Button(editor, text="读取选中", command=self.read_selected_object).pack(side="left", padx=(4, 0))
        ttk.Button(editor, text="写入选中", command=self.write_selected_object).pack(side="left", padx=(8, 0))

        self.object_edit_label = ttk.Label(frame, text="", style="Small.TLabel", wraplength=840)
        self.object_edit_label.pack(anchor="w", pady=(6, 0), fill="x")

        spawn_box = ttk.Frame(frame)
        spawn_box.pack(fill="both", expand=True, pady=(8, 0))
        spawn_row = ttk.Frame(spawn_box)
        spawn_row.pack(fill="x")
        ttk.Label(spawn_row, text="刷对象", style="Status.TLabel").pack(side="left", padx=(0, 10))
        ttk.Label(spawn_row, text="搜索", style="Small.TLabel").pack(side="left")
        ttk.Entry(spawn_row, textvariable=self.spawn_filter_var, width=24).pack(side="left", padx=(6, 8))
        self.spawn_filter_var.trace_add("write", lambda *_args: self.populate_spawn_type_tree())
        ttk.Button(
            spawn_row,
            text="刷新类型",
            command=self.refresh_spawn_types,
        ).pack(side="left")
        ttk.Button(
            spawn_row,
            text="在玩家面前生成",
            command=self.spawn_selected_type_runtime,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            spawn_row,
            text="重载当前存档",
            command=self.reload_current_level_from_object_tab,
        ).pack(side="left", padx=(8, 0))
        ttk.Label(
            spawn_row,
            text="生成实体后需要点击重载当前存档",
            style="Small.TLabel",
            wraplength=260,
        ).pack(side="left", padx=(8, 0))

        spawn_table = ttk.Frame(spawn_box)
        spawn_table.pack(fill="both", expand=True, pady=(8, 0))
        spawn_table.columnconfigure(0, weight=1)
        spawn_table.rowconfigure(0, weight=1)
        columns = ("name", "id", "size", "runtime", "loaded", "package", "levels")
        tree = ttk.Treeview(spawn_table, columns=columns, show="headings", selectmode="browse", height=6)
        spawn_headings = {
            "name": "类型",
            "id": "Type ID",
            "size": "大小",
            "runtime": "运行时",
            "loaded": "当前",
            "package": "资源记录",
            "levels": "关卡",
        }
        spawn_widths = {
            "name": 230,
            "id": 80,
            "size": 70,
            "runtime": 58,
            "loaded": 64,
            "package": 74,
            "levels": 54,
        }
        for column in columns:
            tree.heading(column, text=spawn_headings[column])
            tree.column(column, width=spawn_widths[column], minwidth=spawn_widths[column], anchor="w", stretch=column == "name")
        yscroll = ttk.Scrollbar(spawn_table, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=yscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        tree.bind("<<TreeviewSelect>>", self.on_spawn_type_selected)
        tree.bind("<Double-1>", lambda _event: self.spawn_selected_type_runtime())
        self.spawn_type_tree = tree

        template_table = ttk.Frame(spawn_box)
        template_table.pack(fill="both", expand=True, pady=(8, 0))
        template_table.columnconfigure(0, weight=1)
        template_table.rowconfigure(0, weight=1)
        template_columns = ("level", "id", "diff", "position", "direction", "appearance")
        template_tree = ttk.Treeview(
            template_table,
            columns=template_columns,
            show="headings",
            selectmode="browse",
            height=5,
        )
        template_headings = {
            "level": "属性模板",
            "id": "模板ID",
            "diff": "diff",
            "position": "原坐标",
            "direction": "朝向",
            "appearance": "外观",
        }
        template_widths = {
            "level": 210,
            "id": 100,
            "diff": 70,
            "position": 130,
            "direction": 70,
            "appearance": 210,
        }
        for column in template_columns:
            template_tree.heading(column, text=template_headings[column])
            template_tree.column(
                column,
                width=template_widths[column],
                minwidth=template_widths[column],
                anchor="w",
                stretch=column == "level",
            )
        template_yscroll = ttk.Scrollbar(template_table, orient="vertical", command=template_tree.yview)
        template_tree.configure(yscrollcommand=template_yscroll.set)
        template_tree.grid(row=0, column=0, sticky="nsew")
        template_yscroll.grid(row=0, column=1, sticky="ns")
        template_tree.bind("<Double-1>", lambda _event: self.spawn_selected_type_runtime())
        self.spawn_template_tree = template_tree

        self.object_spawn_label = ttk.Label(spawn_box, text="", style="Small.TLabel", wraplength=840)
        self.object_spawn_label.pack(anchor="w", pady=(6, 0), fill="x")

    def _build_level_tab(self, frame: ttk.Frame) -> None:
        current_box = ttk.Frame(frame)
        current_box.pack(fill="x")
        ttk.Label(current_box, text="当前关卡", style="Status.TLabel").pack(anchor="w")
        ttk.Label(
            current_box,
            textvariable=self.level_current_var,
            style="Small.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(6, 0), fill="x")
        ttk.Label(
            current_box,
            textvariable=self.level_pending_var,
            style="Small.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(3, 0), fill="x")
        ttk.Label(
            current_box,
            textvariable=self.level_transition_var,
            style="Small.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(3, 0), fill="x")

        target_box = ttk.Frame(frame)
        target_box.pack(fill="both", expand=True, pady=(10, 0))
        target_row = ttk.Frame(target_box)
        target_row.pack(fill="x")
        ttk.Label(target_row, text="关卡列表", style="Status.TLabel").pack(anchor="w")

        ttk.Label(
            target_box,
            textvariable=self.level_route_var,
            style="Small.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(6, 0), fill="x")
        ttk.Label(
            target_box,
            textvariable=self.level_completion_var,
            style="Small.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(2, 0), fill="x")

        level_list_row = ttk.Frame(target_box)
        level_list_row.pack(fill="both", expand=True, pady=(8, 0))

        tree_frame = ttk.Frame(level_list_row)
        tree_frame.pack(side="left", fill="both", expand=True)
        tree = ttk.Treeview(
            tree_frame,
            columns=("state", "level", "route", "flags"),
            show="headings",
            height=11,
            selectmode="browse",
        )
        tree.heading("state", text="状态")
        tree.heading("level", text="关卡")
        tree.heading("route", text="路线")
        tree.heading("flags", text="Flags")
        tree.column("state", width=80, stretch=False)
        tree.column("level", width=220, stretch=True)
        tree.column("route", width=300, stretch=True)
        tree.column("flags", width=70, stretch=False)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        tree.bind("<<TreeviewSelect>>", self.on_level_tree_selected)
        self.level_tree = tree
        self.populate_level_tree()

        level_action_buttons = ttk.Frame(level_list_row)
        level_action_buttons.pack(side="left", fill="y", padx=(10, 0), anchor="n")
        ttk.Button(
            level_action_buttons,
            text="刷新完成状态",
            command=self.refresh_level_completion,
        ).pack(fill="x")
        ttk.Button(
            level_action_buttons,
            text="切换选中关卡",
            command=self.switch_selected_level,
        ).pack(fill="x", pady=(8, 0))

        self.level_status_label = ttk.Label(frame, text="", style="Small.TLabel", wraplength=840)
        self.level_status_label.pack(anchor="w", pady=(8, 0), fill="x")
        if not self.level_routes:
            self.level_status_label.configure(
                text="关卡索引未生成：先运行 python tools\\extract_sinking_star_assets.py 可启用目标下拉和路线查询。"
            )

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

    def object_coordinate_values(self) -> tuple[float, float, float]:
        values: list[float] = []
        for axis in COORD_AXES:
            text = self.object_coord_vars[axis].get().strip()
            try:
                value = float(text)
            except ValueError as exc:
                raise TrainerError(f"{axis.upper()} 坐标不是有效数字") from exc
            if not math.isfinite(value) or abs(value) > COORD_LIMIT:
                raise TrainerError(f"{axis.upper()} 坐标超出允许范围")
            values.append(value)
        return (values[0], values[1], values[2])

    def set_object_coordinate_values(self, values: tuple[float, float, float]) -> None:
        for axis, value in zip(COORD_AXES, values):
            self.object_coord_vars[axis].set(f"{value:.3f}")

    def object_direction_value(self) -> float:
        text = self.object_direction_var.get().strip()
        if not text:
            raise TrainerError("朝向不能为空")
        try:
            value = float(text)
        except ValueError as exc:
            raise TrainerError("朝向不是有效数字") from exc
        if not math.isfinite(value):
            raise TrainerError("朝向不是有效数字")
        return normalize_degrees(value)

    def set_object_direction_value(self, value: float | None) -> None:
        self.object_direction_var.set("" if value is None else f"{value:.3f}")

    def object_appearance_value(self) -> str:
        value = self.object_appearance_var.get().strip()
        try:
            data = value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise TrainerError("外观只支持 ASCII 资源名") from exc
        if len(data) > OBJECT_APPEARANCE_MAX_LEN:
            raise TrainerError(f"外观资源名不能超过 {OBJECT_APPEARANCE_MAX_LEN} 字节")
        return value

    def set_object_property_values(self, record: CoordinateObject) -> None:
        self.set_object_direction_value(record.direction)
        self.object_appearance_var.set(record.appearance)

    def selected_object_address(self) -> int:
        if not self.object_tree:
            raise TrainerError("对象列表尚未初始化")
        selection = self.object_tree.selection()
        if not selection:
            raise TrainerError("尚未选择对象")
        return int(selection[0], 16)

    def selected_object_record(self) -> CoordinateObject:
        address = self.selected_object_address()
        record = self.object_record_by_address.get(address)
        if record is None:
            raise TrainerError("选中对象已不在当前列表，请刷新对象")
        return record

    def selected_spawn_type(self) -> SpawnableEntityType:
        if not self.spawn_type_tree:
            raise TrainerError("生成类型列表尚未初始化")
        selection = self.spawn_type_tree.selection()
        if not selection:
            raise TrainerError("请先在生成类型列表里选择一种对象")
        name = selection[0]
        item = self.spawn_type_by_name.get(name)
        if item is None:
            raise TrainerError("选中的生成类型已失效，请刷新类型")
        return item

    def selected_spawn_template(self) -> SpawnEntityTemplate:
        if not self.spawn_template_tree:
            raise TrainerError("属性模板列表尚未初始化")
        selection = self.spawn_template_tree.selection()
        if not selection:
            raise TrainerError("请先选择一个属性模板")
        item = self.spawn_template_by_iid.get(selection[0])
        if item is None:
            raise TrainerError("选中的属性模板已失效，请刷新类型")
        return item

    def on_spawn_type_selected(self, _event: object | None = None) -> None:
        try:
            spawn_type = self.selected_spawn_type()
            self.populate_spawn_template_tree(spawn_type)
        except Exception as exc:
            self.spawn_template_records = []
            self.spawn_template_by_iid = {}
            if self.spawn_template_tree:
                children = self.spawn_template_tree.get_children()
                if children:
                    self.spawn_template_tree.delete(*children)
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"属性模板：{exc}")

    def on_object_scope_changed(self, _event: tk.Event | None = None) -> None:
        self.update_object_radius_state()
        self.populate_object_tree()

    def update_object_radius_state(self) -> None:
        if not self.object_radius_spinbox:
            return
        state = "normal" if self.object_scope_var.get() == OBJECT_SCOPE_RADIUS else "disabled"
        self.object_radius_spinbox.configure(state=state)

    def object_radius(self) -> float:
        try:
            radius = float(self.object_radius_var.get())
        except ValueError:
            return OBJECT_RADIUS_DEFAULT
        if not math.isfinite(radius) or radius <= 0:
            return OBJECT_RADIUS_DEFAULT
        return radius

    def object_matches_scope(self, record: CoordinateObject) -> bool:
        scope = self.object_scope_var.get()
        if scope == OBJECT_SCOPE_RADIUS:
            return record.distance <= self.object_radius()
        return True

    def refresh_objects(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            self.object_records = self.backend.coordinate_objects()
            self.object_record_by_address = {
                record.address: record for record in self.object_records
            }
            names = ["全部"] + sorted(
                {record.type_info.name for record in self.object_records},
                key=str.lower,
            )
            if self.object_filter_combo:
                self.object_filter_combo.configure(values=tuple(names))
            if self.object_filter_var.get() not in names:
                self.object_filter_var.set("全部")
            self.populate_object_tree()
            if self.object_status_label:
                self.object_status_label.configure(text=f"已刷新 {len(self.object_records)} 个对象")
            self.refresh_spawn_types(silent=True)
        except Exception as exc:
            if self.object_status_label:
                self.object_status_label.configure(text=f"对象：{exc}")

    def populate_object_tree(self) -> None:
        if not self.object_tree:
            return
        try:
            selected = self.selected_object_address()
        except TrainerError:
            selected = 0
        tree = self.object_tree
        children = tree.get_children()
        if children:
            tree.delete(*children)
        wanted = self.object_filter_var.get()
        records = [
            record
            for record in self.object_records
            if (wanted == "全部" or record.type_info.name == wanted)
            and self.object_matches_scope(record)
        ]
        for record in records:
            x, y, z = record.position
            iid = f"{record.address:X}"
            direction = "" if record.direction is None else f"{record.direction:.0f}"
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    "P" if record.is_player else "",
                    f"{record.source}[{record.index}]",
                    record.type_info.name,
                    f"0x{record.entity_id:X}",
                    f"{x:.3f}, {y:.3f}, {z:.3f}",
                    direction,
                    f"{record.distance:.2f}",
                ),
            )
        if selected and tree.exists(f"{selected:X}"):
            tree.selection_set(f"{selected:X}")
            tree.see(f"{selected:X}")
        if self.object_status_label:
            self.object_status_label.configure(text=f"显示 {len(records)} / {len(self.object_records)}")

    def refresh_spawn_types(self, silent: bool = False) -> bool:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            self.spawn_type_records = self.backend.spawnable_entity_types(refresh=True)
            self.spawn_type_by_name = {
                item.name: item for item in self.spawn_type_records
            }
            self.populate_spawn_type_tree()
            if self.object_spawn_label and not silent:
                runtime_count = sum(1 for item in self.spawn_type_records if item.runtime)
                package_count = sum(1 for item in self.spawn_type_records if item.package_count)
                self.object_spawn_label.configure(
                    text=(
                        f"刷对象：已读取 {len(self.spawn_type_records)} 种类型；"
                        f"资源包 {package_count} 种，运行时已定位 {runtime_count} 种"
                    )
                )
            return True
        except Exception as exc:
            if silent:
                raise
            if self.object_spawn_label and not silent:
                self.object_spawn_label.configure(text=f"刷对象：{exc}")
            return False

    def populate_spawn_type_tree(self) -> None:
        if not self.spawn_type_tree:
            return
        tree = self.spawn_type_tree
        selected = ""
        selection = tree.selection()
        if selection:
            selected = selection[0]
        children = tree.get_children()
        if children:
            tree.delete(*children)
        needle = self.spawn_filter_var.get().strip().lower()
        records = [
            item
            for item in self.spawn_type_records
            if not needle or needle in item.name.lower()
        ]
        for item in records:
            tree.insert(
                "",
                "end",
                iid=item.name,
                values=(
                    item.name,
                    f"0x{item.type_id:X}" if item.type_id else "",
                    f"0x{item.type_size:X}" if item.type_size else "",
                    "是" if item.runtime else "否",
                    str(item.live_count),
                    str(item.package_count),
                    str(item.level_count),
                ),
            )
        if selected and tree.exists(selected):
            tree.selection_set(selected)
            tree.see(selected)
        elif records:
            tree.selection_set(records[0].name)
        self.on_spawn_type_selected(None)

    def populate_spawn_template_tree(self, spawn_type: SpawnableEntityType) -> None:
        if not self.spawn_template_tree:
            return
        tree = self.spawn_template_tree
        selected = ""
        selection = tree.selection()
        if selection:
            selected = selection[0]

        children = tree.get_children()
        if children:
            tree.delete(*children)
        self.spawn_template_records = []
        self.spawn_template_by_iid = {}

        try:
            templates = self.backend.spawn_templates_for_type(spawn_type.name)
        except TrainerError:
            raise
        except Exception as exc:
            raise TrainerError(f"读取属性模板失败：{exc}") from exc

        self.spawn_template_records = templates
        for index, template in enumerate(templates):
            iid = f"{index}:{template.level_name}:{template.entity_id:08X}"
            self.spawn_template_by_iid[iid] = template
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    template.level_name,
                    f"0x{template.entity_id:X}",
                    str(len(template.diff)),
                    spawn_template_position_text(template),
                    spawn_template_direction_text(template),
                    spawn_template_appearance_text(template),
                ),
            )

        if selected and tree.exists(selected):
            tree.selection_set(selected)
            tree.see(selected)
        elif templates:
            first = tree.get_children()[0]
            tree.selection_set(first)
            tree.see(first)

        if self.object_spawn_label:
            if templates:
                source_text = "运行时可生成" if spawn_type.runtime else "仅资源包模板"
                self.object_spawn_label.configure(
                    text=(
                        f"属性模板：{spawn_type.name} 已读取 {len(templates)} 个，"
                        f"{source_text}；生成时会复用选中模板的方向/变体/外观属性"
                    )
                )
            else:
                self.object_spawn_label.configure(
                    text=f"属性模板：{spawn_type.name} 在资源包里没有现成模板，不能可靠即时生成"
                )

    def on_object_selected(self, _event: object | None = None) -> None:
        try:
            address = self.selected_object_address()
            record = self.object_record_by_address.get(address)
            if record is not None:
                self.set_object_coordinate_values(record.position)
                self.set_object_property_values(record)
                if self.object_edit_label:
                    self.object_edit_label.configure(
                        text=f"选中：{record.type_info.name} 0x{record.address:X}"
                    )
        except Exception as exc:
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"对象：{exc}")

    def read_selected_object(self) -> None:
        try:
            address = self.selected_object_address()
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            values = self.backend.object_xyz(address)
            direction = self.backend.object_direction(address)
            appearance = self.backend.object_appearance(address)
            self.set_object_coordinate_values(values)
            self.set_object_direction_value(direction)
            self.object_appearance_var.set(appearance)
            record = self.object_record_by_address.get(address)
            if record:
                record.position = values
                record.direction = direction
                record.appearance = appearance
            self.populate_object_tree()
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"对象：已读取 0x{address:X}")
        except Exception as exc:
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"对象：{exc}")

    def write_selected_object(self) -> None:
        try:
            address = self.selected_object_address()
            values = self.object_coordinate_values()
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            self.backend.write_object_xyz(address, values)
            record = self.object_record_by_address.get(address)
            if record:
                record.position = values
            self.populate_object_tree()
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"对象：已写入 0x{address:X}")
        except Exception as exc:
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"对象：{exc}")

    def write_selected_object_properties(self) -> None:
        try:
            address = self.selected_object_address()
            direction = self.object_direction_value()
            appearance = self.object_appearance_value()
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            self.backend.write_object_direction(address, direction)
            self.backend.write_object_appearance(address, appearance)
            record = self.object_record_by_address.get(address)
            if record:
                record.direction = direction
                record.appearance = appearance
            self.populate_object_tree()
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"属性：已写入 0x{address:X}")
        except Exception as exc:
            if self.object_edit_label:
                self.object_edit_label.configure(text=f"属性：{exc}")

    def fill_object_target_from_player(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            values = self.backend.player_xyz()
            self.set_object_coordinate_values(values)
            if self.object_spawn_label:
                self.object_spawn_label.configure(text="刷对象：目标坐标已设为玩家位置")
        except Exception as exc:
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"刷对象：{exc}")

    def spawn_selected_object_runtime(self) -> None:
        self.spawn_selected_type_runtime()

    def start_current_save_reload(self) -> str:
        return self.backend.queue_current_save_reload()

    def spawn_selected_type_runtime(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            if not self.spawn_type_records:
                self.refresh_spawn_types(silent=True)
            spawn_type = self.selected_spawn_type()
            if not spawn_type.runtime or not spawn_type.address:
                raise TrainerError(
                    f"{spawn_type.name} 只在资源包里逆向到模板，当前运行时尚未定位类型地址，不能即时生成"
                )
            template = self.selected_spawn_template()
            values = self.backend.player_front_xyz()
            self.set_object_coordinate_values(values)
            result = self.backend.spawn_runtime_entity(spawn_type, values, template)
            try:
                self.refresh_objects()
            except Exception:
                pass
            if self.object_spawn_label:
                x, y, z = result.position
                list_text = "已进入对象列表" if result.listed else "未进入通用对象列表"
                message = (
                    f"刷对象：已在玩家前方生成 {result.entity_type} "
                    f"模板={result.template_level}/0x{result.template_id:X} "
                    f"ID=0x{result.entity_id:X} 地址=0x{result.address:X} "
                    f"对象数 {result.before_count}->{result.after_count} {list_text} "
                    f"坐标=({x:.3f}, {y:.3f}, {z:.3f})"
                )
                self.object_spawn_label.configure(text=message)
            self.debug(
                f"spawn_runtime type={result.entity_type} id=0x{result.entity_id:X} "
                f"addr=0x{result.address:X} count={result.before_count}->{result.after_count} "
                f"listed={result.listed} template={result.template_level}/0x{result.template_id:X}"
            )
        except Exception as exc:
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"刷对象：{exc}")

    def reload_current_level_from_object_tab(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            if not self.backend.attach_if_needed():
                raise TrainerError(self.backend.last_error or "尚未连接游戏")
            campaign_name = self.start_current_save_reload()
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"重载：已请求重新加载当前存档 {campaign_name}")
        except Exception as exc:
            self.backend.last_error = str(exc)
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"重载：{exc}")

    def generate_spawn_package_copy(self) -> None:
        try:
            record = self.selected_object_record()
            if record.is_player:
                raise TrainerError("不要用玩家实体做刷对象模板")
            values = self.object_coordinate_values()
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            result = self.backend.create_spawn_package_copy(
                record.type_info.name,
                record.entity_id,
                values,
            )
            counts = ",".join(f"{key}:{value}" for key, value in result.patch_counts.items())
            if self.object_spawn_label:
                self.object_spawn_label.configure(
                    text=(
                        f"刷对象：已生成 {os.path.normpath(result.output_path)}；"
                        f"{result.entity_type} 模板=0x{result.template_id:X} "
                        f"新ID=0x{result.new_id:X} "
                        f"记录 {result.old_record_count}->{result.new_record_count} "
                        f"字段 {counts}"
                    )
                )
            self.debug(
                f"spawn_package level={result.level_name} type={result.entity_type} "
                f"template=0x{result.template_id:X} new=0x{result.new_id:X} "
                f"path={result.output_path}"
            )
        except Exception as exc:
            if self.object_spawn_label:
                self.object_spawn_label.configure(text=f"刷对象：{exc}")

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

    def open_freezer(self) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            result = self.backend.open_nearest_freezer()
            self.freezer_label.configure(
                text=f"笼子：已打开 ID {result.freezer_id}，距离 {result.distance:.2f}"
            )
            self.debug(
                f"open_freezer id={result.freezer_id} "
                f"addr=0x{result.address:X} distance={result.distance:.2f}"
            )
        except Exception as exc:
            self.backend.last_error = str(exc)
            self.freezer_label.configure(text=f"笼子：{exc}")
            self.debug(f"open_freezer_error {type(exc).__name__}")

    def level_route_text(self, level_name: str) -> str:
        routes = self.level_routes.get(level_name, [])
        return " / ".join(f"{level_set}[{index}]" for level_set, index in routes)

    def level_display_names(self) -> list[str]:
        names = list(self.level_names)
        known = set(names)
        names.extend(sorted(name for name in self.level_completion_states if name not in known))
        return names

    def populate_level_tree(self) -> None:
        if not self.level_tree:
            return
        selected = self.level_target_var.get().strip()
        tree = self.level_tree
        children = tree.get_children()
        if children:
            tree.delete(*children)

        for level_name in self.level_display_names():
            completion = self.level_completion_states.get(level_name)
            flags_text = f"0x{completion.flags:02X}" if completion else "-"
            tree.insert(
                "",
                "end",
                iid=level_name,
                values=(
                    level_completion_text(completion),
                    level_name,
                    self.level_route_text(level_name),
                    flags_text,
                ),
            )
        if selected and tree.exists(selected):
            tree.selection_set(selected)
            tree.see(selected)

    def on_level_tree_selected(self, _event: object | None = None) -> None:
        if not self.level_tree:
            return
        selection = self.level_tree.selection()
        if not selection:
            return
        self.level_target_var.set(selection[0])
        self.lookup_target_level()

    def refresh_level_completion(self, silent: bool = False) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            states = self.backend.level_completion_states()
            self.level_completion_states = states
            self.populate_level_tree()

            solved = sum(1 for state in states.values() if state.solved)
            recorded = len(states)
            known_solved = sum(
                1
                for level_name in self.level_names
                if self.level_completion_states.get(level_name)
                and self.level_completion_states[level_name].solved
            )
            self.level_completion_var.set(
                f"完成状态：记录 {recorded} 个，已完成 {solved} 个；当前列表命中已完成 {known_solved} 个"
            )
            if self.level_status_label and not silent:
                self.level_status_label.configure(text="关卡：完成状态已刷新")
            target = self.level_target_var.get().strip()
            if target:
                self.lookup_target_level()
        except Exception as exc:
            if not silent:
                self.backend.last_error = str(exc)
                if self.level_status_label:
                    self.level_status_label.configure(text=f"完成状态：{exc}")

    def refresh_level_state(self, silent: bool = False) -> None:
        try:
            self.backend.last_attach_attempt = 0.0
            self.backend.attach_if_needed()
            state = self.backend.current_level_state()
            self.level_current_state = state
            self.level_current_var.set(
                f"当前：{state.level_set}[{state.level_index}]  {state.level_name or '(unknown)'}"
            )
            self.level_pending_var.set(
                f"待载入：{state.pending_level_set or '-'}[{state.pending_level_index}]"
            )
            self.level_transition_var.set(
                f"过渡状态：state={state.transition_state} phase={state.transition_phase}"
            )
            if self.level_status_label and not silent:
                self.level_status_label.configure(text="关卡：已刷新")
        except Exception as exc:
            if not silent:
                self.backend.last_error = str(exc)
                if self.level_status_label:
                    self.level_status_label.configure(text=f"关卡：{exc}")

    def update_level_completion_label(self, target: str) -> None:
        completion = self.level_completion_states.get(target)
        if completion is None:
            self.level_completion_var.set(f"完成状态：{target} 未记录")
            return
        state_text = level_completion_text(completion)
        self.level_completion_var.set(
            f"完成状态：{target} {state_text} flags=0x{completion.flags:02X}"
        )

    def lookup_target_level(self) -> None:
        target = self.level_target_var.get().strip()
        if not target:
            if self.level_status_label:
                self.level_status_label.configure(text="关卡：请先在表格里选择关卡")
            return
        self.update_level_completion_label(target)

        matches = self.level_routes.get(target, [])
        if not matches:
            self.level_route_var.set(
                "静态索引未命中；直接切换时会再读取游戏运行时 catalog。"
            )
            if self.level_status_label:
                self.level_status_label.configure(text="关卡：目标未命中静态索引，可尝试直接切换")
            return

        state = self.level_current_state
        route_parts: list[str] = []
        for level_set, index in matches:
            part = f"{level_set}[{index}]"
            if state and level_set == state.level_set:
                delta = index - state.level_index
                if delta:
                    part += f"；相对当前 {delta:+d}"
                else:
                    part += "；当前关卡"
            route_parts.append(part)

        self.level_route_var.set("路线：" + " / ".join(route_parts))
        if self.level_status_label:
            self.level_status_label.configure(text="关卡：目标已命中索引，可直接切换")

    def selected_level_name(self) -> str:
        target = self.level_target_var.get().strip()
        if not target and self.level_tree:
            selection = self.level_tree.selection()
            if selection:
                target = selection[0]
                self.level_target_var.set(target)
        if not target:
            raise TrainerError("请先在表格里选择关卡")
        if any(ch.isspace() for ch in target):
            raise TrainerError("目标关卡名不能包含空白字符")
        return target

    def switch_selected_level(self) -> None:
        try:
            target = self.selected_level_name()
            self.backend.last_attach_attempt = 0.0
            if not self.backend.attach_if_needed():
                raise TrainerError(self.backend.last_error or "尚未连接游戏")
            result = self.backend.request_level_switch(target)
            self.level_route_var.set(
                f"运行时路线：{result.level_set}[{result.level_index}]  "
                f"{result.level_name}  ptr=0x{result.level_set_ptr:X}"
            )
            if self.level_status_label:
                self.level_status_label.configure(
                    text=(
                        "关卡：已触发直接切换，"
                        f"state={result.transition_state} phase={result.transition_phase}"
                    )
                )
            self.debug(
                f"level_switch target={target} set={result.level_set} "
                f"index={result.level_index} ptr=0x{result.level_set_ptr:X}"
            )
            self.refresh_level_state(silent=True)
        except Exception as exc:
            self.backend.last_error = str(exc)
            if self.level_status_label:
                self.level_status_label.configure(text=f"关卡：{exc}")

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
        about = tk.Toplevel(self.root)
        about.title("关于")
        about.transient(self.root)
        about.resizable(False, False)
        about.configure(bg="#f4f5f1")

        frame = ttk.Frame(about, padding=(18, 16, 18, 14))
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"{APP_NAME} v{APP_VERSION}", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="作者：不是吴昊的wh", style="Status.TLabel").pack(anchor="w", pady=(8, 0))
        ttk.Label(frame, text="GitHub 仓库：", style="Status.TLabel").pack(anchor="w", pady=(12, 0))

        link = tk.Label(
            frame,
            text="wudi-7mi/sinkingstarhero",
            bg="#f4f5f1",
            fg="#0b57d0",
            cursor="hand2",
            font=("Segoe UI", 9, "underline"),
        )
        link.pack(anchor="w", pady=(2, 0))
        link.bind("<Button-1>", lambda _event: webbrowser.open_new_tab(GITHUB_REPOSITORY_URL))

        ttk.Button(frame, text="关闭", command=about.destroy).pack(anchor="e", pady=(14, 0))
        about.bind("<Escape>", lambda _event: about.destroy())

        about.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - about.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - about.winfo_height()) // 2
        about.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        about.grab_set()
        about.focus_set()

    def reconnect(self) -> None:
        self.backend.detach()
        self.backend.last_attach_attempt = 0.0
        ok = self.backend.attach_if_needed()
        self.debug(f"manual_reconnect ok={ok}")
        self.on_flags_changed()
        if ok:
            self.refresh_level_state(silent=True)
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
            freezer_key, _freezer_hotkey, freezer_vk = OPEN_FREEZER_HOTKEY
            if user32.GetAsyncKeyState(freezer_vk) & 0x8000:
                active_now.add(freezer_key)
                if freezer_key not in self.debounced_hotkeys:
                    self.open_freezer()
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
            if self.backend.attached and self.tick_count % 20 == 0:
                self.refresh_level_state(silent=True)
                self.refresh_reload_status(silent=True)
        except Exception as exc:
            self.backend.last_error = str(exc)
            self.debug(f"tick_exception {type(exc).__name__}")
        self.refresh_labels()
        if self.tick_count <= 5 or self.tick_count % 20 == 0:
            self.debug("refresh")
        self.root.after(50, self.tick)

    def refresh_reload_status(self, silent: bool = False) -> None:
        if not self.object_spawn_label or not self.backend.attached:
            return
        try:
            requests, done, status = self.backend.reload_counters()
        except Exception:
            return
        if not requests:
            return
        status_text = RELOAD_STATUS_MESSAGES.get(status, f"状态 {status}")
        if status in (
            RELOAD_STATUS_RUNNING,
            RELOAD_STATUS_OK,
            RELOAD_STATUS_BUSY,
            RELOAD_STATUS_NO_CAMPAIGN,
            RELOAD_STATUS_SAVING,
            RELOAD_STATUS_WAITING_SAVE,
            RELOAD_STATUS_LOADING,
        ) or not silent:
            self.object_spawn_label.configure(text=f"重载：{status_text}（请求 {requests}，完成 {done}）")

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
                self.player_label.configure(text="玩家：请移动一下主角以捕获地址")
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
    post_update_addr = 0x1401CA8B3
    code, labels = build_remote_code(
        remote_base,
        pick_return=pick_addr + PICK_RETURN_DELTA,
        gate_skip=gate_addr + GATE_SKIP_DELTA,
        gate_through=gate_addr + GATE_THROUGH_DELTA,
        gate_r14_continue=gate_addr + GATE_R14_CONTINUE_DELTA,
        post_update_return=post_update_addr + MAIN_LOOP_RELOAD_RETURN_DELTA,
        campaign_load=0x140048880,
        campaign_save_current=0x140154860,
        entity_manager_save=0x1401B5EA0,
        runtime_context=0x140731110,
        current_entity_manager=0x1409ACB50,
        pending_level_set=0x1409ACF60,
        transition_phase=0x1409AECD0,
        save_queue_count=0x1409ACC98,
        post_update_state=0x14072E9B0,
    )
    assert labels["pick_hook"] == remote_base
    assert "through_enabled" in labels
    assert len(make_jmp_patch(pick_addr, labels["pick_hook"], PICK_PATCH_LEN)) == PICK_PATCH_LEN
    assert len(make_jmp_patch(gate_addr, labels["gate_hook"], GATE_PATCH_LEN)) == GATE_PATCH_LEN
    assert len(make_jmp_patch(post_update_addr, labels["post_update_hook"], MAIN_LOOP_RELOAD_HOOK_LEN)) == MAIN_LOOP_RELOAD_HOOK_LEN
    assert "campaign_name_buffer" in labels
    print(f"self-test ok: remote_code={len(code)} bytes labels={len(labels)}")

    spawn_code, spawn_labels = build_runtime_spawn_code(0x140700000)
    assert spawn_labels["spawn_entry"] == 0x140700000
    assert "spawn_cleanup" in spawn_labels
    assert len(spawn_code) < SPAWN_REMOTE_BLOCK_SIZE // 2
    print(f"self-test ok: spawn_code={len(spawn_code)} bytes labels={len(spawn_labels)}")

    exe_path = os.path.join(os.getcwd(), PROCESS_NAME)
    if os.path.exists(exe_path):
        with open(exe_path, "rb") as fh:
            data = fh.read()
        pick_count = data.count(PICK_SIGNATURE)
        gate_count = data.count(GATE_SIGNATURE)
        post_update_count = data.count(MAIN_LOOP_RELOAD_HOOK_SIGNATURE)
        print(f"disk AOB: pick={pick_count} gate={gate_count} post_update={post_update_count}")
        if pick_count != 1 or gate_count != 1 or post_update_count != 1:
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
                    ("post_update", MAIN_LOOP_RELOAD_HOOK_RVA, MAIN_LOOP_RELOAD_HOOK_SIGNATURE),
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
        if "reload_status" in backend.hook.labels:
            try:
                requests, done, status = backend.reload_counters()
                status_text = RELOAD_STATUS_MESSAGES.get(status, str(status))
                lines.append(f"reload_requests={requests}")
                lines.append(f"reload_done={done}")
                lines.append(f"reload_status={status} {status_text}")
            except Exception as exc:
                lines.append(f"reload_probe_error={exc}")
        lines.append(f"player_ptr=0x{backend.player_ptr():X}")
        try:
            level = backend.current_level_state()
            lines.append(f"current_level_set={level.level_set}")
            lines.append(f"current_level_index={level.level_index}")
            lines.append(f"current_level_name={level.level_name}")
            lines.append(f"pending_level_set={level.pending_level_set}")
            lines.append(f"pending_level_index={level.pending_level_index}")
            lines.append(f"transition_state={level.transition_state}")
            lines.append(f"transition_phase={level.transition_phase}")
        except Exception as exc:
            lines.append(f"level_probe_error={exc}")
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
