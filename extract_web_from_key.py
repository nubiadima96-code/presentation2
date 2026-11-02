#!/usr/bin/env python3
"""Read-only extract from Нечіпати/*.key into the web deck. Never writes into Нечіпати."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import warnings
import zipfile

import imageio_ffmpeg
from PIL import Image
from google.protobuf.json_format import MessageToDict as m2d
from keynote_parser.codec import IWAFile, UnknownArchiveWarning

warnings.simplefilter("ignore", UnknownArchiveWarning)

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "Нечіпати", "презентація від першого імпланта до навчання лікарів.key")
ASSETS = os.path.join(ROOT, "assets")
PHOTO_DIR = os.path.join(ASSETS, "photos")
VID_DIR = os.path.join(ASSETS, "videos")
AUD_DIR = os.path.join(ASSETS, "audio")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
MAX_SIDE = 1800


def dec_name(fn: str) -> str:
    if any(c in fn for c in "╨╤╠"):
        try:
            return fn.encode("cp437").decode("utf-8")
        except Exception:
            return fn
    return fn


def load_iwa(z, name):
    return IWAFile.from_buffer(z.read(name), name)


def section_for(caption: str, prev: str, idx: int) -> str:
    t = (caption or "").lower()
    if idx == 1:
        return "Титул"
    keys = [
        ("контакт", "Контакт"),
        ("телефон", "Контакт"),
        ("кліп", "Фінал"),
        ("який я лікар", "Фінал"),
        ("музик", "Фінал"),
        ("філософ", "Філософія"),
        ("ментор", "Менторство"),
        ("школа dsc", "Школа"),
        ("dsc implantology", "Школа"),
        ("курс", "Курси"),
        ("carlos", "Курси"),
        ("реконструк", "Реконструкція"),
        ("графт", "Реконструкція"),
        ("мембран", "Реконструкція"),
        ("клінік", "Клініка"),
        ("радівил", "Радивилів"),
        ("інтерн", "Інтернатура"),
        ("універс", "Шлях до медицини"),
        ("гіпсу", "Шлях до медицини"),
        ("11 клас", "Шлях до медицини"),
        ("спортзал", "Дитинство"),
        ("щоденник", "Дитинство"),
        ("школа", "Дитинство"),
        ("зуб", "Дитинство"),
        ("roman", "Дитинство"),
    ]
    for k, s in keys:
        if k in t:
            return s
    return prev or "DSC"


def main():
    assert os.path.isfile(SRC), SRC
    z = zipfile.ZipFile(SRC)
    names = {n: n for n in z.namelist()}

    by_id = {}
    for n in z.namelist():
        if not n.startswith("Data/"):
            continue
        m = re.search(r"-(\d+)\.[^.]+$", os.path.basename(n))
        if m:
            by_id[m.group(1)] = n

    doc = load_iwa(z, "Index/Document.iwa")
    show = None
    nodes = {}
    for chunk in doc.chunks:
        for seg in chunk.archives:
            ident = getattr(seg.header, "identifier", None)
            for obj in seg.objects:
                n = obj.__class__.__name__
                d = m2d(obj, preserving_proto_field_name=True)
                if n == "ShowArchive":
                    show = d
                if n == "SlideNodeArchive":
                    nodes[str(ident)] = d

    meta = load_iwa(z, "Index/Metadata.iwa")
    loc = {}
    for chunk in meta.chunks:
        for seg in chunk.archives:
            for obj in seg.objects:
                if obj.__class__.__name__ != "PackageMetadata":
                    continue
                d = m2d(obj, preserving_proto_field_name=True)
                for c in d.get("components") or []:
                    loc[str(c.get("identifier"))] = c.get("locator") or ""

    def iwa_name(sid):
        l = loc.get(str(sid), "")
        cands = []
        if l:
            cands += [f"Index/{l}.iwa", f"Index/{l}"]
        cands.append(f"Index/Slide-{sid}.iwa")
        for c in cands:
            if c in names:
                return c
        for n in names:
            if n.endswith(f"Slide-{sid}.iwa") or n.endswith(f"-{sid}.iwa") and n.startswith("Index/"):
                return n
        return None

    shutil.rmtree(PHOTO_DIR, ignore_errors=True)
    shutil.rmtree(VID_DIR, ignore_errors=True)
    shutil.rmtree(AUD_DIR, ignore_errors=True)
    os.makedirs(PHOTO_DIR)
    os.makedirs(VID_DIR)
    os.makedirs(AUD_DIR)

    slides = []
    prev_sec = "Титул"
    vis = 0
    tree = (show.get("slideTree") or {}).get("slides") or []

    def save_photo(ident, vis_id, k):
        zname = by_id.get(str(ident))
        if not zname:
            return None
        raw = z.read(zname)
        try:
            im = Image.open(io.BytesIO(raw))
            im = im.convert("RGB")
        except Exception:
            return None
        w, h = im.size
        if min(w, h) < 64:
            return None
        if max(w, h) > MAX_SIDE:
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        out = os.path.join(PHOTO_DIR, f"s{vis_id:03d}_{k}.jpg")
        im.save(out, "JPEG", quality=86, optimize=True)
        return {"src": f"assets/photos/{os.path.basename(out)}", "w": im.size[0], "h": im.size[1]}

    def save_video(ident, vis_id, start, end):
        zname = by_id.get(str(ident))
        if not zname:
            return None
        ext = os.path.splitext(zname)[1].lower()
        raw = z.read(zname)
        if ext in (".mp3", ".m4a", ".aac", ".wav"):
            out = os.path.join(AUD_DIR, f"s{vis_id:03d}.mp3")
            open(out, "wb").write(raw)
            return {"src": f"assets/audio/{os.path.basename(out)}", "kind": "audio", "start": start, "end": end}
        tmp = os.path.join(VID_DIR, f"_src_{ident}{ext}")
        open(tmp, "wb").write(raw)
        out = os.path.join(VID_DIR, f"s{vis_id:03d}.mp4")
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
        if start and float(start) > 0.05:
            cmd += ["-ss", str(float(start))]
        cmd += ["-i", tmp]
        if end and float(end) > 0:
            dur = float(end) - float(start or 0)
            if dur > 0.2:
                cmd += ["-t", f"{dur:.3f}"]
        cmd += [
            "-vf", "scale='min(1280,iw)':-2",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "96k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            out,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
        if r.returncode != 0 or not os.path.isfile(out):
            print("ffmpeg fail", ident, r.stderr[-400:])
            # fallback: keep original if small enough
            return None
        return {"src": f"assets/videos/{os.path.basename(out)}", "kind": "video", "start": 0, "end": None}

    for i, ref in enumerate(tree, 1):
        nid = ref.get("identifier")
        node = nodes.get(str(nid), {})
        if node.get("isSkipped"):
            continue
        sid = (node.get("slide") or {}).get("identifier")
        name = iwa_name(sid)
        if not name:
            print("missing iwa", i, sid)
            continue
        vis += 1
        iwa = load_iwa(z, name)
        texts = []
        imgs = []
        movs = []
        for chunk in iwa.chunks:
            for seg in chunk.archives:
                for obj in seg.objects:
                    cn = obj.__class__.__name__
                    d = m2d(obj, preserving_proto_field_name=True)
                    if cn == "StorageArchive":
                        if (d.get("kind") or "") == "NOTE":
                            continue
                        t = "".join(d.get("text") or []).replace("\ufffc", "").strip()
                        if t:
                            texts.append(t)
                    elif cn == "ImageArchive":
                        ident = (d.get("data") or {}).get("identifier")
                        nat = d.get("naturalSize") or {}
                        if ident:
                            imgs.append((ident, float(nat.get("width") or 0), float(nat.get("height") or 0)))
                    elif cn == "MovieArchive":
                        ident = (d.get("movieData") or d.get("data") or {}).get("identifier")
                        st = d.get("startTime")
                        en = d.get("endTime")
                        nat = d.get("naturalSize") or {}
                        if ident:
                            movs.append((ident, float(st or 0), float(en or 0), nat))

        caption = " · ".join(" ".join(t.split()) for t in texts) if texts else ""
        if not caption:
            if movs:
                caption = "Відео"
            elif imgs:
                caption = ""
        prev_sec = section_for(caption, prev_sec, vis)

        photos = []
        for k, (ident, nw, nh) in enumerate(imgs, 1):
            p = save_photo(ident, vis, k)
            if p:
                photos.append(p)

        videos = []
        for ident, st, en, nat in movs:
            v = save_video(ident, vis, st, en)
            if v:
                v["w"] = int(nat.get("width") or 1920)
                v["h"] = int(nat.get("height") or 1080)
                videos.append(v)

        layout = "empty"
        if videos and not photos:
            layout = "video"
        elif len(photos) == 1:
            layout = "single"
        elif len(photos) == 2:
            layout = "duo"
        elif len(photos) >= 3:
            layout = "trio"

        slides.append(
            {
                "id": vis,
                "srcId": i,
                "section": prev_sec,
                "caption": caption,
                "text": "\n".join(texts),
                "photos": photos,
                "videos": videos,
                "layout": layout,
            }
        )
        print(f"{vis:03} kn={i:03} {layout:6} p={len(photos)} v={len(videos)} {caption[:70]!r}")

    payload = {"total": len(slides), "slides": slides}
    open(os.path.join(ASSETS, "slides.json"), "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=0)
    )
    print("DONE slides", len(slides), "photos", sum(len(s["photos"]) for s in slides), "videos", sum(len(s["videos"]) for s in slides))


if __name__ == "__main__":
    main()
