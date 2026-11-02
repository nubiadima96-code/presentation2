#!/usr/bin/env python3
"""Polish the Keynote package in-place: gym photo, type, photo grid. Directory .key only."""

from __future__ import annotations

import hashlib
import io
import os
import warnings

import pymupdf
from PIL import Image
from keynote_parser.codec import IWAFile, UnknownArchiveWarning

warnings.simplefilter("ignore", UnknownArchiveWarning)

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = os.path.join(ROOT, "презентація від першого імпланта до навчання лікарів.key")
PDF = os.path.join(ROOT, "презентація_від_першого_імпланта_до_навчання_лікарів.pdf")

SW, SH = 1920.0, 1080.0
MX, MY = 72.0, 48.0
GAP = 28.0
NAVY = (0.055, 0.118, 0.196)
INK = (0.965, 0.973, 0.984)
ACCENT = (0.78, 0.86, 0.94)

SKIP_STYLE_PREFIXES = ("stickyComment-", "note-0-", "chart-", "tableCellText-", "tableName-")


def set_rgb(color, rgb, a=1.0):
    color.model = 1
    color.r, color.g, color.b = rgb
    color.a = a
    color.rgbspace = 1


def skip_style(obj) -> bool:
    try:
        super_ = obj.super
    except Exception:
        return False
    sid = getattr(super_, "style_identifier", "") or ""
    name = getattr(super_, "name", "") or ""
    if any(sid.startswith(p) for p in SKIP_STYLE_PREFIXES):
        return True
    if "Примітки" in name:
        return True
    return False


def map_font(name: str, size: float | None) -> str:
    if not name:
        return name
    low = name.lower()
    if "druk" in low:
        return name
    size = float(size or 0)
    italic = "italic" in low or "oblique" in low
    if italic:
        return "IowanOldStyle-Italic"
    if size >= 40 or "title" in low or "headline" in low or "bold" in low:
        return "IowanOldStyle-Bold"
    if "iowan" in low or "avenir" in low or "newyork" in low or "new york" in low:
        if size >= 40:
            return "IowanOldStyle-Bold"
        return name if "avenir" in low else "AvenirNext-Medium"
    return "AvenirNext-Medium" if size < 40 else "IowanOldStyle-Bold"


def restyle_char_props(cp) -> bool:
    changed = False
    size = cp.font_size if cp.HasField("font_size") else None
    if cp.font_name:
        new = map_font(cp.font_name, size)
        if new != cp.font_name:
            cp.font_name = new
            changed = True
        size2 = float(size or 0)
        if size2 >= 70:
            cp.font_size = 56.0
            changed = True
        elif size2 >= 48:
            cp.font_size = 52.0
            changed = True
        elif 20 <= size2 < 28:
            cp.font_size = 28.0
            changed = True
    try:
        if cp.HasField("font_color"):
            c = cp.font_color
            if c.r > 0.82 and c.g > 0.82 and c.b > 0.82:
                set_rgb(c, INK)
                changed = True
            elif c.r < 0.2 and c.g < 0.2 and c.b < 0.2:
                set_rgb(c, INK)
                changed = True
    except Exception:
        pass
    return changed


def restyle_obj(obj) -> bool:
    name = obj.__class__.__name__
    if name not in ("ParagraphStyleArchive", "CharacterStyleArchive"):
        return False
    if skip_style(obj):
        return False
    try:
        cp = obj.char_properties
        sid = ""
        try:
            sid = (obj.super.style_identifier or "") + " " + (obj.super.name or "")
        except Exception:
            pass
        if not cp.font_name and ("title" in sid.lower() or "заголов" in sid.lower()):
            cp.font_name = "IowanOldStyle-Bold"
            if not cp.HasField("font_size"):
                cp.font_size = 52.0
            if not cp.HasField("font_color"):
                set_rgb(cp.font_color, INK)
        return restyle_char_props(cp)
    except Exception:
        return False


def walk_geometry(obj):
    cur = obj
    for _ in range(6):
        if hasattr(cur, "geometry") and cur.HasField("geometry"):
            return cur.geometry
        if hasattr(cur, "super") and cur.HasField("super"):
            cur = cur.super
            continue
        break
    return None


def set_rect(geom, x, y, w, h):
    geom.position.x = float(x)
    geom.position.y = float(y)
    geom.size.width = float(w)
    geom.size.height = float(h)
    if hasattr(geom, "angle"):
        geom.angle = 0.0
    if hasattr(geom, "flags"):
        geom.flags = 3


def set_path_rect(obj, w, h):
    cur = obj
    pathsource = None
    for _ in range(6):
        if hasattr(cur, "pathsource") and cur.HasField("pathsource"):
            pathsource = cur.pathsource
            break
        if hasattr(cur, "super") and cur.HasField("super"):
            cur = cur.super
        else:
            break
    if pathsource is None:
        return
    try:
        bps = pathsource.bezier_path_source
        bps.naturalSize.width = float(w)
        bps.naturalSize.height = float(h)
        path = bps.path
        pts = [
            (0.0, 0.0),
            (float(w), 0.0),
            (float(w), float(h)),
            (0.0, float(h)),
        ]
        ei = 0
        for el in path.elements:
            t = el.type
            # 1=moveTo, 2=lineTo typically; we just rewrite any with points
            if el.points:
                el.points[0].x = pts[min(ei, 3)][0]
                el.points[0].y = pts[min(ei, 3)][1]
                ei += 1
    except Exception:
        return


def load_iwa(path):
    return IWAFile.from_buffer(open(path, "rb").read(), path)


def save_iwa(path, iwa):
    open(path, "wb").write(iwa.to_buffer())


def replace_gym_photo():
    pdf = pymupdf.open(PDF)
    page = pdf[15]  # page 16
    blob = None
    w = h = 960, 1280
    for im in page.get_images(full=True):
        xref, iw, ih = im[0], im[2], im[3]
        if iw == 960 and ih == 1280:
            info = pdf.extract_image(xref)
            blob = info["image"]
            w, h = iw, ih
            break
    if not blob:
        raise SystemExit("gym jpeg missing from PDF")
    data_dir = os.path.join(KEY, "Data")
    target = None
    thumb = None
    for fn in os.listdir(data_dir):
        if fn.endswith("-12375.jpeg") or fn.endswith("-12375.jpg"):
            target = os.path.join(data_dir, fn)
        if "-12376." in fn:
            thumb = os.path.join(data_dir, fn)
    if not target:
        raise SystemExit("12375 data file missing")
    open(target, "wb").write(blob)
    im = Image.open(io.BytesIO(blob)).convert("RGB")
    im.thumbnail((256, 256), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=78)
    tblob = out.getvalue()
    if thumb:
        open(thumb, "wb").write(tblob)
    # metadata digests
    meta_path = os.path.join(KEY, "Index/Metadata.iwa")
    iwa = load_iwa(meta_path)
    for chunk in iwa.chunks:
        for seg in chunk.archives:
            for obj in seg.objects:
                if obj.__class__.__name__ != "PackageMetadata":
                    continue
                for d in obj.datas:
                    ident = str(d.identifier)
                    if ident == "12375":
                        d.digest = hashlib.sha1(blob).digest()
                        d.materialized_length = len(blob)
                    if ident == "12376" and thumb:
                        d.digest = hashlib.sha1(tblob).digest()
                        d.materialized_length = len(tblob)
    save_iwa(meta_path, iwa)
    print("replaced gym photo 12375", len(blob), "bytes")


def layout_gym_slide():
    path = os.path.join(KEY, "Index/Slide-4083940.iwa")
    iwa = load_iwa(path)
    title_left = (MX, 40.0, 860.0, 100.0)
    title_right = (960.0, 40.0, 888.0, 100.0)
    # photos under titles, contain in remaining canvas
    # left portrait 1206x2622, right 960x1280
    area_y, area_h = 155.0, 880.0
    left_nat, right_nat = (1206.0, 2622.0), (960.0, 1280.0)
    # two columns
    col_w = (SW - 2 * MX - GAP) / 2.0
    def contain(nw, nh, bw, bh):
        s = min(bw / nw, bh / nh)
        return nw * s, nh * s

    lw, lh = contain(*left_nat, col_w, area_h)
    rw, rh = contain(*right_nat, col_w, area_h)
    lx = MX + (col_w - lw) / 2
    rx = MX + col_w + GAP + (col_w - rw) / 2
    ly = area_y + (area_h - lh) / 2
    ry = area_y + (area_h - rh) / 2

    for chunk in iwa.chunks:
        for seg in chunk.archives:
            hid = str(getattr(seg.header, "identifier", ""))
            for obj in seg.objects:
                n = obj.__class__.__name__
                if n == "PlaceholderArchive" and hid == "4083944":
                    g = walk_geometry(obj)
                    set_rect(g, *title_left)
                    set_path_rect(obj, title_left[2], title_left[3])
                if n == "ShapeInfoArchive" and hid == "4281529":
                    g = walk_geometry(obj)
                    set_rect(g, *title_right)
                    set_path_rect(obj, title_right[2], title_right[3])
                if n == "ImageArchive":
                    ident = str(obj.data.identifier)
                    g = walk_geometry(obj)
                    if ident == "10270":
                        set_rect(g, lx, ly, lw, lh)
                        obj.originalSize.width = lw
                        obj.originalSize.height = lh
                    elif ident == "12375":
                        set_rect(g, rx, ry, rw, rh)
                        obj.originalSize.width = rw
                        obj.originalSize.height = rh
                        obj.naturalSize.width = 960.0
                        obj.naturalSize.height = 1280.0
                if n == "MaskArchive":
                    parent = str(obj.super.parent.identifier) if obj.super.HasField("parent") else ""
                    g = walk_geometry(obj)
                    if parent == "4165916":
                        set_rect(g, 0, 0, lw, lh)
                        set_path_rect(obj, lw, lh)
                    elif parent == "4283242":
                        set_rect(g, 0, 0, rw, rh)
                        set_path_rect(obj, rw, rh)
    save_iwa(path, iwa)
    print("laid out gym slide")


def layout_slide_iwa(iwa) -> int:
    """Contain-fit images under titles; skip movies and full-bleed heroes."""
    images = []
    masks = []
    titles = []
    movies = []
    for chunk in iwa.chunks:
        for seg in chunk.archives:
            hid = str(getattr(seg.header, "identifier", ""))
            for obj in seg.objects:
                n = obj.__class__.__name__
                if n == "MovieArchive":
                    movies.append(obj)
                elif n == "ImageArchive":
                    images.append((hid, obj))
                elif n == "MaskArchive":
                    masks.append(obj)
                elif n == "PlaceholderArchive":
                    kind = getattr(obj, "kind", "")
                    if "Title" in str(kind):
                        titles.append(obj)
                elif n == "ShapeInfoArchive":
                    try:
                        if obj.is_text_box:
                            titles.append(obj)
                    except Exception:
                        pass
    if movies or not images or len(images) > 3:
        return 0
    # skip full-bleed
    full = 0
    for _, obj in images:
        g = walk_geometry(obj)
        if g and g.size.width > 1700 and g.size.height > 900:
            full += 1
    if full == len(images):
        return 0

    title_h = 0.0
    real_titles = []
    for t in titles:
        g = walk_geometry(t)
        if g is None:
            continue
        if g.size.width < 40 or g.size.height < 20:
            continue
        real_titles.append((t, g))
    if real_titles:
        title_h = 108.0
        if len(real_titles) == 1:
            t, g = real_titles[0]
            set_rect(g, MX, MY, SW - 2 * MX, title_h)
            set_path_rect(t, SW - 2 * MX, title_h)
        else:
            n = min(len(real_titles), 3)
            tw = (SW - 2 * MX - GAP * (n - 1)) / n
            for i, (t, g) in enumerate(real_titles[:n]):
                x = MX + i * (tw + GAP)
                set_rect(g, x, MY, tw, title_h)
                set_path_rect(t, tw, title_h)

    area_y = MY + (title_h + 18 if title_h else 0)
    area_h = SH - area_y - MY
    area_w = SW - 2 * MX
    n = len(images)
    col_w = (area_w - GAP * (n - 1)) / n if n else area_w
    changed = 0
    for i, (hid, obj) in enumerate(images):
        g = walk_geometry(obj)
        nw = obj.naturalSize.width if obj.HasField("naturalSize") else g.size.width
        nh = obj.naturalSize.height if obj.HasField("naturalSize") else g.size.height
        nw, nh = float(nw or 1), float(nh or 1)
        s = min(col_w / nw, area_h / nh)
        w, h = nw * s, nh * s
        x = MX + i * (col_w + GAP) + (col_w - w) / 2
        y = area_y + (area_h - h) / 2
        set_rect(g, x, y, w, h)
        try:
            obj.originalSize.width = w
            obj.originalSize.height = h
        except Exception:
            pass
        for mask in masks:
            try:
                parent = str(mask.super.parent.identifier)
            except Exception:
                continue
            if parent == hid:
                mg = walk_geometry(mask)
                set_rect(mg, 0, 0, w, h)
                set_path_rect(mask, w, h)
        changed += 1
    return changed


def polish_all():
    idx = os.path.join(KEY, "Index")
    style_n = 0
    layout_n = 0
    for fn in sorted(os.listdir(idx)):
        if not fn.endswith(".iwa"):
            continue
        path = os.path.join(idx, fn)
        try:
            iwa = load_iwa(path)
        except Exception:
            continue
        changed = False
        for chunk in iwa.chunks:
            for seg in chunk.archives:
                for obj in seg.objects:
                    if restyle_obj(obj):
                        style_n += 1
                        changed = True
        if fn.startswith("Slide-") and "Template" not in fn:
            c = layout_slide_iwa(iwa)
            if c:
                layout_n += c
                changed = True
        if changed:
            save_iwa(path, iwa)
    print("styles", style_n, "images laid out", layout_n)


def main():
    if not os.path.isdir(KEY):
        raise SystemExit(f"expected package directory: {KEY}")
    replace_gym_photo()
    polish_all()
    layout_gym_slide()  # after generic layout, pin the gym slide
    print("done")


if __name__ == "__main__":
    main()
