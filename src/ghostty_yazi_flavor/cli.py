"""Command-line interface."""

import argparse
import os
import re
import sys

from . import __version__, generator, watcher

EXAMPLES = """\
examples:
  ghostty-yazi-flavor                          regenerate the flavor
  ghostty-yazi-flavor generate --out ./x.yazi  write it somewhere else
  ghostty-yazi-flavor install-watcher          regenerate automatically on
                                               Ghostty config changes
  ghostty-yazi-flavor status                   what's installed, what theme
"""


def _flavor_theme(out_dir: str):
    """Theme name recorded in a generated flavor.toml, or None."""
    path = os.path.join(os.path.expanduser(out_dir), "flavor.toml")
    try:
        with open(path) as f:
            head = f.read(512)
    except OSError:
        return None
    m = re.search(r'from Ghostty theme "(.*)"', head)
    return m.group(1) if m else None


def _status(out_dir: str) -> None:
    flavor_dir = os.path.expanduser(out_dir)
    flavor_file = os.path.join(flavor_dir, "flavor.toml")
    if os.path.exists(flavor_file):
        import datetime

        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(flavor_file))
        theme = _flavor_theme(out_dir) or "(unknown)"
        print(f"flavor:  {flavor_dir}")
        print(f'         theme "{theme}", generated {mtime:%Y-%m-%d %H:%M:%S}')
    else:
        print(f"flavor:  not generated yet ({flavor_dir})")
        print("         run `ghostty-yazi-flavor` to create it")
    print(f"watcher: {watcher.status()}")


def main() -> None:
    ap = argparse.ArgumentParser(
        prog="ghostty-yazi-flavor",
        description="Generate a yazi flavor from the active Ghostty theme.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("-V", "--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="command", metavar="command")

    gen = sub.add_parser(
        "generate",
        help="write the flavor from the active Ghostty theme (the default)",
        description="Write flavor.toml + tmtheme.xml from the resolved Ghostty config.",
    )
    gen.add_argument(
        "--out",
        default=generator.DEFAULT_OUT,
        help=f"output flavor directory (default: {generator.DEFAULT_OUT})",
    )
    gen.add_argument(
        "--ghostty",
        default=None,
        help="path to the ghostty binary (default: autodetect)",
    )

    ins = sub.add_parser(
        "install-watcher",
        help="regenerate automatically whenever the Ghostty config changes",
        description="Install a file watcher on the Ghostty config: a launchd "
        "LaunchAgent (WatchPaths) on macOS, systemd user units (.path + "
        "oneshot .service) on Linux.",
    )
    ins.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="print the units instead of installing them",
    )

    sub.add_parser("uninstall-watcher", help="remove the watcher")
    sub.add_parser("status", help="show flavor and watcher state")

    args = ap.parse_args()
    command = args.command or "generate"

    if command == "generate":
        out = getattr(args, "out", generator.DEFAULT_OUT)
        ghostty = getattr(args, "ghostty", None)
        generator.generate(out=out, ghostty=ghostty)
    elif command == "install-watcher":
        watcher.install(print_only=args.print_only)
    elif command == "uninstall-watcher":
        watcher.uninstall()
    elif command == "status":
        _status(generator.DEFAULT_OUT)


if __name__ == "__main__":
    main()
