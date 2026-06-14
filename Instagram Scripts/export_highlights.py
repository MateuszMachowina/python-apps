"""
Highlight Exporter — generuje MP4 wyglądający jak nagranie ekranu z Instagrama.
Wymaga: ffmpeg na PATH, Pillow
"""

import os, sys, json, subprocess, shutil, tempfile, re, io, threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ─── Config ───────────────────────────────────────────────────────────────────
HIGHLIGHTS_DIR = Path("highlights")
EXPORTS_DIR    = Path("exports")
FLAGS_DIR      = Path("flags")

OUT_W, OUT_H = 1080, 1920
FPS          = 30
PHOTO_SEC    = 4

# ─── Colours (matching Instagram dark UI) ─────────────────────────────────────
BG      = "#000000"
ACCENT  = "#c13584"
ACCENT2 = "#833ab4"
ACCENT3 = "#fd1d1d"
GOLD    = "#fcaf45"
TEXT    = "#ffffff"
SUBTEXT = "#aaaaaa"
SUCCESS = "#2ecc71"
ERROR   = "#e74c3c"
GOLD_UI = "#f5a623"

# GUI colours
BG_UI     = "#0a0a0a"; SURF_UI = "#161616"; CARD_UI   = "#1e1e1e"
ACCENT_UI = "#c13584"; ACC2_UI = "#833ab4"; TEXT_UI   = "#f0f0f0"; SUB_UI = "#888888"
FH = ("Segoe UI", 20, "bold"); FS = ("Segoe UI", 11)
FM = ("Consolas", 9);          FB = ("Segoe UI", 11, "bold")

def _hex(c):
    h = c.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ─── Font loader ──────────────────────────────────────────────────────────────
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\seguiemj.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except Exception: pass
    return ImageFont.load_default()


# ─── Flag fetcher ─────────────────────────────────────────────────────────────
_flag_cache: dict = {}
_CC_RE = re.compile(r'\b([A-Z]{2})\s*$')

def _fetch_flag(cc: str, height: int = 20) -> Image.Image | None:
    key = f"{cc}:{height}"
    if key in _flag_cache: return _flag_cache[key]
    FLAGS_DIR.mkdir(exist_ok=True)
    local = FLAGS_DIR / f"{cc.lower()}.png"
    raw = None
    if local.exists():
        try: raw = local.read_bytes()
        except Exception: pass
    if not raw:
        import urllib.request
        for url in [f"https://flagcdn.com/20x15/{cc.lower()}.png"]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6) as r: raw = r.read()
                local.write_bytes(raw); break
            except Exception: continue
    if not raw: _flag_cache[key] = None; return None
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        w = max(1, int(img.width * height / img.height))
        _flag_cache[key] = img.resize((w, height), Image.LANCZOS)
        return _flag_cache[key]
    except Exception: _flag_cache[key] = None; return None

def extract_cc(title: str):
    m = _CC_RE.search(title)
    if m: return title[:m.start()].rstrip(), m.group(1)
    return title, None


# ─── PIL helpers ──────────────────────────────────────────────────────────────
def circle_crop(img: Image.Image, size: int) -> Image.Image:
    S = size * 4
    img  = img.convert("RGBA").resize((S, S), Image.LANCZOS)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S-1, S-1), fill=255)
    out  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    return out.resize((size, size), Image.LANCZOS)

def draw_ring(size: int, colors, thickness: int = 5) -> Image.Image:
    S  = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = cy = S // 2
    step = max(1, (thickness * 4) // len(colors))
    for i, col in enumerate(colors):
        r = max(1, cx - i * step)
        d.ellipse((cx-r, cy-r, cx+r, cy+r),
                  outline=(*_hex(col), 255), width=step + 1)
    return img.resize((size, size), Image.LANCZOS)


# ─── Instagram-style overlay ──────────────────────────────────────────────────
def build_overlay(cover_thumb: Image.Image | None,
                  title: str, cc: str | None,
                  item_idx: int, total: int) -> Image.Image:
    """
    Full 1080×1920 RGBA overlay — transparent centre, Instagram UI at top.
    Matches the look of Instagram story screen recording.
    """
    ov = Image.new("RGBA", (OUT_W, OUT_H), (0, 0, 0, 0))
    d  = ImageDraw.Draw(ov)

    # ── Top gradient scrim (makes header readable on any background) ──────────
    scrim_h = 200
    for y in range(scrim_h):
        alpha = int(210 * (1 - y / scrim_h) ** 0.5)
        d.line([(0, y), (OUT_W, y)], fill=(0, 0, 0, alpha))

    # ── Story progress bars ───────────────────────────────────────────────────
    # Position: top, like Instagram (thin bars, small gap, white/dimmed)
    bar_h    = 4
    bar_y    = 52
    margin_x = 12
    gap      = 5
    n_bars   = min(total, 100)   # cap at 100 bars for readability
    avail    = OUT_W - margin_x * 2 - gap * (n_bars - 1)
    bw       = max(2, avail // n_bars)

    for i in range(n_bars):
        x1 = margin_x + i * (bw + gap)
        x2 = x1 + bw
        if i < item_idx:
            fill = (*_hex(TEXT), 230)   # watched — bright
        elif i == item_idx:
            fill = (*_hex(TEXT), 230)   # current — bright
        else:
            fill = (*_hex(TEXT), 70)    # upcoming — dim
        d.rounded_rectangle([x1, bar_y, x2, bar_y + bar_h], radius=2, fill=fill)

    # ── Header row ────────────────────────────────────────────────────────────
    hdr_y     = 70
    av_size   = 80
    ring_size = av_size + 12

    # Avatar ring (gradient: red→pink→purple→gold, like Instagram)
    ring = draw_ring(ring_size, [ACCENT3, ACCENT, ACCENT2, GOLD], thickness=6)
    av_x = margin_x
    av_y = hdr_y
    ov.paste(ring, (av_x, av_y), ring)

    # Avatar image
    if cover_thumb:
        av_img = circle_crop(cover_thumb, av_size)
        off    = (ring_size - av_size) // 2
        ov.paste(av_img, (av_x + off, av_y + off), av_img)

    # Text block: title + flag + counter
    tx = av_x + ring_size + 16
    ty = av_y + (ring_size // 2) - 28   # vertically centre in avatar

    font_title = _font(40, bold=True)
    font_count = _font(32)

    # Title
    d.text((tx, ty), title, font=font_title, fill=(*_hex(TEXT), 255))

    # Flag image to the right of title
    if cc:
        try:
            tw = int(d.textlength(title, font=font_title))
        except Exception:
            tw = len(title) * 22
        flag = _fetch_flag(cc, height=30)
        if flag:
            fy = ty + (font_title.size - flag.height) // 2 + 4
            fx = tx + tw + 12
            if fx + flag.width < OUT_W - 20:
                ov.paste(flag, (fx, fy), flag)
        else:
            d.text((tx + tw + 12, ty), f"[{cc}]",
                   font=_font(32), fill=(*_hex(SUBTEXT), 180))

    # Story counter: "4 / 21" — small, grey, below title
    count_text = f"{item_idx + 1} / {total}"
    d.text((tx, ty + 48), count_text, font=font_count,
           fill=(*_hex(SUBTEXT), 200))

    # ── Bottom gradient scrim ─────────────────────────────────────────────────
    # Subtle darkening at bottom (like Instagram's gradient for caption area)
    bot_scrim_h = 160
    bot_start   = OUT_H - bot_scrim_h
    for y in range(bot_scrim_h):
        alpha = int(120 * (y / bot_scrim_h) ** 1.5)
        d.line([(0, bot_start + y), (OUT_W, bot_start + y)],
               fill=(0, 0, 0, alpha))

    return ov


# ─── Frame compositor ─────────────────────────────────────────────────────────
def fit_media(img: Image.Image) -> Image.Image:
    """Cover-fit to OUT_W×OUT_H, black letterbox if needed."""
    img = img.convert("RGB")
    iw, ih = img.size
    scale  = max(OUT_W / iw, OUT_H / ih)
    nw     = int(iw * scale)
    nh     = int(ih * scale)
    img    = img.resize((nw, nh), Image.LANCZOS)
    lf = (nw - OUT_W) // 2
    tp = (nh - OUT_H) // 2
    return img.crop((lf, tp, lf + OUT_W, tp + OUT_H))

def composite(media: Image.Image, overlay: Image.Image) -> Image.Image:
    base = media.convert("RGBA")
    return Image.alpha_composite(base, overlay).convert("RGB")


# ─── ffmpeg helpers ───────────────────────────────────────────────────────────
def extract_thumb(video_path: Path, out_path: Path) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", str(out_path)],
            timeout=15, check=True, capture_output=True)
        return out_path.exists()
    except Exception: return False

def get_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip())
    except Exception: return 5.0

def _run(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


# ─── Segment writers ──────────────────────────────────────────────────────────
def write_photo_segment(img_path: Path, overlay: Image.Image,
                        duration: float, out_path: Path, log_fn) -> bool:
    try:
        media = Image.open(img_path); media.load()
        frame = composite(fit_media(media), overlay)
        tmp   = out_path.with_suffix(".frame.png")
        frame.save(str(tmp), "PNG")
        r = _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(tmp),
            "-t", str(duration),
            "-vf", f"scale={OUT_W}:{OUT_H}",
            "-r", str(FPS),
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-an", str(out_path)
        ])
        tmp.unlink(missing_ok=True)
        if r.returncode != 0:
            log_fn(f"    ✘ ffmpeg: {r.stderr.decode()[:200]}", ERROR)
            return False
        return True
    except Exception as e:
        log_fn(f"    ✘ photo segment: {e}", ERROR); return False


def write_video_segment(vid_path: Path, overlay: Image.Image,
                        out_path: Path, log_fn) -> bool:
    try:
        tmp_ov = out_path.with_suffix(".ov.png")
        overlay.save(str(tmp_ov), "PNG")
        duration = get_duration(vid_path)

        # Scale video to fill 1080×1920, overlay UI, keep audio
        r = _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(vid_path),
            "-i", str(tmp_ov),
            "-filter_complex",
            (f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
             f"crop={OUT_W}:{OUT_H},setsar=1[bg];"
             f"[bg][1:v]overlay=0:0[out]"),
            "-map", "[out]",
            "-map", "0:a?",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(duration),
            str(out_path)
        ], timeout=300)
        tmp_ov.unlink(missing_ok=True)
        if r.returncode != 0:
            log_fn(f"    ✘ ffmpeg: {r.stderr.decode()[:200]}", ERROR)
            return False
        return True
    except Exception as e:
        log_fn(f"    ✘ video segment: {e}", ERROR); return False


def crossfade(seg_a: Path, seg_b: Path, out_path: Path, log_fn) -> bool:
    """xfade transition between two segments."""
    try:
        dur_a  = get_duration(seg_a)
        offset = max(0.01, dur_a - 0.3)

        # Try with audio crossfade first
        r = _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(seg_a), "-i", str(seg_b),
            "-filter_complex",
            (f"[0:v][1:v]xfade=transition=fade:duration=0.3:offset={offset:.3f}[vout];"
             f"[0:a][1:a]acrossfade=d=0.3[aout]"),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            str(out_path)
        ], timeout=120)

        if r.returncode != 0:
            # No audio (photos) — video-only crossfade
            r2 = _run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(seg_a), "-i", str(seg_b),
                "-filter_complex",
                (f"[0:v][1:v]xfade=transition=fade:duration=0.3:offset={offset:.3f}[vout]"),
                "-map", "[vout]",
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                "-an", str(out_path)
            ], timeout=120)
            if r2.returncode != 0:
                log_fn(f"    ✘ crossfade: {r2.stderr.decode()[:200]}", ERROR)
                return False
        return True
    except Exception as e:
        log_fn(f"    ✘ crossfade: {e}", ERROR); return False


def concat_list(paths: list[Path], out_path: Path, log_fn) -> bool:
    try:
        lst = out_path.with_suffix(".list.txt")
        lst.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
        r = _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0", "-i", str(lst),
            "-c", "copy", str(out_path)
        ], timeout=600)
        lst.unlink(missing_ok=True)
        if r.returncode != 0:
            log_fn(f"    ✘ concat: {r.stderr.decode()[:200]}", ERROR)
            return False
        return True
    except Exception as e:
        log_fn(f"    ✘ concat: {e}", ERROR); return False


# ─── Main export ──────────────────────────────────────────────────────────────
def export_highlight(coll: dict, photo_sec: int, log_fn, progress_fn) -> bool:
    title    = coll.get("title", "Untitled")
    files    = coll["_files"]
    coll_dir = coll["_dir"]
    total    = len(files)
    if total == 0:
        log_fn("  (empty — skipping)", SUBTEXT); return True

    # Load cover thumbnail
    cover = None
    cn    = coll.get("cover")
    if cn and (coll_dir / cn).exists():
        try:
            cover = Image.open(coll_dir / cn); cover.load(); cover = cover.convert("RGB")
        except Exception: pass
    if cover is None:
        for f in files:
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                try: cover = Image.open(f); cover.load(); cover = cover.convert("RGB"); break
                except Exception: pass
            elif f.suffix.lower() in (".mp4", ".mov"):
                tp = f.with_suffix(".thumb.jpg")
                if not tp.exists(): extract_thumb(f, tp)
                if tp.exists():
                    try: cover = Image.open(tp); cover.load(); cover = cover.convert("RGB"); break
                    except Exception: pass

    clean, cc = extract_cc(title)
    tmpdir    = Path(tempfile.mkdtemp(prefix="hl_"))
    segments  = []

    try:
        for idx, fpath in enumerate(files):
            log_fn(f"  [{idx+1}/{total}] {fpath.name}", SUBTEXT)
            overlay = build_overlay(cover, clean, cc, idx, total)
            seg     = tmpdir / f"seg_{idx:04d}.mp4"
            is_vid  = fpath.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv")

            if is_vid:
                ok = write_video_segment(fpath, overlay, seg, log_fn)
            else:
                ok = write_photo_segment(fpath, overlay, float(photo_sec), seg, log_fn)

            if ok: segments.append(seg)
            progress_fn(idx + 1, total)

        if not segments:
            log_fn("  No segments produced.", ERROR); return False

        if len(segments) == 1:
            final = segments[0]
        else:
            log_fn("  Applying crossfades …", SUBTEXT)
            current = segments[0]
            for i in range(1, len(segments)):
                faded = tmpdir / f"cf_{i:04d}.mp4"
                if crossfade(current, segments[i], faded, log_fn):
                    current = faded
                else:
                    log_fn("  (crossfade failed — hard cut)", GOLD_UI)
                    cat = tmpdir / f"cat_{i:04d}.mp4"
                    concat_list([current, segments[i]], cat, log_fn)
                    current = cat
            final = current

        username = coll.get("_username", "") or coll.get("username", "")
        out_dir  = EXPORTS_DIR / username if username else EXPORTS_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c for c in title if c.isalnum() or c in " _-").strip() or "highlight"
        dest = out_dir / f"{safe}.mp4"
        shutil.copy2(final, dest)
        log_fn(f"  ✔ Saved → {dest}", SUCCESS)
        return True

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ─── Data loading ─────────────────────────────────────────────────────────────
def _is_coll(d: Path) -> bool:
    return d.is_dir() and (
        (d / "meta.json").exists() or any(d.glob("*.mp4")) or any(d.glob("*.jpg")))

def _load_one(d: Path, username: str = "") -> dict | None:
    mf = d / "meta.json"
    if mf.exists():
        meta = json.loads(mf.read_text(encoding="utf-8"))
    else:
        items  = [{"index": i, "type": "video", "file": f.name}
                  for i, f in enumerate(sorted(d.glob("*.mp4")), 1)]
        items += [{"index": i, "type": "image", "file": f.name}
                  for i, f in enumerate(sorted(d.glob("*.jpg")), len(items)+1)]
        meta   = {"title": d.name, "items": items}
    meta["_dir"]      = d
    meta["_username"] = meta.get("username") or username
    meta["_files"]    = [d / it["file"] for it in meta.get("items", [])
                         if (d / it["file"]).exists()]
    return meta if meta["_files"] else None

def load_collections() -> list[dict]:
    cols = []
    if not HIGHLIGHTS_DIR.exists(): return cols
    for entry in HIGHLIGHTS_DIR.iterdir():
        if not entry.is_dir(): continue
        if _is_coll(entry):
            m = _load_one(entry, "")
            if m: cols.append(m)
        else:
            for sub in entry.iterdir():
                if _is_coll(sub):
                    m = _load_one(sub, entry.name)
                    if m: cols.append(m)
    cols.sort(key=lambda x: (x.get("_username", ""), x.get("title", "")))
    return cols


# ─── GUI ──────────────────────────────────────────────────────────────────────
class ExporterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Highlight Exporter")
        self.geometry("760x720")
        self.minsize(640, 600)
        self.configure(bg=BG_UI)
        self.collections   = load_collections()
        self.photo_sec_var = tk.StringVar(value=str(PHOTO_SEC))
        self.check_vars    = []
        self._build_ui()

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=SURF_UI, height=60)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=ACCENT_UI, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="✦ Highlight Exporter", bg=SURF_UI, fg=TEXT_UI,
                 font=FH).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="→ mp4", bg=SURF_UI, fg=SUB_UI,
                 font=FS).pack(side="left")

        # ── Settings bar ──────────────────────────────────────────────────────
        srow = tk.Frame(self, bg=CARD_UI, padx=20, pady=10)
        srow.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(srow, text="Photo duration:", bg=CARD_UI, fg=SUB_UI,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(srow, textvariable=self.photo_sec_var, bg=SURF_UI,
                 fg=TEXT_UI, insertbackground=TEXT_UI, relief="flat",
                 font=FS, width=3, justify="center").pack(
            side="left", padx=(8, 4), ipady=4)
        tk.Label(srow, text="s", bg=CARD_UI, fg=SUB_UI,
                 font=("Segoe UI", 10)).pack(side="left")
        tk.Label(srow, text=f"  →  {EXPORTS_DIR.resolve()}",
                 bg=CARD_UI, fg=SUB_UI, font=("Segoe UI", 8)).pack(side="left", padx=16)

        # ── Checklist (scrollable) ─────────────────────────────────────────────
        tk.Label(self, text="Select highlights to export:",
                 bg=BG_UI, fg=SUB_UI, font=("Segoe UI", 9)).pack(
            anchor="w", padx=20, pady=(10, 2))

        list_outer = tk.Frame(self, bg=SURF_UI)
        list_outer.pack(fill="x", padx=16, pady=(0, 0))

        # Canvas + scrollbar for long lists
        cl_canvas = tk.Canvas(list_outer, bg=SURF_UI, highlightthickness=0,
                              height=200)
        cl_scroll = ttk.Scrollbar(list_outer, orient="vertical",
                                   command=cl_canvas.yview)
        cl_canvas.configure(yscrollcommand=cl_scroll.set)
        cl_scroll.pack(side="right", fill="y")
        cl_canvas.pack(side="left", fill="both", expand=True)

        cl_inner = tk.Frame(cl_canvas, bg=SURF_UI)
        win_id   = cl_canvas.create_window((0, 0), window=cl_inner, anchor="nw")
        cl_inner.bind("<Configure>", lambda e: cl_canvas.configure(
            scrollregion=cl_canvas.bbox("all")))
        cl_canvas.bind("<Configure>", lambda e: cl_canvas.itemconfig(
            win_id, width=e.width))
        cl_canvas.bind("<MouseWheel>",
            lambda e: cl_canvas.yview_scroll(-1*(e.delta//120), "units"))

        if not self.collections:
            tk.Label(cl_inner, text="No highlights found. Run downloader.py first.",
                     bg=SURF_UI, fg=SUB_UI, font=("Segoe UI", 10)).pack(pady=20)
        else:
            last_user = None
            for coll in self.collections:
                u = coll.get("_username", "")
                if u and u != last_user:
                    last_user = u
                    tk.Label(cl_inner, text=f"@{u}", bg=SURF_UI, fg=ACCENT_UI,
                             font=("Segoe UI", 9, "bold")).pack(
                        anchor="w", padx=12, pady=(8, 2))
                var = tk.BooleanVar(value=True)
                self.check_vars.append(var)
                row = tk.Frame(cl_inner, bg=SURF_UI)
                row.pack(fill="x", padx=8, pady=1)
                tk.Checkbutton(row, variable=var, bg=SURF_UI, fg=TEXT_UI,
                               selectcolor=CARD_UI, activebackground=SURF_UI,
                               relief="flat").pack(side="left")
                n = len(coll["_files"])
                tk.Label(row, text=coll.get("title", "Untitled"),
                         bg=SURF_UI, fg=TEXT_UI,
                         font=("Segoe UI", 10, "bold")).pack(side="left")
                tk.Label(row, text=f"  ({n} items)", bg=SURF_UI, fg=SUB_UI,
                         font=("Segoe UI", 9)).pack(side="left")

        # Select all / none row
        sel_row = tk.Frame(self, bg=BG_UI)
        sel_row.pack(fill="x", padx=16, pady=(4, 0))
        for lbl, fn in [("Select all", self._sel_all), ("None", self._sel_none)]:
            tk.Button(sel_row, text=lbl, command=fn,
                      bg=CARD_UI, fg=SUB_UI, relief="flat",
                      font=("Segoe UI", 8), cursor="hand2",
                      padx=8, pady=3).pack(side="left", padx=(0, 4))

        # ── Progress ──────────────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=BG_UI, padx=16, pady=6)
        prog_frame.pack(fill="x")
        sty = ttk.Style(self); sty.theme_use("clam")
        sty.configure("EX.Horizontal.TProgressbar",
                       troughcolor=SURF_UI, background=ACCENT_UI,
                       bordercolor=BG_UI, lightcolor=ACCENT_UI,
                       darkcolor=ACC2_UI, thickness=8)
        self.progress = ttk.Progressbar(prog_frame, style="EX.Horizontal.TProgressbar",
                                         mode="determinate")
        self.progress.pack(fill="x")
        self.prog_lbl = tk.Label(prog_frame, text="Ready", bg=BG_UI,
                                  fg=SUB_UI, font=("Segoe UI", 9))
        self.prog_lbl.pack(anchor="e")

        # ── Log ───────────────────────────────────────────────────────────────
        log_frame = tk.Frame(self, bg=SURF_UI, padx=2, pady=2)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(4, 0))
        self.log = scrolledtext.ScrolledText(
            log_frame, bg="#0d0d0d", fg=TEXT_UI, font=FM,
            relief="flat", wrap="word", state="disabled",
            selectbackground=ACC2_UI, padx=10, pady=8)
        self.log.pack(fill="both", expand=True)
        for tag, col in [("err", ERROR), ("ok", SUCCESS), ("acc", ACCENT_UI),
                         ("sub", SUB_UI), ("gold", GOLD_UI)]:
            self.log.tag_configure(tag, foreground=col)

        # ── Bottom bar (always visible) ────────────────────────────────────────
        bot = tk.Frame(self, bg=SURF_UI, padx=16, pady=12)
        bot.pack(fill="x", side="bottom")

        self.export_btn = tk.Button(
            bot, text="▶  Export Selected", command=self._start_export,
            bg=ACCENT_UI, fg="white", activebackground=ACC2_UI,
            activeforeground="white", relief="flat",
            font=FB, cursor="hand2", padx=24, pady=10)
        self.export_btn.pack(side="right")

        tk.Button(bot, text="📂  Open exports", command=self._open_folder,
                  bg=CARD_UI, fg=TEXT_UI, activebackground=SURF_UI,
                  relief="flat", font=FB, cursor="hand2",
                  padx=14, pady=10).pack(side="right", padx=(0, 8))

        self.status_lbl = tk.Label(bot, text="Idle", bg=SURF_UI,
                                    fg=SUB_UI, font=FS)
        self.status_lbl.pack(side="left")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _sel_all(self):
        for v in self.check_vars: v.set(True)
    def _sel_none(self):
        for v in self.check_vars: v.set(False)

    def _log(self, msg, tag=""):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")

    def _start_export(self):
        selected = [self.collections[i]
                    for i, v in enumerate(self.check_vars) if v.get()]
        if not selected:
            self._log("Nothing selected.", "sub"); return
        try:    photo_sec = max(1, int(self.photo_sec_var.get()))
        except: photo_sec = PHOTO_SEC

        self.export_btn.config(state="disabled", text="Exporting …")
        self.status_lbl.config(text="Running …")
        self.progress["value"] = 0

        def run():
            tc = len(selected)
            for ci, coll in enumerate(selected):
                title = coll.get("title", "Untitled")
                self.after(0, self._log, f"\n📁  {title}", "acc")
                self.after(0, lambda t=title, i=ci: self.status_lbl.config(
                    text=f"{i+1}/{tc}: {t}"))

                def pfn(done, tot, ci=ci):
                    overall = (ci * 100 + int(done / tot * 100)) // tc
                    self.after(0, lambda o=overall, d=done, t=tot, i=ci: (
                        self.progress.__setitem__("value", o),
                        self.prog_lbl.config(text=f"{i+1}/{tc}  item {d}/{t}")))

                ok = export_highlight(
                    coll, photo_sec,
                    log_fn=lambda m, tag="sub": self.after(0, self._log, m, tag),
                    progress_fn=pfn)
                if not ok:
                    self.after(0, self._log, f"  ✘ Failed: {title}", "err")
            self.after(0, self._on_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self):
        self.export_btn.config(state="normal", text="▶  Export Selected")
        self.status_lbl.config(text="Done ✔")
        self.progress["value"] = 100
        self._log(f"\n✅  Export complete → {EXPORTS_DIR.resolve()}", "ok")

    def _open_folder(self):
        EXPORTS_DIR.mkdir(exist_ok=True)
        os.startfile(EXPORTS_DIR.resolve())


if __name__ == "__main__":
    ExporterApp().mainloop()