# Toolbox All-in-One / 基本工具集齐·免下载工具箱

A free, open-source Windows desktop application that bundles everyday utilities
into one program, so you do not have to download a separate app for each task.

**开源免费 · 无广告 · 无付费 · 无遥测 · 数据本地保存**

## What it does

**50 built-in tools**, no separate downloads, all free and open source:

- **Life (13)**: calculator, 7-day weather, unit/base conversion, mortgage & tax
  calculators, BMI, timestamp & date calculators, timer/stopwatch, random picker,
  password generator, relative-title calculator
- **Office (16)**: document editor (txt/md/html/rtf/docx), PDF reader, AI assistant,
  word count, text diff/case/Base64/URL/JSON/regex/encoding tools, notepad, todo
  list, Markdown preview, paint board, Pomodoro timer
- **Media (9)**: music & video players, FFmpeg transcoding, image viewer/converter/
  compressor, screen color picker, color palette, screenshot
- **System (12)**: Chromium multi-tab browser, temp-file cleaner (whitelist scan,
  explicit confirmation, Recycle Bin), lightweight local file health check
  (recoverable quarantine; not a full AV engine), archive manager (zip / tar.gz /
  7z with path-traversal protection), scan & print, component status, file hash,
  batch rename, file split/merge, disk usage, system info, process manager

Written in Python 3.13 + PySide6; data is stored locally in SQLite.
**No advertisements, no paid tiers, no telemetry, and no account required.**

## Download

- Free builds: <https://github.com/liu123860/Toolbox-All-in-One/releases>
- Project website: <https://v.gd/rOEyJx> (source files in `03-官方网站/`)
- `Setup-基本工具集齐工具箱.exe` + program folder — user-level install, no admin rights
- `基本工具集齐工具箱-便携纯净版.zip` — unzip and run; delete the folder to uninstall

Each release ships a SHA-256 checksum so you can verify the download.

> **Windows SmartScreen / antivirus warning:** This is an open-source project
> built without a commercial code-signing certificate, so Windows may show a
> "Windows protected your PC" prompt on first run. Choose
> **More info → Run anyway** after verifying the checksum. The full source is
> public for review. See [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

## Build from source

Prerequisites: Python 3.13, Git.

```powershell
git clone https://github.com/liu123860/Toolbox-All-in-One.git
cd Toolbox-All-in-One
python -m pip install -r 02-程序文件/requirements.txt
python -m pip install pyinstaller
cd 02-程序文件
python main.py            # run from source
python main.py --selftest # built-in self test (30 checks)
```

Release artifacts are built by CI (`.github/workflows/release.yml`) on
GitHub-hosted Windows runners.

```powershell
python build/build_ci.py --version 1.0.0.0 --root . --out out
```

## Code signing policy

This project does **not** currently use a code-signing certificate. Release
binaries are built transparently by public CI and accompanied by SHA-256
checksums. Details — build provenance, checksum verification, and why unsigned
builds are normal for open-source software — are in
[CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md). Privacy: [PRIVACY.md](PRIVACY.md).

## Security notes

- The cleaner only scans whitelisted temporary directories and deletes to the
  Recycle Bin after explicit confirmation.
- The local file health check is a lightweight heuristic, not a full antivirus
  engine; results are clearly labelled as such.
- Archive extraction rejects path-traversal entries (Zip-Slip).
- AI assistant keys are encrypted with Windows DPAPI and stay on the device.
- Passwords are stored as salted PBKDF2 hashes, never in plain text.

## License

[MIT](LICENSE) — an OSI-approved license. No commercial dual-licensing.
Third-party components are open source and listed in the repository.

## Contributing

Issues and pull requests are welcome at
<https://github.com/liu123860/Toolbox-All-in-One>.
