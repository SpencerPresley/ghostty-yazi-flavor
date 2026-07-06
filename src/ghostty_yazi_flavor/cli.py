"""Command-line interface."""

import argparse

from . import __version__, generator, watcher


def main():
    ap = argparse.ArgumentParser(
        prog="ghostty-yazi-flavor",
        description="Generate a yazi flavor from the active Ghostty theme.",
    )
    ap.add_argument(
        "command",
        nargs="?",
        default="generate",
        choices=["generate", "install-watcher", "uninstall-watcher"],
        help="generate (default): write the flavor; install-watcher: regenerate "
        "automatically whenever the Ghostty config changes (launchd on macOS, "
        "systemd user units on Linux); uninstall-watcher: remove it",
    )
    ap.add_argument(
        "--out",
        default=generator.DEFAULT_OUT,
        help=f"output flavor directory (default: {generator.DEFAULT_OUT})",
    )
    ap.add_argument(
        "--ghostty", default=None, help="path to the ghostty binary (default: autodetect)"
    )
    ap.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="with install-watcher: print the units instead of installing them",
    )
    ap.add_argument("--version", action="version", version=__version__)
    args = ap.parse_args()

    if args.command == "generate":
        generator.generate(out=args.out, ghostty=args.ghostty)
    elif args.command == "install-watcher":
        watcher.install(print_only=args.print_only)
    elif args.command == "uninstall-watcher":
        watcher.uninstall()


if __name__ == "__main__":
    main()
