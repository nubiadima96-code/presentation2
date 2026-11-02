#!/usr/bin/env python3
"""Restyle the Keynote .key in-file: type, colors, slide fills. Do not move media."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import warnings
import zipfile

from keynote_parser.codec import IWAFile, UnknownArchiveWarning

warnings.simplefilter("ignore", UnknownArchiveWarning)

SRC = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "презентація від першого імпланта до навчання лікарів.key",
)

# DSC cinematic tokens
NAVY = (0.055, 0.118, 0.196)  # #0e1e32
SILK = (0.910, 0.937, 0.965)  # #e8eef6
INK_LIGHT = (0.957, 0.965, 0.976)  # off-white on photos
ACCENT = (0.232, 0.427, 0.580)  # #3b6d94

KEEP_FONTS = ("iowan", "avenir", "druk", "newyork", "new york")

SKIP_STYLE_PREFIXES = (
    "stickyComment-",
    "note-0-",
    "chart-",
    "tableCellText-",
    "tableName-",
)

NOTE_PARENTS = {"4060457"}


def skip_style(obj) -> bool:
    super_ = obj.super
    sid = getattr(super_, "style_identifier", "") or ""
    name = getattr(super_, "name", "") or ""
    if any(sid.startswith(p) for p in SKIP_STYLE_PREFIXES):
        return True
    if "Примітки" in name:
        return True
    try:
        if super_.HasField("parent") and str(super_.parent.identifier) in NOTE_PARENTS:
            return True
    except Exception:
        pass
    return False


def set_rgb(color, rgb, a=1.0):
    color.model = 1  # rgb
    color.r, color.g, color.b = rgb
    color.a = a
    color.rgbspace = 1  # srgb


def near_white(color) -> bool:
    try:
        return color.r > 0.85 and color.g > 0.85 and color.b > 0.85
    except Exception:
        return False


def near_black(color) -> bool:
    try:
        return color.r < 0.12 and color.g < 0.12 and color.b < 0.12
    except Exception:
        return False


def map_font(name: str, size: float | None, italic_quote: bool) -> str:
    if not name:
        return name
    low = name.lower()
    if any(k in low for k in KEEP_FONTS):
        return name
    size = float(size or 0)
    if italic_quote or "italic" in low:
        return "IowanOldStyle-Italic"
    if "times" in low or "gillsans" in low or "calibri" in low or "helvetica" in low:
        if size >= 54 or "bold" in low or "light" in low and size >= 70:
            if "light" in low:
                return "IowanOldStyle-Roman"
            return "IowanOldStyle-Bold"
        if "bold" in low:
            return "IowanOldStyle-Bold"
        return "AvenirNext-Regular"
    return name


def restyle_paragraph(obj) -> bool:
    if skip_style(obj):
        return False
    super_ = obj.super
    sid = getattr(super_, "style_identifier", "") or ""
    name = getattr(super_, "name", "") or ""
    changed = False
    cp = obj.char_properties
    quote = "Quote" in sid or "Цитата" in name or "quote" in sid.lower()
    size = cp.font_size if cp.HasField("font_size") else None
    if cp.font_name:
        new = map_font(cp.font_name, size, quote)
        if new != cp.font_name:
            cp.font_name = new
            changed = True
    if cp.HasField("font_color") and near_white(cp.font_color):
        set_rgb(cp.font_color, INK_LIGHT)
        changed = True
    return changed


def restyle_character(obj) -> bool:
    if skip_style(obj):
        return False
    changed = False
    cp = obj.char_properties
    size = cp.font_size if cp.HasField("font_size") else None
    if cp.font_name:
        new = map_font(cp.font_name, size, False)
        if new != cp.font_name:
            cp.font_name = new
            changed = True
    if cp.HasField("font_color") and near_white(cp.font_color):
        set_rgb(cp.font_color, INK_LIGHT)
        changed = True
    return changed


def restyle_slide_style(obj) -> bool:
    props = obj.slide_properties
    if not props.HasField("fill"):
        return False
    fill = props.fill
    if fill.HasField("image"):
        return False
    if fill.HasField("gradient"):
        return False
    if fill.HasField("color"):
        c = fill.color
        if near_black(c) or (c.g > 0.2 and c.b > 0.2 and c.r < 0.35):
            set_rgb(c, NAVY)
            return True
        if near_white(c):
            set_rgb(c, SILK)
            return True
    return False


def restyle_shape_style(obj) -> bool:
    """Soften default black caption chips; leave image fills alone."""
    sp = getattr(obj, "shape_properties", None)
    if sp is None:
        return False
    fill = getattr(sp, "fill", None)
    if fill is None:
        return False
    try:
        if fill.HasField("image"):
            return False
        if fill.HasField("color") and near_black(fill.color):
            set_rgb(fill.color, NAVY, a=0.92)
            return True
    except Exception:
        return False
    return False


def restyle_iwa(raw: bytes, filename: str) -> tuple[bytes, int]:
    iwa = IWAFile.from_buffer(raw, filename)
    n = 0
    for chunk in iwa.chunks:
        for seg in chunk.archives:
            for obj in seg.objects:
                name = obj.__class__.__name__
                try:
                    if name == "ParagraphStyleArchive":
                        n += int(restyle_paragraph(obj))
                    elif name == "CharacterStyleArchive":
                        n += int(restyle_character(obj))
                    elif name == "SlideStyleArchive":
                        n += int(restyle_slide_style(obj))
                    elif name == "ShapeStyleArchive":
                        n += int(restyle_shape_style(obj))
                except Exception:
                    continue
    if n == 0:
        return raw, 0
    return iwa.to_buffer(), n


def main():
    if not os.path.isfile(SRC):
        sys.exit(f"missing {SRC}")
    print("source", SRC, "size", os.path.getsize(SRC))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".key", dir=os.path.dirname(SRC))
    os.close(tmp_fd)
    os.remove(tmp_path)

    changed_files = 0
    changed_objs = 0
    with zipfile.ZipFile(SRC, "r") as zin, zipfile.ZipFile(
        tmp_path, "w", compression=zipfile.ZIP_STORED
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename.startswith("Index/") and info.filename.endswith(".iwa"):
                try:
                    new, n = restyle_iwa(data, info.filename)
                except Exception as e:
                    print("SKIP", info.filename, e)
                    new, n = data, 0
                if n:
                    changed_files += 1
                    changed_objs += n
                    data = new
                    print(f"  {info.filename}: {n} styles")
            new_info = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
            new_info.compress_type = info.compress_type
            new_info.external_attr = info.external_attr
            new_info.flag_bits = info.flag_bits
            zout.writestr(new_info, data)

    os.replace(tmp_path, SRC)
    print("done files", changed_files, "objects", changed_objs)
    print("size now", os.path.getsize(SRC))


if __name__ == "__main__":
    main()
