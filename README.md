# Toolbox All-in-One / 基本工具集齐·免下载工具箱

A free, open-source Windows desktop application that bundles everyday utilities
into one program, so you do not have to download a separate app for each task.

> **Replace every `<...>` placeholder in this README before publishing the repository.**

## What it does

- Calculator, 7-day weather forecast, document editor (txt/md/html/rtf/docx), PDF reader
- Music / video player, Chromium-based multi-tab browser
- Archive manager (zip / tar.gz / 7z, with path-traversal protection)
- Temporary-file cleaner (whitelist scan, explicit confirmation, Recycle Bin)
- Malware heuristic scanner (quarantine is recoverable; not a full AV engine)
- Scan & print helper, optional AI assistant, component status overview

Written in Python 3.13 + PySide6; data is stored locally in SQLite.
**No advertisements, no paid tiers, no telemetry, and no account required.**

## Download

Free downloads: <https://github.com/<your-account>/<repo>/releases> and the
project download page <https://<your-account>.github.io/<repo>/download.html>.

- `Setup-Toolbox-All-in-One.exe` + program folder — user-level install, no admin rights
- `Toolbox-All-in-One-portable.zip` — unzip and run; delete the folder to uninstall

Windows may show a SmartScreen prompt for unsigned builds. After the
SignPath Foundation application is approved, released binaries are signed;
see **Code signing policy** below.

## Build from source

Prerequisites: Python 3.13, Git.

```powershell
git clone https://github.com/<your-account>/<repo>.git
cd <repo>
python -m pip install -r 02-程序文件/requirements.txt
python -m pip install pyinstaller
cd 02-程序文件
python main.py            # run from source
python main.py --selftest # built-in self test
```

Release artifacts are built only by CI (`.github/workflows/release.yml`) on
GitHub-hosted Windows runners. Nothing built on a developer machine is signed.

```powershell
python build/build_ci.py --version 1.0.0.0 --root . --out out
```

## Code signing policy

Free code signing provided by [SignPath.io](https://about.signpath.io),
certificate by [SignPath Foundation](https://signpath.org).

Status: **Pending approval**. Details — what is signed, CI origin verification,
team roles, privacy statement, and signature verification — are in
[CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md). See also
[PRIVACY.md](PRIVACY.md).

## Security notes

- The cleaner only scans whitelisted temporary directories and deletes to the
  Recycle Bin after explicit confirmation.
- The scanner is a lightweight heuristic, not a full antivirus engine; results
  are clearly labelled as such.
- Archive extraction rejects path-traversal entries (Zip-Slip).
- AI assistant keys are encrypted with Windows DPAPI and stay on the device.
- Passwords are stored as salted PBKDF2 hashes, never in plain text.

## License

[MIT](LICENSE) — an OSI-approved license. No commercial dual-licensing.
Third-party components are open source and listed in the repository.
