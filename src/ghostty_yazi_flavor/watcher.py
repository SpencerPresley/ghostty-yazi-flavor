"""Install a file watcher so the flavor regenerates on Ghostty config changes.

macOS: launchd LaunchAgent with WatchPaths — event-driven, no polling.
Linux:  systemd user path unit (PathModified=) + a oneshot service — the
        systemd analog of WatchPaths. (supervisord/runit have no file-watching
        primitive; for those, run an inotifywait loop — see the README.)

Both watch the Ghostty config file and, if present, the custom themes dir.
"""

import os
import shutil
import subprocess
import sys

LABEL = "com.ghostty-yazi-flavor"
PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
LAUNCHD_LOG = os.path.expanduser("~/Library/Logs/ghostty-yazi-flavor.log")
SYSTEMD_DIR = os.path.expanduser("~/.config/systemd/user")
UNIT = "ghostty-yazi-flavor"

INOTIFY_HINT = (
    "no systemd found. Run a watch loop under your supervisor of choice "
    "(supervisord, runit, ...):\n"
    "  inotifywait -m -e close_write ~/.config/ghostty/config | "
    "while read -r _; do ghostty-yazi-flavor; done"
)


def _die(msg: str) -> "None":
    sys.exit(f"ghostty-yazi-flavor: {msg}")


def tool_path() -> str:
    p = shutil.which("ghostty-yazi-flavor")
    if not p:
        p = os.path.realpath(sys.argv[0])
        if not (os.access(p, os.X_OK) and os.path.basename(p).startswith("ghostty-yazi-flavor")):
            _die(
                "can't find ghostty-yazi-flavor on PATH — install the tool "
                "first (uv tool install / pipx install), then rerun."
            )
    p = os.path.realpath(p)
    # An ephemeral `uvx` run resolves into uv's cache, which gets pruned — a
    # watcher pointing there dies silently. Demand a persistent install.
    if "/.cache/uv/" in p or "/Library/Caches/uv/" in p:
        _die(
            f"refusing to point the watcher at an ephemeral uvx path ({p}).\n"
            "Install persistently first: uv tool install ghostty-yazi-flavor"
        )
    return p


def watch_paths() -> "list[str]":
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    paths = [os.path.join(xdg, "ghostty", "config")]
    themes = os.path.join(xdg, "ghostty", "themes")
    if os.path.isdir(themes):
        paths.append(themes)
    if sys.platform == "darwin":
        appsupport = os.path.expanduser(
            "~/Library/Application Support/com.mitchellh.ghostty/config"
        )
        if os.path.exists(appsupport):
            paths.append(appsupport)
    return paths


def _run(cmd: "list[str]", fatal: bool = True) -> "subprocess.CompletedProcess":
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if fatal and proc.returncode != 0:
        _die(f"`{' '.join(cmd)}` failed:\n{proc.stderr.strip() or proc.stdout.strip()}")
    return proc


# --- launchd (macOS) --------------------------------------------------------


def _launchd_plist(exe: str, paths: "list[str]") -> str:
    watch = "\n".join(f"\t\t<string>{p}</string>" for p in paths)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Label</key>
\t<string>{LABEL}</string>
\t<key>ProgramArguments</key>
\t<array>
\t\t<string>{exe}</string>
\t</array>
\t<key>WatchPaths</key>
\t<array>
{watch}
\t</array>
\t<key>StandardOutPath</key>
\t<string>{LAUNCHD_LOG}</string>
\t<key>StandardErrorPath</key>
\t<string>{LAUNCHD_LOG}</string>
</dict>
</plist>
"""


def _install_launchd(exe: str, paths: "list[str]", print_only: bool) -> None:
    plist = _launchd_plist(exe, paths)
    if print_only:
        print(f"# would write {PLIST}:\n{plist}")
        return
    os.makedirs(os.path.dirname(PLIST), exist_ok=True)
    with open(PLIST, "w") as f:
        f.write(plist)
    _run(["launchctl", "unload", PLIST], fatal=False)
    _run(["launchctl", "load", PLIST])
    print(f"install-watcher: loaded {PLIST}")
    print(f"watching: {', '.join(paths)}")
    print(f"log: {LAUNCHD_LOG}")


def _uninstall_launchd() -> None:
    if not os.path.exists(PLIST):
        print("uninstall-watcher: nothing installed.")
        return
    _run(["launchctl", "unload", PLIST], fatal=False)
    os.remove(PLIST)
    print(f"uninstall-watcher: removed {PLIST}")


def _status_launchd() -> str:
    if not os.path.exists(PLIST):
        return "not installed (run `ghostty-yazi-flavor install-watcher`)"
    loaded = _run(["launchctl", "list", LABEL], fatal=False).returncode == 0
    state = "loaded" if loaded else "INSTALLED BUT NOT LOADED"
    return f"launchd, {state} ({PLIST})"


# --- systemd (Linux) --------------------------------------------------------


def _systemd_units(exe: str, paths: "list[str]") -> "tuple[str, str]":
    modified = "\n".join(f"PathModified={p}" for p in paths)
    service = f"""[Unit]
Description=Regenerate the yazi flavor from the active Ghostty theme

[Service]
Type=oneshot
ExecStart={exe}
"""
    path_unit = f"""[Unit]
Description=Watch the Ghostty config and regenerate the yazi flavor

[Path]
{modified}

[Install]
WantedBy=default.target
"""
    return service, path_unit


def _install_systemd(exe: str, paths: "list[str]", print_only: bool) -> None:
    if not shutil.which("systemctl"):
        _die(f"install-watcher: {INOTIFY_HINT}")
    service, path_unit = _systemd_units(exe, paths)
    if print_only:
        print(f"# would write {SYSTEMD_DIR}/{UNIT}.service:\n{service}")
        print(f"# would write {SYSTEMD_DIR}/{UNIT}.path:\n{path_unit}")
        return
    os.makedirs(SYSTEMD_DIR, exist_ok=True)
    with open(os.path.join(SYSTEMD_DIR, f"{UNIT}.service"), "w") as f:
        f.write(service)
    with open(os.path.join(SYSTEMD_DIR, f"{UNIT}.path"), "w") as f:
        f.write(path_unit)
    _run(["systemctl", "--user", "daemon-reload"])
    _run(["systemctl", "--user", "enable", "--now", f"{UNIT}.path"])
    print(f"install-watcher: enabled {UNIT}.path (systemd user unit)")
    print(f"watching: {', '.join(paths)}")


def _uninstall_systemd() -> None:
    removed = False
    if shutil.which("systemctl"):
        _run(["systemctl", "--user", "disable", "--now", f"{UNIT}.path"], fatal=False)
    for suffix in (".service", ".path"):
        unit = os.path.join(SYSTEMD_DIR, UNIT + suffix)
        if os.path.exists(unit):
            os.remove(unit)
            removed = True
    if removed and shutil.which("systemctl"):
        _run(["systemctl", "--user", "daemon-reload"], fatal=False)
    print("uninstall-watcher: removed." if removed else "uninstall-watcher: nothing installed.")


def _status_systemd() -> str:
    unit = os.path.join(SYSTEMD_DIR, f"{UNIT}.path")
    if not os.path.exists(unit):
        return "not installed (run `ghostty-yazi-flavor install-watcher`)"
    if shutil.which("systemctl"):
        proc = _run(["systemctl", "--user", "is-active", f"{UNIT}.path"], fatal=False)
        return f"systemd, {proc.stdout.strip() or 'unknown'} ({unit})"
    return f"systemd units present, systemctl not found ({unit})"


# --- dispatch ---------------------------------------------------------------


def install(print_only: bool = False) -> None:
    exe = tool_path()
    paths = watch_paths()
    if sys.platform == "darwin":
        _install_launchd(exe, paths, print_only)
    elif sys.platform.startswith("linux"):
        _install_systemd(exe, paths, print_only)
    else:
        _die(f"install-watcher: unsupported platform {sys.platform!r}")


def uninstall() -> None:
    if sys.platform == "darwin":
        _uninstall_launchd()
    elif sys.platform.startswith("linux"):
        _uninstall_systemd()
    else:
        _die(f"uninstall-watcher: unsupported platform {sys.platform!r}")


def status() -> str:
    if sys.platform == "darwin":
        return _status_launchd()
    if sys.platform.startswith("linux"):
        return _status_systemd()
    return f"unsupported platform {sys.platform!r}"
