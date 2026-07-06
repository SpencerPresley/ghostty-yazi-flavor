# ghostty-yazi-flavor

[![PyPI](https://img.shields.io/pypi/v/ghostty-yazi-flavor)](https://pypi.org/project/ghostty-yazi-flavor/)

Generate a [yazi](https://yazi-rs.github.io/) flavor from your active
[Ghostty](https://ghostty.org/) theme — so yazi's hover bars, mode pills, and
code-preview syntax highlighting actually match your terminal instead of
fighting it.

<!-- TODO: before/after screenshots -->

## Why

Yazi's default theme follows your terminal's 16-color ANSI palette, which gets
you most of the way — but two things don't follow it:

1. **Code-preview highlighting** uses syntect's built-in default theme, which
   ignores your palette entirely. On most themes that means a wall of
   mismatched color over the wrong background.
2. **Hover indicators** use reverse-video: the hovered row becomes a solid
   block of its own text color. If your theme keeps something loud in its blue
   slot, every hover is a neon bar.

Hand-made flavors fix this for popular themes (catppuccin, dracula, …). For
the other ~450 themes Ghostty ships with — or your own custom one — this tool
generates the flavor from whatever theme is actually active.

## How it works

It runs `ghostty +show-config`, which prints the **resolved** config with the
active theme's palette already applied (built-in themes, custom themes in
`~/.config/ghostty/themes`, includes — all handled by Ghostty itself). From
those 16 colors + background/foreground/selection it writes:

```
~/.config/yazi/flavors/ghostty.yazi/
├── flavor.toml    # hover bars, mode pills, tabs, borders — palette-derived
└── tmtheme.xml    # code-preview highlighting built from your actual colors
```

The flavor is deliberately **partial**: everything yazi's preset already gets
right by following ANSI colors is left alone; only the spots that ignore the
palette (or follow it badly) are overridden.

## Install

```bash
uv tool install ghostty-yazi-flavor
# or: pipx install ghostty-yazi-flavor
```

Then point yazi at the flavor in `~/.config/yazi/theme.toml`:

```toml
[flavor]
dark = "ghostty"
light = "ghostty"
```

## Use

```bash
ghostty-yazi-flavor                    # regenerate from the current theme
```

Change your Ghostty theme → run it again → restart yazi. Options:
`--out <dir>`, `--ghostty <path>`, `--version`.

## Automatic regeneration

```bash
ghostty-yazi-flavor install-watcher    # set it and forget it
```

Installs a file watcher on your Ghostty config (and custom themes directory,
if you have one), so the flavor regenerates on every config write — including
saves that you follow with Ghostty's reload-config keybinding:

- **macOS**: a launchd LaunchAgent using `WatchPaths` — event-driven, no
  polling, no dependencies. Logs to `~/Library/Logs/ghostty-yazi-flavor.log`.
- **Linux**: systemd user units (a `.path` watching the config + a oneshot
  `.service`).

`--print` shows exactly what would be installed without touching anything;
`ghostty-yazi-flavor uninstall-watcher` removes it cleanly.

**Non-systemd Linux**: run a watch loop under your supervisor of choice
(supervisord, runit, …):

```bash
inotifywait -m -e close_write ~/.config/ghostty/config | while read -r _; do
  ghostty-yazi-flavor
done
```

**chezmoi**: if your Ghostty config is managed there, skip the watcher and
hook regeneration to the source of truth instead:

```bash
# .chezmoiscripts/run_onchange_after_sync-yazi-flavor.sh.tmpl
#!/bin/bash
set -euo pipefail
# ghostty config hash: {{ include "dot_config/ghostty/config" | sha256sum }}
"$HOME/.local/bin/ghostty-yazi-flavor"
```

## tmux note

If yazi renders **colorless** inside tmux, the pane environment is missing
`COLORTERM`. Add to your tmux.conf:

```tmux
set -ga update-environment COLORTERM
```

## License

MIT
