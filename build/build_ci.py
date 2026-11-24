#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI build driver for the OPEN-SOURCE edition.

Two modes:
  build   -- PyInstaller onedir main app + one-file setup, then create
             out/unsigned.zip with three unsigned PE copies for SignPath.
  repack  -- take the signed ZIP returned by SignPath, put every signed PE
             back at its real path, rebuild the portable ZIP (CRC changes),
             assemble out/release/ and write SHA256SUMS.txt.

Only meant to run on GitHub-hosted Windows runners. No signing is done here:
SignPath is the sole signer, and nothing built locally is ever submitted.

The open-source edition uses ASCII file names to avoid code-page problems in
CI, ZIP archives and signing policies; replace APP_* constants if you keep the
Chinese product file names.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

APP_NAME = "Toolbox-All-in-One"
MAIN_EXE_NAME = APP_NAME + ".exe"
SETUP_EXE_NAME = "Setup-" + APP_NAME + ".exe"
PORTABLE_ZIP_NAME = APP_NAME + "-portable.zip"
UNSIGNED_MEMBERS = ("main.exe", "setup.exe", "portable.exe")


def parse_version(v: str) -> tuple[int, int, int, int]:
    parts = v.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        raise ValueError(f"version must be four numeric parts, got {v!r}")
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def version_info_text(version: str, product: str) -> str:
    """PyInstaller --version-file content.

    SignPath enforces product-name / product-version in default.xml, so these
    MUST match the parameters passed to the signing request.
    """
    a, b, c, d = parse_version(version)
    tup = f"({a}, {b}, {c}, {d})"
    return f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tup},
    prodvers={tup},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904b0', [
        StringStruct('CompanyName', '{product}'),
        StringStruct('FileDescription', '{product}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{APP_NAME}'),
        StringStruct('LegalCopyright', 'MIT License'),
        StringStruct('OriginalFilename', '{MAIN_EXE_NAME}'),
        StringStruct('ProductName', '{product}'),
        StringStruct('ProductVersion', '{version}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
'''


def pyinstaller(args: list[str], cwd: Path) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", *args]
    print("RUN:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(cwd), check=True)


def build(root: Path, out: Path, version: str, product: str) -> None:
    src = root / "02-程序文件"
    if not (src / "main.py").is_file():
        raise SystemExit(f"missing application source: {src / 'main.py'}")
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("dist", "_work", "_spec", "signed", "release", "portable"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    vi = out / "_spec" / "version_info.txt"
    vi.write_text(version_info_text(version, product), encoding="utf-8")

    common = [
        "--noconfirm", "--clean", "--windowed",
        "--version-file", str(vi),
        "--distpath", str(out / "dist"),
        "--workpath", str(out / "_work"),
        "--specpath", str(out / "_spec"),
    ]

    # 1) main application: onedir (no self-extracting stub, fewer false positives)
    # NOTE: do NOT use --collect-submodules PySide6 -- it walks the entire Qt
    # module tree (Qt3D/QtBluetooth/QtQuick/...) and can hang for hours.
    # PyInstaller's Qt hooks already follow the modules we actually import;
    # list them explicitly here only to also catch importlib-based lazy loads.
    qt_modules = [
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
        "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtPrintSupport",
        "PySide6.QtWebEngineWidgets",
    ]
    pyinstaller_args = [
        "main.py", "--onedir", "--name", APP_NAME,
        "--collect-binaries", "PySide6",
        "--collect-submodules", "app",          # lazy imports via importlib
        *[a for m in qt_modules for a in ("--collect-submodules", m)],
    ]
    # QtWebEngine needs its process binary + resource .pak files present;
    # collect-binaries brings the binaries, add the resource/webview data explicitly.
    pyside6_pkg = Path(sys.executable).parent / "Lib" / "site-packages" / "PySide6"
    for sub in ("resources", "plugins"):
        d = pyside6_pkg / sub
        if d.is_dir():
            pyinstaller_args += ["--add-data", f"{d};PySide6/{sub}"]
    pyinstaller_args += [
        *(["--add-data", f"{src / 'vendor'};vendor"]
          if (src / "vendor").is_dir() else []),
        *common,
    ]
    pyinstaller(pyinstaller_args, cwd=src)

    # 2) setup wizard: one file, copies the sibling onedir folder
    pyinstaller([
        str(root / "build" / "setup_gui.py"),
        "--onefile", "--name", "Setup-" + APP_NAME,
        *common,
    ], cwd=root)

    main_exe = out / "dist" / APP_NAME / MAIN_EXE_NAME
    setup_exe = out / "dist" / SETUP_EXE_NAME
    for p in (main_exe, setup_exe):
        if not p.is_file():
            raise SystemExit(f"PyInstaller did not produce {p}")

    # 3) unsigned.zip: three copies, ASCII names, one signing request
    unsigned = out / "unsigned.zip"
    with zipfile.ZipFile(unsigned, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(main_exe, "main.exe")
        z.write(setup_exe, "setup.exe")
        z.write(main_exe, "portable.exe")
    print(f"BUILD OK -> {unsigned} ({unsigned.stat().st_size / 1024 / 1024:.1f} MB)", flush=True)


def find_signed_zip(out: Path) -> Path:
    candidates = sorted((out / "signed").rglob("*.zip"))
    for p in candidates:
        try:
            with zipfile.ZipFile(p) as z:
                names = set(z.namelist())
            if all(m in names for m in UNSIGNED_MEMBERS):
                return p
        except zipfile.BadZipFile:
            continue
    raise SystemExit("signed artifact not found under out/signed (expected a ZIP with main/setup/portable.exe)")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def repack(root: Path, out: Path, version: str, product: str) -> None:
    signed_zip = find_signed_zip(out)
    staged = out / "signed_extract"
    if staged.exists():
        shutil.rmtree(staged)
    staged.mkdir(parents=True)
    with zipfile.ZipFile(signed_zip) as z:
        z.extractall(staged)
    for m in UNSIGNED_MEMBERS:
        if not (staged / m).is_file():
            raise SystemExit(f"signed artifact missing {m}")

    dist_dir = out / "dist" / APP_NAME
    main_exe = dist_dir / MAIN_EXE_NAME
    setup_exe = out / "dist" / SETUP_EXE_NAME
    shutil.copyfile(staged / "main.exe", main_exe)
    shutil.copyfile(staged / "setup.exe", setup_exe)

    # portable edition: full copy of onedir, its own signed exe, marker file
    portable_dir = out / "portable" / APP_NAME
    if portable_dir.exists():
        shutil.rmtree(portable_dir)
    shutil.copytree(dist_dir, portable_dir)
    shutil.copyfile(staged / "portable.exe", portable_dir / MAIN_EXE_NAME)
    (portable_dir / "portable.marker").write_text(
        "Portable edition: no ads, reduced effects, data stored under this folder.\n",
        encoding="utf-8")

    release = out / "release"
    if release.exists():
        shutil.rmtree(release)
    release.mkdir(parents=True)
    shutil.copyfile(setup_exe, release / SETUP_EXE_NAME)
    shutil.copytree(dist_dir, release / APP_NAME)
    portable_zip = release / PORTABLE_ZIP_NAME
    with zipfile.ZipFile(portable_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(portable_dir.rglob("*")):
            if p.is_file():
                z.write(p, str(Path(APP_NAME) / p.relative_to(portable_dir)))

    sums = release / "SHA256SUMS.txt"
    lines = []
    for p in sorted(release.rglob("*")):
        if p.is_file() and p != sums:
            lines.append(f"{sha256(p)}  {p.relative_to(release).as_posix()}")
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"REPACK OK -> {release} ({len(lines)} files hashed)", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repack", action="store_true")
    ap.add_argument("--version", required=True, help="four-part version, e.g. 1.0.0.0")
    ap.add_argument("--product", default="Toolbox All-in-One")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="out")
    args = ap.parse_args()
    parse_version(args.version)
    root = Path(args.root).resolve()
    out = Path(args.out).resolve()
    (repack if args.repack else build)(root, out, args.version, args.product)
    return 0


if __name__ == "__main__":
    sys.exit(main())
