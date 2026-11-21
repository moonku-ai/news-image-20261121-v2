"""Tests for news-image-20261121 v2 — pure-stdlib poster renderer.

Written FIRST (TDD RED): main.py does not exist yet, so every test must
fail with ModuleNotFoundError / ImportError before the implementation lands.
"""
import importlib
import os
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))


def test_png_encoder_writes_valid_png():
    import main

    png = main.encode_png(4, 3, bytes([255, 0, 0] * 12))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    # IHDR: width 4, height 3, bit depth 8, color type 2 (RGB)
    assert struct.unpack(">IIBBBBB", png[16:29])[:2] == (4, 3)
    assert png[24] == 8 and png[25] == 2
    # Every chunk CRC must verify; last chunk is IEND.
    pos = 8
    types = []
    while pos < len(png):
        length = struct.unpack(">I", png[pos:pos + 4])[0]
        ctype = png[pos + 4:pos + 8]
        data = png[pos + 8:pos + 8 + length]
        crc = struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])[0]
        assert zlib.crc32(ctype + data) & 0xFFFFFFFF == crc
        types.append(ctype)
        pos += 12 + length
    assert types[-1] == b"IEND"
    assert pos == len(png)


def test_font_measures_and_renders_known_glyph():
    import main

    # 'A' is 5 columns + 1 gap = 6 advance units; scale 2 -> 12 px wide.
    assert main.text_width("A", 2) == 12
    assert main.text_width("AB", 1) == 12
    # Rendering 'H' at scale 1 must set the two vertical bars and the middle bar.
    canvas = main.Canvas(12, 7)
    canvas.draw_text(0, 0, "H", 1, main.WHITE)
    assert canvas.pixel(0, 0) == main.WHITE  # top of left bar
    assert canvas.pixel(4, 0) == main.WHITE  # top of right bar
    assert canvas.pixel(2, 0) == main.BLACK  # gap at top row
    assert canvas.pixel(2, 3) == main.WHITE  # middle bar


def test_text_wrap_never_overflows_its_box():
    import main

    lines = main.wrap_text("MYANMAR GUILTY OF GENOCIDE", 4, 200)
    for line in lines:
        assert main.text_width(line, 4) <= 200
    assert len(lines) >= 2


def test_render_is_deterministic_and_sized():
    import main

    png1 = main.render_poster()
    png2 = main.render_poster()
    assert png1 == png2, "two renders must be byte-identical"
    assert len(png1) <= 1_048_576, f"PNG {len(png1)} bytes exceeds 1 MiB"
    w, h = struct.unpack(">II", png1[16:24])
    assert (w, h) == (1024, 1024)


def test_render_covers_the_day_faithfully():
    import main

    # The layout plan must name the day and carry every main story.
    plan = main.layout_plan()
    assert "21 NOVEMBER 2026" in plan["masthead"]
    heads = " ".join(s["headline"] for s in plan["stories"])
    for key in ("GENOCIDE", "BURSTS", "KYIV", "DECLARATION", "DEADLOCK"):
        assert key in heads
    # Every story carries an honest date tag.
    for story in plan["stories"]:
        assert story["dateline"], f"missing dateline on {story['headline']}"


def test_main_writes_entry_png_with_correct_mode_and_env():
    with tempfile.TemporaryDirectory() as tmp:
        outdir = Path(tmp) / "out"
        env = dict(os.environ, MAKEFUN_OUTPUT_DIR=str(outdir))
        proc = subprocess.run(
            [sys.executable, str(REPO / "main.py")],
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 0, proc.stderr
        entry = outdir / "entry.png"
        assert entry.exists()
        assert len(entry.read_bytes()) <= 1_048_576
        assert (entry.stat().st_mode & 0o777) == 0o644
        # Second run must produce identical bytes (grader runs twice).
        first = entry.read_bytes()
        proc2 = subprocess.run(
            [sys.executable, str(REPO / "main.py")],
            env=env, capture_output=True, text=True, timeout=60,
        )
        assert proc2.returncode == 0, proc2.stderr
        assert entry.read_bytes() == first


def test_main_uses_stdlib_only():
    src = (REPO / "main.py").read_text()
    import ast

    tree = ast.parse(src)
    allowed = {
        "os", "struct", "sys", "zlib", "hashlib", "pathlib", "math",
        "argparse", "typing",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in allowed, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed, node.module
    assert "socket" not in src and "urllib" not in src and "requests" not in src
