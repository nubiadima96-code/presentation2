#!/usr/bin/env python3
"""Build a widescreen PPTX from the live web deck, then Keynote saves it as .key.
Never writes into Нечіпати."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT_PPTX = ROOT / "Шлях важливіший за ціль — DSC.pptx"
OUT_KEY = ROOT / "Шлях важливіший за ціль — DSC.key"
BG = ASSETS / "key-bg.jpg"
LOGO = ASSETS / "key-logo.png"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)
INK = RGBColor(0x0A, 0x1C, 0x2E)
SUB = RGBColor(0x3D, 0x5F, 0x7A)
BLUE = RGBColor(0x1A, 0x6F, 0xB5)
MUTED = RGBColor(0x5A, 0x73, 0x88)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

QUOTE_PHOTO = {31, 192, 193, 194, 195}
ROLES_ID = 43
EVEN_TRIO = 199
PLACE_ID = 30
CONTACT_ID = 202
MANIFESTO_ID = 201
ROSTER_ID = 46

TITLE_FONT = "Georgia"
BODY_FONT = "Helvetica Neue"


def emu(n):
    return int(n) if isinstance(n, int) else int(n)


def set_run(run, size, color, bold=False, italic=False, font=TITLE_FONT):
    run.font.size = size
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font


def add_text(slide, x, y, w, h, text, size, color, bold=False, italic=False, font=TITLE_FONT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    try:
        tf._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}.get(anchor, "t"))
    except Exception:
        pass
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    set_run(run, size, color, bold, italic, font)
    return box


def add_multitext(slide, x, y, w, h, lines, size, color, italic=False, font=TITLE_FONT, leading_scale=1.15):
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(6)
        run = p.add_run()
        run.text = line
        set_run(run, size if i == 0 else Pt(max(14, int(size.pt * 0.62))), color if i == 0 else SUB, False, italic if i == 0 else False, font if i == 0 else BODY_FONT)
    return box


def round_pic(shape, pct=0.06):
    spPr = shape._element.spPr
    prst = spPr.find(qn("a:prstGeom"))
    if prst is None:
        prst = etree.SubElement(spPr, qn("a:prstGeom"))
    prst.set("prst", "roundRect")
    avLst = prst.find(qn("a:avLst"))
    if avLst is None:
        avLst = etree.SubElement(prst, qn("a:avLst"))
    else:
        for child in list(avLst):
            avLst.remove(child)
    gd = etree.SubElement(avLst, qn("a:gd"))
    gd.set("name", "adj")
    gd.set("fmla", f"val {int(pct * 100000)}")


def glass_behind(slide, x, y, w, h, pad=Inches(0.06)):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x - pad, y - pad, w + pad * 2, h + pad * 2)
    sh.line.fill.background()
    sh.fill.solid()
    sh.fill.fore_color.rgb = WHITE
    try:
        solid = sh.fill._xPr
        # keep a soft white frame
        sh.fill.fore_color.rgb = RGBColor(0xF7, 0xFB, 0xFF)
    except Exception:
        pass
    sh.adjustments[0] = 0.12
    return sh


def fit_in(max_w, max_h, iw, ih):
    if not iw or not ih:
        return max_w, max_h
    s = min(max_w / iw, max_h / ih)
    return iw * s, ih * s


def add_photo(slide, path, box_x, box_y, box_w, box_h, center=True):
    p = Path(path)
    if not p.is_file():
        return None
    from PIL import Image

    with Image.open(p) as im:
        iw, ih = im.size
    fw, fh = fit_in(box_w, box_h, iw, ih)
    x = box_x + (box_w - fw) / 2 if center else box_x
    y = box_y + (box_h - fh) / 2 if center else box_y
    glass_behind(slide, x, y, fw, fh)
    pic = slide.shapes.add_picture(str(p), x, y, fw, fh)
    round_pic(pic)
    return pic


def add_chrome(slide, s, total):
    if LOGO.is_file():
        slide.shapes.add_picture(str(LOGO), Inches(0.38), Inches(0.22), height=Inches(0.42))
    add_text(
        slide,
        Inches(10.4),
        Inches(0.28),
        Inches(2.55),
        Inches(0.32),
        "WE DON'T LIE",
        Pt(11),
        MUTED,
        bold=True,
        font=BODY_FONT,
        align=PP_ALIGN.RIGHT,
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_text(
        slide,
        Inches(3.4),
        Inches(7.08),
        Inches(6.5),
        Inches(0.28),
        "Від першого імпланта до навчання лікарів",
        Pt(11),
        MUTED,
        italic=True,
        font=TITLE_FONT,
        align=PP_ALIGN.CENTER,
    )
    add_text(
        slide,
        Inches(0.4),
        Inches(7.08),
        Inches(2.8),
        Inches(0.28),
        f"{s['id']}  /  {total}   {s.get('section') or ''}".upper(),
        Pt(9),
        MUTED,
        bold=True,
        font=BODY_FONT,
        align=PP_ALIGN.LEFT,
    )


def title_pt(text: str) -> Pt:
    n = len(text or "")
    if n > 110:
        return Pt(20)
    if n > 80:
        return Pt(24)
    if n > 52:
        return Pt(28)
    if n > 32:
        return Pt(34)
    return Pt(40)


def ratio_of(p):
    w = float(p.get("w") or 1)
    h = float(p.get("h") or 1)
    return w / h if h else 1


def resolve(src: str) -> Path:
    return ROOT / src


def video_poster(src: str) -> Path | None:
    p = resolve(src)
    if not p.is_file():
        return None
    out = ASSETS / "photos" / f"_poster_{p.stem}.jpg"
    if out.is_file():
        return out
    try:
        import imageio_ffmpeg

        ff = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run(
            [ff, "-y", "-ss", "0.8", "-i", str(p), "-frames:v", "1", "-q:v", "3", str(out)],
            capture_output=True,
            check=False,
        )
        return out if out.is_file() else None
    except Exception:
        return None


def add_bg(slide):
    slide.shapes.add_picture(str(BG), 0, 0, SLIDE_W, SLIDE_H)


def add_blue_bar(slide, x, y, h):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, Inches(0.06), h)
    bar.line.fill.background()
    bar.fill.solid()
    bar.fill.fore_color.rgb = BLUE
    return bar


def layout_text(slide, s):
    cap = (s.get("caption") or "").strip()
    sub = (s.get("subtitle") or "").strip()
    lines = [ln.strip() for ln in sub.split("\n") if ln.strip()]
    add_blue_bar(slide, Inches(0.55), Inches(2.15), Inches(3.0))
    title = cap or (lines[0] if lines else "")
    rest = lines if cap else lines[1:]
    add_text(slide, Inches(0.85), Inches(2.05), Inches(11.6), Inches(1.8), title, title_pt(title), INK, italic=True, font=TITLE_FONT, anchor=MSO_ANCHOR.TOP)
    if rest:
        add_multitext(slide, Inches(0.85), Inches(3.9), Inches(10.5), Inches(2.6), rest, Pt(20), SUB, italic=False, font=BODY_FONT)


def layout_side(slide, s, photos):
    cap = (s.get("caption") or "").strip()
    sub = (s.get("subtitle") or "").strip()
    add_text(slide, Inches(0.45), Inches(1.15), Inches(4.55), Inches(4.8), cap, title_pt(cap), INK, italic=True, font=TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
    if sub:
        add_text(slide, Inches(0.45), Inches(5.5), Inches(4.55), Inches(1.2), sub.replace("\n", "  ·  "), Pt(18), SUB, font=BODY_FONT, anchor=MSO_ANCHOR.TOP)
    if photos:
        add_photo(slide, resolve(photos[0]["src"]), Inches(5.15), Inches(0.95), Inches(7.7), Inches(5.85))


def layout_top(slide, s, photos):
    cap = (s.get("caption") or "").strip()
    sub = (s.get("subtitle") or "").strip()
    if cap:
        add_text(slide, Inches(0.5), Inches(0.78), Inches(12.3), Inches(0.7), cap, Pt(26), INK, italic=True, font=TITLE_FONT, anchor=MSO_ANCHOR.MIDDLE)
    if sub:
        add_text(slide, Inches(0.5), Inches(1.38), Inches(12.3), Inches(0.4), sub.replace("\n", "  ·  "), Pt(14), SUB, font=BODY_FONT)
    y = Inches(1.85) if cap else Inches(0.95)
    h = Inches(4.95) if cap else Inches(5.85)
    layout_photos(slide, photos, Inches(0.45), y, Inches(12.4), h)


def layout_photos(slide, photos, x, y, w, h, square=False):
    n = len(photos)
    if n <= 0:
        return
    if n == 1:
        add_photo(slide, resolve(photos[0]["src"]), x, y, w, h)
        return
    gap = Inches(0.18)
    cell = (w - gap * (n - 1)) / n
    side = min(cell, h) if square else None
    for i, p in enumerate(photos):
        cx = x + i * (cell + gap)
        if square and side:
            px = cx + (cell - side) / 2
            py = y + (h - side) / 2
            add_photo(slide, resolve(p["src"]), px, py, side, side)
        else:
            add_photo(slide, resolve(p["src"]), cx, y, cell, h)


def layout_roles(slide, photos):
    docs = photos[:2]
    lead = photos[2]
    lect = photos[3:]
    add_text(slide, Inches(0.7), Inches(0.82), Inches(3.5), Inches(0.4), "ЛІКАР", Pt(16), INK, bold=True, font=BODY_FONT, align=PP_ALIGN.CENTER)
    add_text(slide, Inches(9.1), Inches(0.82), Inches(3.5), Inches(0.4), "ЛЕКТОР", Pt(16), INK, bold=True, font=BODY_FONT, align=PP_ALIGN.CENTER)
    # left stack
    if docs:
        hh = Inches(2.7)
        for i, p in enumerate(docs[:2]):
            add_photo(slide, resolve(p["src"]), Inches(0.55), Inches(1.25) + i * (hh + Inches(0.16)), Inches(3.7), hh)
    if lead:
        cap = (lead.get("caption") or "Керівник").strip()
        add_text(slide, Inches(4.55), Inches(0.82), Inches(4.2), Inches(0.4), cap, Pt(16), INK, bold=True, font=BODY_FONT, align=PP_ALIGN.CENTER)
        add_photo(slide, resolve(lead["src"]), Inches(4.55), Inches(1.25), Inches(4.2), Inches(5.5))
    if lect:
        hh = Inches(2.7)
        for i, p in enumerate(lect[:2]):
            add_photo(slide, resolve(p["src"]), Inches(9.05), Inches(1.25) + i * (hh + Inches(0.16)), Inches(3.7), hh)


def layout_place(slide, s, photos):
    cap = (s.get("caption") or "Радивилів").strip()
    lines = [ln.strip() for ln in (s.get("subtitle") or "").split("\n") if ln.strip()]
    add_text(slide, Inches(0.5), Inches(1.2), Inches(4.6), Inches(1.1), cap, Pt(40), INK, italic=True, font=TITLE_FONT)
    if lines:
        add_multitext(slide, Inches(0.5), Inches(2.4), Inches(4.6), Inches(3.8), lines, Pt(22), SUB, font=BODY_FONT)
    if photos:
        add_photo(slide, resolve(photos[0]["src"]), Inches(5.3), Inches(1.05), Inches(7.5), Inches(5.7))


def layout_contact(slide, s, photos):
    add_text(slide, Inches(0.55), Inches(2.0), Inches(12.2), Inches(0.7), "DSC on AIR", Pt(22), SUB, bold=True, font=BODY_FONT, align=PP_ALIGN.CENTER)
    add_text(slide, Inches(0.55), Inches(2.7), Inches(12.2), Inches(1.1), "+380 99 564 65 45", Pt(44), INK, italic=True, font=TITLE_FONT, align=PP_ALIGN.CENTER)
    if photos:
        layout_photos(slide, photos, Inches(3.2), Inches(4.05), Inches(6.9), Inches(2.55))


def audio_to_mp4(src: str) -> Path | None:
    p = resolve(src)
    if not p.is_file():
        return None
    out = ASSETS / "videos" / f"{p.stem}_audio.mp4"
    if out.is_file() and out.stat().st_mtime >= p.stat().st_mtime:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    still = ASSETS / "photos" / f"_poster_{p.stem}.jpg"
    if not still.is_file():
        from PIL import Image, ImageDraw, ImageFont

        im = Image.open(BG).convert("RGB").resize((1920, 1080))
        d = ImageDraw.Draw(im)
        d.ellipse((860, 420, 1060, 620), outline=(26, 111, 181), width=8)
        d.polygon([(930, 470), (930, 570), (1020, 520)], fill=(26, 111, 181))
        im.save(still, "JPEG", quality=90)
    try:
        import imageio_ffmpeg

        ff = imageio_ffmpeg.get_ffmpeg_exe()
        r = subprocess.run(
            [
                ff, "-y", "-loop", "1", "-i", str(still), "-i", str(p),
                "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
                "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(out),
            ],
            capture_output=True, text=True,
        )
        return out if r.returncode == 0 and out.is_file() else None
    except Exception:
        return None


def add_video(slide, src: str, poster: Path | None, box_x, box_y, box_w, box_h, vw=16, vh=9):
    p = resolve(src)
    if not p.is_file():
        return None
    fw, fh = fit_in(box_w, box_h, vw or 16, vh or 9)
    x = box_x + (box_w - fw) / 2
    y = box_y + (box_h - fh) / 2
    glass_behind(slide, x, y, fw, fh)
    poster_path = poster if poster and poster.is_file() else video_poster(src)
    kwargs = {"mime_type": "video/mp4"}
    if poster_path and poster_path.is_file():
        kwargs["poster_frame_image"] = str(poster_path)
    try:
        return slide.shapes.add_movie(str(p), x, y, fw, fh, **kwargs)
    except Exception as e:
        print("movie fail", p.name, e)
        if poster_path and poster_path.is_file():
            return add_photo(slide, poster_path, x, y, fw, fh)
        return None


def layout_video(slide, s):
    cap = (s.get("caption") or "").strip()
    v = (s.get("videos") or [None])[0]
    if not v:
        add_text(slide, Inches(0.8), Inches(3.0), Inches(11.7), Inches(1.2), cap or "Відео", Pt(32), INK, italic=True, font=TITLE_FONT, align=PP_ALIGN.CENTER)
        return
    if v.get("kind") == "audio":
        layout_text(slide, s)
        mp4 = audio_to_mp4(v.get("src") or "")
        if mp4:
            add_video(slide, str(mp4.relative_to(ROOT)), video_poster(str(mp4.relative_to(ROOT))), Inches(5.4), Inches(6.15), Inches(2.5), Inches(0.7), 16, 5)
        return
    if cap:
        add_text(slide, Inches(0.5), Inches(0.8), Inches(12.3), Inches(0.55), cap, Pt(26), INK, italic=True, font=TITLE_FONT)
    poster = resolve(v["poster"]) if v.get("poster") else None
    if not poster or not poster.is_file():
        poster = video_poster(v.get("src") or "")
    y = Inches(1.5) if cap else Inches(0.95)
    h = Inches(5.25) if cap else Inches(5.8)
    add_video(slide, v.get("src") or "", poster, Inches(1.15), y, Inches(11.0), h, v.get("w") or 16, v.get("h") or 9)


def build():
    data = json.loads((ASSETS / "slides.json").read_text())
    slides = data["slides"]
    total = len(slides)
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    for s in slides:
        slide = prs.slides.add_slide(blank)
        add_bg(slide)
        photos = [p for p in (s.get("photos") or []) if (p.get("src") and resolve(p["src"]).is_file())]
        videos = s.get("videos") or []
        cap = (s.get("caption") or "").strip()
        sub = (s.get("subtitle") or "").strip()
        layout = s.get("layout") or "empty"
        sid = s.get("id")
        has_copy = bool(cap or sub)

        try:
            if sid == PLACE_ID:
                layout_place(slide, s, photos)
            elif sid == ROLES_ID:
                layout_roles(slide, photos)
            elif sid == CONTACT_ID:
                layout_contact(slide, s, photos)
            elif sid == MANIFESTO_ID:
                layout_video(slide, s) if videos else layout_text(slide, s)
            elif sid == ROSTER_ID:
                layout_text(slide, s)
            elif layout == "video" or (videos and not photos):
                layout_video(slide, s)
            elif not photos and not videos:
                layout_text(slide, s)
            elif sid in QUOTE_PHOTO or (
                has_copy
                and len(photos) == 1
                and ratio_of(photos[0]) < 0.85
            ):
                layout_side(slide, s, photos)
            elif sid == EVEN_TRIO:
                layout_photos(slide, photos, Inches(0.45), Inches(0.95), Inches(12.4), Inches(5.85), square=True)
            elif not has_copy:
                layout_photos(slide, photos, Inches(0.55), Inches(0.9), Inches(12.2), Inches(5.9))
            else:
                layout_top(slide, s, photos)
        except Exception as e:
            add_text(slide, Inches(1), Inches(3), Inches(11), Inches(1), f"{cap or sid}", Pt(28), INK, italic=True, font=TITLE_FONT)
            print("slide fail", sid, e)

        add_chrome(slide, s, total)
        print(f"{sid:03} {layout:12} {cap[:40]!r}")

    prs.save(OUT_PPTX)
    print("WROTE", OUT_PPTX, "bytes", OUT_PPTX.stat().st_size)
    export_keynote()


def keynote_installed() -> bool:
    for p in (
        "/Applications/Keynote.app",
        "/System/Applications/Keynote.app",
    ):
        if os.path.isdir(p):
            return True
    return False


def export_keynote():
    """Open the PPTX in Keynote and save a native .key — no UI clicking."""
    pptx = str(OUT_PPTX)
    key = str(OUT_KEY)
    if not keynote_installed():
        print("NO KEYNOTE.APP — wrote PPTX only:", pptx)
        return
    script = f'''
tell application "Keynote"
  set src to POSIX file "{pptx}"
  set dest to POSIX file "{key}"
  set theDoc to open src
  delay 4
  save theDoc in dest
  close theDoc saving no
end tell
'''
    print("KEYNOTE EXPORT", key)
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print("osascript err", r.stderr[-800:])
        return
    print("WROTE", key if Path(key).exists() else "missing")


if __name__ == "__main__":
    build()
