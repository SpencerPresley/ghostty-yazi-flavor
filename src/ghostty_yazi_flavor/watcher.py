"""Install a file watcher so the flavor regenerates on Ghostty config changes.

macOS: launchd LaunchAgent with WatchPaths — fires on any write, no polling.
Linux: systemd user path unit (PathModified) — the systemd analog.

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


def tool_path():
    p = shutil.which("ghostty-yazi-flavor")
    if not p:
        p = os.path.realpath(sys.argv[0])
        if not (os.access(p, os.X_OK) and os.path.basename(p).startswith("ghostty-yazi-flavor")):
            sys.exit(
                "install-watcher: can't find ghostty-yazi-flavor on PATH — install "
                "the tool first (uv tool install / pipx install), then rerun."
            )
    p = os.path.realpath(p)
    # An ephemeral `uvx` run resolves into uv's cache, which gets pruned — a
    # watcher pointing there dies silently. Demand a persistent install.
    if "/.cache/uv/" in p or "/Library/Caches/uv/" in p:
        sys.exit(
            f"install-watcher: refusing to point the watcher at an ephemeral uvx "
            f"path ({p}).\nInstall persistently first: uv tool install ghostty-yazi-flavor"
        )
    return p


def watch_paths():
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


def _launchd_plist(exe, paths):
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


def _systemd_units(exe, paths):
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


def install(print_only=False):
    exe = tool_path()
    paths = watch_paths()

    if sys.platform == "darwin":
        plist = _launchd_plist(exe, paths)
        if print_only:
            print(f"# would write {PLIST}:\n{plist}")
            return
        os.makedirs(os.path.dirname(PLIST), exist_ok=True)
        with open(PLIST, "w") as f:
            f.write(plist)
        subprocess.run(["launchctl", "unload", PLIST], capture_output=True)
        subprocess.run(["launchctl", "load", PLIST], check=True)
        print(f"install-watcher: loaded {PLIST}")
        print(f"watching: {', '.join(paths)}")
        print(f"log: {LAUNCHD_LOG}")
    elif sys.platform.startswith("linux"):
        if not shutil.which("systemctl"):
            sys.exit(
                "install-watcher: no systemd found. Run something like\n"
                "  inotifywait -m -e close_write ~/.config/ghostty/config | "
                "while read -r _; do ghostty-yazi-flavor; done\n"
                "under your supervisor of choice (supervisord, runit, ...)."
            )
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
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", f"{UNIT}.path"], check=True
        )
        print(f"install-watcher: enabled {UNIT}.path (systemd user unit)")
        print(f"watching: {', '.join(paths)}")
    else:
        sys.exit(f"install-watcher: unsupported platform {sys.platform!r}")


def uninstall():
    if sys.platform == "darwin":
        if not os.path.exists(PLIST):
            print("uninstall-watcher: nothing installed.")
            return
        subprocess.run(["launchctl", "unload", PLIST], capture_output=True)
        os.remove(PLIST)
        print(f"uninstall-watcher: removed {PLIST}")
    elif sys.platform.startswith("linux"):
        removed = False
        if shutil.which("systemctl"):
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", f"{UNIT}.path"],
                capture_output=True,
            )
        for suffix in (".service", ".path"):
            unit = os.path.join(SYSTEMD_DIR, UNIT + suffix)
            if os.path.exists(unit):
                os.remove(unit)
                removed = True
        if removed and shutil.which("systemctl"):
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        print("uninstall-watcher: removed." if removed else "uninstall-watcher: nothing installed.")
    else:
        sys.exit(f"uninstall-watcher: unsupported platform {sys.platform!r}")
