# ghostty-yazi-flavor

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
uv tool install git+https://github.com/SpencerPresley/ghostty-yazi-flavor
# or: pipx install git+https://github.com/SpencerPresley/ghostty-yazi-flavor
# or just grab the single stdlib-only file:
#   curl -o ~/.local/bin/ghostty-yazi-flavor https://raw.githubusercontent.com/SpencerPresley/ghostty-yazi-flavor/main/ghostty_yazi_flavor.py && chmod +x ~/.local/bin/ghostty-yazi-flavor
```

Then point yazi at the flavor in `~/.config/yazi/theme.toml`:

```toml
[flavor]
dark = "ghostty"
light = "ghostty"
```

## Use

```bash
ghostty-yazi-flavor        # regenerate from the current theme
```

Change your Ghostty theme → run it again → restart yazi. That's the whole
loop. Options: `--out <dir>`, `--ghostty <path>`, `--version`.

## Automating "run it again"

**macOS — launchd WatchPaths** (regenerate on any write to the Ghostty
config, no polling, no dependencies). Save as
`~/Library/LaunchAgents/com.ghostty-yazi-flavor.plist`, substituting
`YOUR_USER`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>Label</key>
	<string>com.ghostty-yazi-flavor</string>
	<key>ProgramArguments</key>
	<array>
		<string>/Users/YOUR_USER/.local/bin/ghostty-yazi-flavor</string>
	</array>
	<key>WatchPaths</key>
	<array>
		<string>/Users/YOUR_USER/.config/ghostty/config</string>
	</array>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ghostty-yazi-flavor.plist
```

**Linux — systemd path unit**: a `ghostty-yazi-flavor.path` watching
`%h/.config/ghostty/config` paired with a oneshot `.service` does the same
job.

## tmux note

If yazi renders **colorless** inside tmux, the pane environment is missing
`COLORTERM`. Add to your tmux.conf:

```tmux
set -ga update-environment COLORTERM
```

**chezmoi** (if your Ghostty config is managed there, hook regeneration to
the file actually changing):

```bash
# .chezmoiscripts/run_onchange_after_sync-yazi-flavor.sh.tmpl
#!/bin/bash
set -euo pipefail
# ghostty config hash: {{ include "dot_config/ghostty/config" | sha256sum }}
"$HOME/.local/bin/ghostty-yazi-flavor"
```

## License

MIT
