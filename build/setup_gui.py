#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-level install / uninstall wizard (open-source edition).

SignPath Foundation conditions implemented here:
  * privacy policy is displayed before installation
  * an option disables all networked features
  * system changes are announced (user-level directory only)
  * an uninstaller is provided, and refuses to touch directories it did not create

The installer copies the sibling onedir folder <app_dir>/Toolbox-All-in-One
into a user-chosen directory. No admin rights, no machine-wide registry writes,
no services, no drivers.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

APP_NAME = "Toolbox-All-in-One"
MARKER = ".installed-by-setup"
FORBIDDEN = ("c:\\windows", "c:\\program files", "c:\\program files (x86)", "c:\\users\\default")

PRIVACY_SHORT = (
    "隐私政策摘要 / Privacy\n\n"
    "本程序无广告、无付费、无遥测。账号与设置数据保存在本机 SQLite；\n"
    "密码仅存加盐哈希。仅在用户主动使用天气或自行配置的 AI 助手时联网。\n"
    "安装仅写入当前用户可选择目录，不修改系统级配置。\n"
    "完整政策见安装目录下的 PRIVACY.md 与仓库 PRIVACY.md。\n\n"
    "No ads, no paid tiers, no telemetry. Data stays on this device.\n"
    "Network access only when you invoke weather or a self-configured AI endpoint."
)


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def payload_dir() -> Path:
    return app_dir() / APP_NAME


def _guard(target: Path) -> None:
    low = str(target).lower()
    if any(low.startswith(p) for p in FORBIDDEN):
        raise RuntimeError(f"refusing to operate on a system directory: {target}")
    if target == Path(target.anchor):
        raise RuntimeError("refusing to operate on a drive root")


def install(target: Path, disable_network: bool = False, privacy_copy: Path | None = None) -> Path:
    payload = payload_dir()
    if not payload.is_dir():
        raise RuntimeError(f"program folder not found next to the setup executable: {payload}")
    target = target.resolve()
    _guard(target)
    dest = target / APP_NAME
    if dest.exists():
        raise RuntimeError(f"target already exists: {dest}")
    if dest == payload or payload in dest.parents:
        raise RuntimeError("refusing to copy the program into itself")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(payload, dest)
    (dest / MARKER).write_text("created by setup_gui.py\n", encoding="utf-8")
    if disable_network:
        (dest / "network.disabled").write_text("all networked features disabled at install time\n", encoding="utf-8")
    if privacy_copy and privacy_copy.is_file():
        shutil.copyfile(privacy_copy, dest / "PRIVACY.md")
    if not (dest / "PRIVACY.md").exists():
        (dest / "PRIVACY.md").write_text(
            PRIVACY_SHORT + "\n\nFull policy: " +
            "https://github.com/<your-account>/<repo>/blob/main/PRIVACY.md\n",
            encoding="utf-8")
    if getattr(sys, "frozen", False):
        runner = f'"{app_dir() / ("Setup-" + APP_NAME + ".exe")}"'
    else:
        runner = f'"{sys.executable}" "{Path(__file__).resolve()}"'
    uninst = dest / "卸载.bat"
    uninst.write_text(
        '@echo off\r\n'
        f'{runner} --uninstall --target="{target}"\r\n'
        'pause\r\n', encoding="utf-8")
    return dest


def uninstall(target: Path) -> None:
    target = target.resolve()
    _guard(target)
    dest = target / APP_NAME
    if not dest.is_dir():
        raise RuntimeError(f"nothing to uninstall at {dest}")
    if not (dest / MARKER).is_file():
        raise RuntimeError("refusing to delete: this directory was not created by this installer")
    shutil.rmtree(dest)
    # keep the parent directory (user may keep their own data there)


def run_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    win = tk.Tk()
    win.title(APP_NAME + " — 安装 / Install")
    win.geometry("620x520")
    frm = ttk.Frame(win, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="基本工具集齐工具箱 · 开源版", font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(frm, text="安装仅写入您选择的目录，不需要管理员权限；不修改系统级配置。",
              wraplength=580).pack(anchor="w", pady=(4, 10))

    box = tk.Text(frm, height=12, wrap="word")
    box.insert("1.0", PRIVACY_SHORT)
    box.configure(state="disabled")
    box.pack(fill="both", expand=True)

    net = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm, text="关闭所有联网功能（天气、AI 助手） / Disable networked features",
                    variable=net).pack(anchor="w", pady=8)

    path_var = tk.StringVar(value=str(Path.home() / "AppData" / "Local" / APP_NAME))

    def choose() -> None:
        p = filedialog.askdirectory()
        if p:
            path_var.set(p)

    row = ttk.Frame(frm)
    row.pack(fill="x")
    ttk.Entry(row, textvariable=path_var).pack(side="left", fill="x", expand=True)
    ttk.Button(row, text="浏览…", command=choose).pack(side="left", padx=6)

    def do_install() -> None:
        try:
            dest = install(Path(path_var.get()), disable_network=net.get(),
                           privacy_copy=app_dir() / "PRIVACY.md")
            messagebox.showinfo("完成", f"已安装到：\n{dest}\n\n卸载：运行该目录下的 卸载.bat")
            win.destroy()
        except Exception as e:
            messagebox.showerror("安装失败", str(e))

    ttk.Button(frm, text="安装 / Install", command=do_install).pack(pady=12)
    win.mainloop()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--silent", action="store_true", help="install without GUI")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--target", type=Path)
    ap.add_argument("--disable-network", action="store_true")
    args = ap.parse_args()
    if args.silent or args.uninstall:
        if not args.target:
            ap.error("--target is required with --silent / --uninstall")
        try:
            if args.uninstall:
                uninstall(args.target)
                print("UNINSTALL OK")
            else:
                print("INSTALL OK ->", install(args.target, args.disable_network,
                                              app_dir() / "PRIVACY.md"))
        except Exception as e:
            print("ERROR:", e, file=sys.stderr)
            return 1
        return 0
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
