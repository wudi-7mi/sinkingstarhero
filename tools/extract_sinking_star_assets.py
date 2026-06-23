#!/usr/bin/env python3
"""Build a local asset index for Order of the Sinking Star Demo.

The script is read-only with respect to the game install. It parses the
``simp`` packages that carry a trailing ``toc!`` table, extracts level entity
and manifest blobs to a local analysis directory, and writes CSV summaries that
can be cross-checked against IDA/CE notes.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class PackageEntry:
    package: str
    name: str
    offset: int
    size: int


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def parse_simp_package(path: Path) -> tuple[int, list[PackageEntry]]:
    data = path.read_bytes()
    if data[:4] != b"simp":
        raise ValueError(f"{path} does not start with simp")

    toc_offset = data.rfind(b"toc!")
    if toc_offset < 0:
        return -1, []

    count = read_u64(data, toc_offset + 8)
    cursor = toc_offset + 0x40
    entries: list[PackageEntry] = []

    for _ in range(count):
        if cursor + 4 > len(data):
            raise ValueError(f"{path}: TOC ended while reading name length")
        name_len = read_u32(data, cursor)
        cursor += 4

        name_end = cursor + name_len
        if name_end >= len(data):
            raise ValueError(f"{path}: TOC entry name overruns file")
        name = data[cursor:name_end].decode("ascii", errors="replace")
        cursor = name_end

        if data[cursor] != 0:
            raise ValueError(f"{path}: TOC entry {name!r} is not NUL-terminated")
        cursor += 1

        size = read_u64(data, cursor)
        cursor += 8
        offset = read_u64(data, cursor)
        cursor += 8

        if offset + size > toc_offset:
            raise ValueError(f"{path}: TOC entry {name!r} points outside payload")
        entries.append(PackageEntry(path.name, name, offset, size))

    return toc_offset, entries


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def inventory_files(game_root: Path) -> list[dict]:
    rows: list[dict] = []
    for folder_name in ("data", "data-common", "data-pc"):
        folder = game_root / folder_name
        if not folder.exists():
            continue
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            rows.append(
                {
                    "folder": folder_name,
                    "relative_path": path.relative_to(game_root).as_posix(),
                    "name": path.name,
                    "extension": path.suffix,
                    "size": path.stat().st_size,
                }
            )
    return rows


def copy_package_entries(package_path: Path, entries: Iterable[PackageEntry], output_dir: Path) -> None:
    data = package_path.read_bytes()
    for entry in entries:
        if not (
            entry.name.endswith(".entities")
            or entry.name.endswith(".level_manifest")
            or entry.name.endswith(".level_set")
        ):
            continue
        target = output_dir / "extracted_levels" / entry.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data[entry.offset : entry.offset + entry.size])


def manifest_sections(text: str) -> dict[str, list[str]]:
    sections = {"meshes": [], "textures": []}
    current: str | None = None
    for raw_line in text.replace("\r\n", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(";;;;;"):
            key = line[5:].strip().lower()
            current = key if key in sections else None
            continue
        if current:
            sections[current].append(line)
    return sections


def build_level_rows(game_root: Path, entries: list[PackageEntry], output_dir: Path) -> tuple[list[dict], list[dict]]:
    by_level: dict[str, dict] = {}
    for entry in entries:
        if not entry.name.startswith("data-common/"):
            continue
        suffix = None
        if entry.name.endswith(".entities"):
            suffix = ".entities"
        elif entry.name.endswith(".level_manifest"):
            suffix = ".level_manifest"
        if not suffix:
            continue

        level = Path(entry.name).name[: -len(suffix)]
        row = by_level.setdefault(
            level,
            {
                "level": level,
                "entities_size": "",
                "entities_offset": "",
                "manifest_size": "",
                "manifest_offset": "",
                "paint_size": "",
                "lightmap_size": "",
                "preview_texture_size": "",
                "mesh_refs": "",
                "texture_refs": "",
            },
        )
        key = "entities" if suffix == ".entities" else "manifest"
        row[f"{key}_size"] = entry.size
        row[f"{key}_offset"] = entry.offset

    asset_rows: list[dict] = []
    manifest_root = output_dir / "extracted_levels" / "data-common"
    for level, row in by_level.items():
        paint = game_root / "data-common" / f"{level}.all_paint_data"
        lightmap = game_root / "data-common" / f"{level}.all_lightmap_data"
        preview = game_root / "data-pc" / f"__{level}.texture"
        if paint.exists():
            row["paint_size"] = paint.stat().st_size
        if lightmap.exists():
            row["lightmap_size"] = lightmap.stat().st_size
        if preview.exists():
            row["preview_texture_size"] = preview.stat().st_size

        manifest = manifest_root / f"{level}.level_manifest"
        if not manifest.exists():
            continue
        text = manifest.read_text(encoding="utf-8", errors="replace")
        sections = manifest_sections(text)
        row["mesh_refs"] = len(sections["meshes"])
        row["texture_refs"] = len(sections["textures"])

        for mesh in sections["meshes"]:
            candidate = game_root / "data-common" / f"{mesh}.compressed_mesh"
            asset_rows.append(
                {
                    "level": level,
                    "kind": "mesh",
                    "asset": mesh,
                    "candidate_path": candidate.relative_to(game_root).as_posix(),
                    "exists": candidate.exists(),
                }
            )
        for texture in sections["textures"]:
            candidate = game_root / "data-pc" / f"{texture}.texture"
            asset_rows.append(
                {
                    "level": level,
                    "kind": "texture",
                    "asset": texture,
                    "candidate_path": candidate.relative_to(game_root).as_posix(),
                    "exists": candidate.exists(),
                }
            )

    return [by_level[key] for key in sorted(by_level)], asset_rows


def parse_logs(game_root: Path) -> list[dict]:
    rows: list[dict] = []
    log_dir = game_root / "logs"
    if not log_dir.exists():
        return rows

    manifest_re = re.compile(r'Found level manifest for "([^"]+)" with (\d+) meshes and (\d+) textures')
    loading_re = re.compile(r"Loading level '([^']+)'")
    async_re = re.compile(r"Begin loading async with (\d+) (meshes|textures): (.+?) - (.+)")

    for log_path in sorted(log_dir.glob("*.txt")):
        for line_number, line in enumerate(log_path.read_text(errors="replace").splitlines(), start=1):
            match = manifest_re.search(line)
            if match:
                rows.append(
                    {
                        "log": log_path.name,
                        "line": line_number,
                        "event": "found_manifest",
                        "level": match.group(1),
                        "count": "",
                        "kind": "",
                        "first": match.group(2),
                        "last": match.group(3),
                    }
                )
                continue
            match = loading_re.search(line)
            if match:
                rows.append(
                    {
                        "log": log_path.name,
                        "line": line_number,
                        "event": "loading_level",
                        "level": match.group(1),
                        "count": "",
                        "kind": "",
                        "first": "",
                        "last": "",
                    }
                )
                continue
            match = async_re.search(line)
            if match:
                rows.append(
                    {
                        "log": log_path.name,
                        "line": line_number,
                        "event": "begin_async",
                        "level": "",
                        "count": match.group(1),
                        "kind": match.group(2),
                        "first": match.group(3),
                        "last": match.group(4),
                    }
                )
    return rows


def write_notes(output_dir: Path, package_rows: list[dict], level_rows: list[dict]) -> None:
    notes = [
        "# Sinking Star Asset Notes",
        "",
        "## Confirmed layout",
        "",
        "- `data/levels.package` starts with `simp` and carries a trailing `toc!` table.",
        "- The `toc!` table header is followed by little-endian entries: `u32 name_len`, ASCII name, NUL, `u64 size`, `u64 payload_offset`.",
        "- `levels.package` contains packaged `data-common/<level>.entities`, `data-common/<level>.level_manifest`, and `data/level_sets/*.level_set` payloads.",
        "- Per-level paint and lightmap files are loose files in `data-common` as `<level>.all_paint_data` and `<level>.all_lightmap_data`.",
        "- Mesh assets are loose `data-common/*.compressed_mesh` files.",
        "- Texture assets are loose `data-pc/*.texture` files; many per-level preview textures use `__<level>.texture`.",
        "",
        "## IDA anchors",
        "",
        "- `sub_140042F00` reads `%/%.level_manifest`, parses `;;;;; meshes` / `;;;;; textures`, and logs `Found level manifest...`.",
        "- `sub_1402295E0` reads `%/%.all_paint_data` and `%/%.all_lightmap_data`.",
        "- `sub_1400BF120` recognizes catalog asset extensions including `entities`, `level_manifest`, `all_paint_data`, and `all_lightmap_data`.",
        "",
        "## CE read-only checks",
        "",
        "- `sinking_star.exe+67c1d7` -> `%/%.level_manifest`",
        "- `sinking_star.exe+690c14` -> `%/%.all_paint_data`",
        "- `sinking_star.exe+6901f7` -> `%/%.all_lightmap_data`",
        "- `sinking_star.exe+682d43` -> `data-common`",
        "- `sinking_star.exe+682d4f` -> `data-pc`",
        "- `sinking_star.exe+68d40f` -> `Loading level '%'`",
        "",
        "## Summary",
        "",
        f"- Parsed package entries: {len(package_rows)}",
        f"- Indexed levels: {len(level_rows)}",
        "",
        "Generated files:",
        "",
        "- `package_entries.csv`",
        "- `level_index.csv`",
        "- `level_manifest_assets.csv`",
        "- `resource_inventory.csv`",
        "- `log_level_loads.csv`",
        "- `extracted_levels/`",
    ]
    (output_dir / "asset_notes.md").write_text("\n".join(notes) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_repo = Path(__file__).resolve().parents[1]
    parser.add_argument("--game-root", type=Path, default=default_repo.parent)
    parser.add_argument("--output", type=Path, default=default_repo / "analysis_out")
    args = parser.parse_args()

    game_root = args.game_root.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    package_rows: list[dict] = []
    all_entries: list[PackageEntry] = []
    for package_path in sorted((game_root / "data").glob("*.package")):
        toc_offset, entries = parse_simp_package(package_path)
        for entry in entries:
            package_rows.append(
                {
                    "package": entry.package,
                    "name": entry.name,
                    "offset": entry.offset,
                    "size": entry.size,
                    "toc_offset": toc_offset,
                }
            )
        if package_path.name == "levels.package":
            copy_package_entries(package_path, entries, output_dir)
            all_entries.extend(entries)

    level_rows, asset_rows = build_level_rows(game_root, all_entries, output_dir)
    resource_rows = inventory_files(game_root)
    log_rows = parse_logs(game_root)

    write_csv(output_dir / "package_entries.csv", package_rows, ["package", "name", "offset", "size", "toc_offset"])
    write_csv(
        output_dir / "level_index.csv",
        level_rows,
        [
            "level",
            "entities_size",
            "entities_offset",
            "manifest_size",
            "manifest_offset",
            "paint_size",
            "lightmap_size",
            "preview_texture_size",
            "mesh_refs",
            "texture_refs",
        ],
    )
    write_csv(output_dir / "level_manifest_assets.csv", asset_rows, ["level", "kind", "asset", "candidate_path", "exists"])
    write_csv(output_dir / "resource_inventory.csv", resource_rows, ["folder", "relative_path", "name", "extension", "size"])
    write_csv(output_dir / "log_level_loads.csv", log_rows, ["log", "line", "event", "level", "count", "kind", "first", "last"])
    write_notes(output_dir, package_rows, level_rows)

    summary = {
        "game_root": str(game_root),
        "output": str(output_dir),
        "package_entries": len(package_rows),
        "levels": len(level_rows),
        "manifest_assets": len(asset_rows),
        "resource_files": len(resource_rows),
        "log_events": len(log_rows),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
