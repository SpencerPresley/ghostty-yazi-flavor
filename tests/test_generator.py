import sys
import xml.etree.ElementTree as ET

import pytest

from ghostty_yazi_flavor import generator

SHOW_CONFIG = "\n".join(
    [f"palette = {i}=#{i:02x}{i:02x}{i:02x}" for i in range(16)]
    + [
        "background = #191323",
        "foreground = cccccc",
        "cursor-color = #e07d13",
        "selection-background = #220525",
        "theme = Banana Blueberry",
        "font-family = Hack Nerd Font",
        "not a config line",
    ]
).splitlines()


def test_norm_hex():
    assert generator.norm_hex("#AABBCC") == "#aabbcc"
    assert generator.norm_hex("aabbcc") == "#aabbcc"
    assert generator.norm_hex("") is None
    assert generator.norm_hex("red") is None
    assert generator.norm_hex("#aabbccdd") is None


def test_parse():
    palette, scalars = generator.parse(SHOW_CONFIG)
    assert sorted(palette) == list(range(16))
    assert palette[15] == "#0f0f0f"
    assert scalars["theme"] == "Banana Blueberry"
    assert scalars["foreground"] == "cccccc"  # normalized later, kept raw here
    assert "font-family" not in scalars


def test_render_flavor_is_valid_toml_with_palette_hexes():
    palette, _ = generator.parse(SHOW_CONFIG)
    out = generator.render_flavor("Test", palette, "#191323", "#cccccc")
    assert '{ bg = "#080808", bold = true }' in out  # indicator = palette 8
    assert 'from Ghostty theme "Test"' in out
    tomllib = pytest.importorskip("tomllib")
    parsed = tomllib.loads(out)
    assert parsed["indicator"]["current"]["bg"] == "#080808"
    assert parsed["mode"]["normal_main"]["bg"] == "#040404"  # palette 4


def test_render_tmtheme_is_valid_xml():
    palette, _ = generator.parse(SHOW_CONFIG)
    out = generator.render_tmtheme(
        "Test", palette, "#191323", "#cccccc", "#e07d13", "#220525"
    )
    root = ET.fromstring(out)
    assert root.tag == "plist"
    strings = [e.text for e in root.iter("string")]
    assert "#191323" in strings  # background
    assert "Ghostty Test" in strings


def test_generate_writes_both_files(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "find_ghostty", lambda explicit=None: "ghostty")
    monkeypatch.setattr(generator, "resolved_config", lambda g: SHOW_CONFIG)
    generator.generate(out=str(tmp_path / "x.yazi"))
    assert (tmp_path / "x.yazi" / "flavor.toml").exists()
    assert (tmp_path / "x.yazi" / "tmtheme.xml").exists()


def test_generate_exits_on_missing_palette(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "find_ghostty", lambda explicit=None: "ghostty")
    monkeypatch.setattr(generator, "resolved_config", lambda g: SHOW_CONFIG[2:])
    with pytest.raises(SystemExit):
        generator.generate(out=str(tmp_path / "x.yazi"))
