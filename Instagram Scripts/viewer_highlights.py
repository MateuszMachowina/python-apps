"""
Instagram Highlights Viewer — with emoji flags + smooth transitions
"""

import tkinter as tk
from tkinter import ttk
import json, os, sys, subprocess, re, io, urllib.request
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw, ImageFont
from datetime import datetime

try:
    import vlc
    VLC_OK = True
except ImportError:
    VLC_OK = False

# ─── Paths ───────────────────────────────────────────────────────────────────────
HIGHLIGHTS_DIR = Path("highlights")
COVER_SIZE     = 72
SIDEBAR_WIDTH  = 270

# ─── Colours ─────────────────────────────────────────────────────────────────────
BG       = "#0a0a0a"
SURFACE  = "#111111"
CARD     = "#1a1a1a"
CARD_HOV = "#222222"
ACCENT   = "#c13584"
ACCENT2  = "#833ab4"
ACCENT3  = "#fd1d1d"
TEXT     = "#f5f5f5"
SUBTEXT  = "#777777"
FONT_HEAD = ("Segoe UI", 13, "bold")
FONT_SUB  = ("Segoe UI", 9)
FONT_BTN  = ("Segoe UI", 11, "bold")

DEFAULT_PHOTO_SEC = 2


# ─── Flag PNG fetcher ────────────────────────────────────────────────────────────
_flag_cache: dict[str, Image.Image | None] = {}
FLAGS_DIR = Path(__file__).parent / "flags"

def _fetch_flag_image(cc: str, height: int = 14) -> Image.Image | None:
    cc = cc.upper().strip()
    key = f"{cc}:{height}"
    if key in _flag_cache:
        return _flag_cache[key]
    FLAGS_DIR.mkdir(exist_ok=True)
    local = FLAGS_DIR / f"{cc.lower()}.png"
    raw: bytes | None = None
    if local.exists():
        try: raw = local.read_bytes()
        except Exception: pass
    if raw is None:
        import urllib.request
        for url in [
            f"https://flagcdn.com/20x15/{cc.lower()}.png",
            f"https://flagpedia.net/data/flags/mini/{cc.lower()}.png",
        ]:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    raw = resp.read()
                local.write_bytes(raw)
                break
            except Exception: continue
    if not raw:
        _flag_cache[key] = None; return None
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
        w = max(1, int(img.width * height / img.height))
        img = img.resize((w, height), Image.LANCZOS)
        _flag_cache[key] = img; return img
    except Exception:
        _flag_cache[key] = None; return None

_CC_RE = re.compile(r'\b([A-Z]{2})\s*$')

def extract_country_code(title: str) -> tuple[str, str | None]:
    m = _CC_RE.search(title)
    if m:
        return title[:m.start()].rstrip(), m.group(1)
    return title, None

def inject_flag(title: str) -> str:
    clean, cc = extract_country_code(title)
    return f"{clean} [{cc}]" if cc else title


# ─── Pillow helpers ──────────────────────────────────────────────────────────────
def _pil_colour(hex_col: str):
    h = hex_col.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _load_emoji_font(size: int) -> ImageFont.FreeTypeFont | None:
    paths = [
        r"C:\Windows\Fonts\seguiemj.ttf",
        r"C:\Windows\Fonts\seguisym.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for fp in paths:
        if os.path.exists(fp):
            try: return ImageFont.truetype(fp, size)
            except Exception: pass
    return None


def make_circle_image(img: Image.Image, size: int) -> ImageTk.PhotoImage:
    """Crop image into a circle with anti-aliased edge (4x supersample)."""
    S = size * 4
    img  = img.convert("RGBA").resize((S, S), Image.LANCZOS)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, S-1, S-1), fill=255)
    out  = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, mask=mask)
    out  = out.resize((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(out)


def make_ring_photo(size: int, colors, bg=(0,0,0,0), thickness=2) -> ImageTk.PhotoImage:
    """Draw a smooth gradient ring via 4x supersampling. size = outer diameter."""
    S  = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx  = cy = S // 2
    n   = len(colors)
    for i, col in enumerate(colors):
        # Each colour occupies a shrinking ring
        r_out = cx - i * (thickness * 4 // n)
        r_in  = r_out - thickness * 4 // n - 1
        r_in  = max(r_in, 0)
        # parse hex colour
        h = col.lstrip("#")
        rgb = tuple(int(h[j:j+2], 16) for j in (0, 2, 4))
        d.ellipse((cx-r_out, cy-r_out, cx+r_out, cy+r_out),
                  outline=(*rgb, 255), width=thickness*4//n + 2)
    img = img.resize((size, size), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def extract_thumbnail(video_path: Path, out_path: Path) -> bool:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", str(out_path)],
            timeout=15, check=True, capture_output=True,
        )
        return out_path.exists()
    except FileNotFoundError: return False
    except Exception: return False


def _is_coll_dir(d: Path) -> bool:
    """True if d looks like a highlight folder (has media files or meta.json)."""
    return d.is_dir() and (
        (d / "meta.json").exists() or
        any(d.glob("*.mp4")) or
        any(d.glob("*.jpg"))
    )

def _load_one(d: Path, username: str = "") -> dict | None:
    mf = d / "meta.json"
    if mf.exists():
        meta = json.loads(mf.read_text(encoding="utf-8"))
    else:
        items = [{"index": i, "type": "video", "file": f.name}
                 for i, f in enumerate(sorted(d.glob("*.mp4")), 1)]
        items += [{"index": i, "type": "image", "file": f.name}
                  for i, f in enumerate(sorted(d.glob("*.jpg")), len(items)+1)]
        meta = {"title": d.name, "items": items}
    meta["_dir"]      = d
    meta["_username"] = meta.get("username") or username
    meta["_files"]    = [
        d / it["file"]
        for it in meta.get("items", [])
        if (d / it["file"]).exists()
    ]
    dt_raw = meta.get("downloaded_at")
    if dt_raw:
        try: meta["_downloaded_at"] = datetime.fromisoformat(dt_raw)
        except Exception: meta["_downloaded_at"] = datetime.min
    else:
        meta["_downloaded_at"] = datetime.min
    return meta if meta["_files"] else None

def load_collections() -> list[dict]:
    cols = []
    if not HIGHLIGHTS_DIR.exists(): return cols
    for entry in HIGHLIGHTS_DIR.iterdir():
        if not entry.is_dir(): continue
        if _is_coll_dir(entry):
            # Old flat structure: highlights/<highlight>/
            m = _load_one(entry, username="")
            if m: cols.append(m)
        else:
            # New structure: highlights/<username>/<highlight>/
            username = entry.name
            for sub in entry.iterdir():
                if _is_coll_dir(sub):
                    m = _load_one(sub, username=username)
                    if m: cols.append(m)
    cols.sort(key=lambda x: (x["_username"], x["_downloaded_at"]))
    return cols


# ─── Main window ─────────────────────────────────────────────────────────────────
class ViewerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Highlights Viewer")
        self.geometry("1180x720")
        self.minsize(900, 560)
        self.configure(bg=BG)
        self._sidebar_refs = []

        self.collections    = load_collections()
        self.active_coll    = None
        self.active_item    = 0
        self.vlc_instance   = vlc.Instance(
            "--avcodec-hw=none", "--codec=avcodec",
        ) if VLC_OK else None
        self.vlc_player     = None
        self._auto_timer    = None
        self._advancing     = False
        self._playing       = False
        self._photo_refs    = []
        self._current_photo = None
        self.photo_sec_var  = tk.StringVar(value=str(DEFAULT_PHOTO_SEC))

        self._build_ui()
        self._populate_sidebar()
        self.title_lbl.config(text="Select a highlight")
        self.counter_lbl.config(text="")

    # ── Build UI ─────────────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = tk.Frame(self, bg=SURFACE, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="✦  Highlights", bg=SURFACE, fg=TEXT,
                 font=FONT_HEAD).pack(side="left", padx=18, pady=10)

        dur = tk.Frame(hdr, bg=SURFACE)
        dur.pack(side="right", padx=16, pady=6)
        tk.Label(dur, text="Photo duration", bg=SURFACE, fg=SUBTEXT,
                 font=("Segoe UI", 8)).pack(anchor="e")
        row = tk.Frame(dur, bg=SURFACE)
        row.pack()
        tk.Button(row, text="−", command=self._dec_dur,
                  bg=CARD, fg=TEXT, activebackground=CARD_HOV, relief="flat",
                  font=("Segoe UI", 11, "bold"), cursor="hand2", width=2).pack(side="left")
        tk.Entry(row, textvariable=self.photo_sec_var,
                 bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10, "bold"), width=3, justify="center").pack(
            side="left", padx=4, ipady=3)
        tk.Label(row, text="s", bg=SURFACE, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Button(row, text="+", command=self._inc_dur,
                  bg=CARD, fg=TEXT, activebackground=CARD_HOV, relief="flat",
                  font=("Segoe UI", 11, "bold"), cursor="hand2", width=2).pack(side="left", padx=(4,0))

        tk.Button(hdr, text="↺  Reload", command=self._reload,
                  bg=CARD, fg=SUBTEXT, activebackground=CARD_HOV, activeforeground=TEXT,
                  relief="flat", font=FONT_SUB, cursor="hand2",
                  padx=10, pady=4).pack(side="right", padx=(0,8), pady=10)

        panes = tk.Frame(self, bg=BG)
        panes.pack(fill="both", expand=True)

        # ── Sidebar ──────────────────────────────────────────────────────────────
        self.sidebar = tk.Frame(panes, bg=SURFACE, width=SIDEBAR_WIDTH)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="COLLECTIONS", bg=SURFACE, fg=SUBTEXT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=16, pady=(14,6))
        self.sb_canvas = tk.Canvas(self.sidebar, bg=SURFACE, highlightthickness=0, bd=0)
        sb_scroll = ttk.Scrollbar(self.sidebar, orient="vertical",
                                  command=self.sb_canvas.yview)
        self.sb_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        self.sb_canvas.pack(side="left", fill="both", expand=True)
        self.sb_inner = tk.Frame(self.sb_canvas, bg=SURFACE)
        self._sb_win = self.sb_canvas.create_window((0,0), window=self.sb_inner, anchor="nw")
        self.sb_inner.bind("<Configure>", lambda e: self.sb_canvas.configure(
            scrollregion=self.sb_canvas.bbox("all")))
        self.sb_canvas.bind("<Configure>", lambda e: self.sb_canvas.itemconfig(
            self._sb_win, width=e.width))

        # ── Player area ──────────────────────────────────────────────────────────
        pw = tk.Frame(panes, bg=BG)
        pw.pack(side="left", fill="both", expand=True)

        # ── Story header row (NEW) ────────────────────────────────────────────────
        story_hdr = tk.Frame(pw, bg=BG, height=52)
        story_hdr.pack(fill="x", padx=12, pady=(8, 0))
        story_hdr.pack_propagate(False)

        # Avatar circle (32px) with gradient ring
        av_size = 36
        self.hdr_avatar_cv = tk.Canvas(story_hdr, bg=BG, width=av_size, height=av_size,
                                        highlightthickness=0)
        self.hdr_avatar_cv.pack(side="left", pady=8)

        # Title + counter on one line
        hdr_text = tk.Frame(story_hdr, bg=BG)
        hdr_text.pack(side="left", padx=(10, 0), pady=8)

        title_row = tk.Frame(hdr_text, bg=BG)
        title_row.pack(anchor="w")

        self.title_lbl = tk.Label(title_row, text="", bg=BG, fg=TEXT, font=FONT_HEAD,
                                   anchor="w")
        self.title_lbl.pack(side="left")

        self.counter_lbl = tk.Label(title_row, text="", bg=BG, fg=SUBTEXT,
                                     font=("Segoe UI", 11), anchor="w")
        self.counter_lbl.pack(side="left", padx=(8, 0))

        # ── Progress strips ──────────────────────────────────────────────────────
        self.strip_frame = tk.Frame(pw, bg=BG, height=3)
        self.strip_frame.pack(fill="x", padx=20, pady=(6, 6))

        # ── Media canvas ─────────────────────────────────────────────────────────
        self.vid_canvas = tk.Canvas(pw, bg="#000000", highlightthickness=0, cursor="hand2")
        self.vid_canvas.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        self.vid_canvas.bind("<Button-1>", self._on_canvas_click)

        # ── Controls ─────────────────────────────────────────────────────────────
        ctrl = tk.Frame(pw, bg=BG, pady=8)
        ctrl.pack(fill="x", padx=20)
        bcfg = dict(bg=CARD, fg=TEXT, activebackground=CARD_HOV, activeforeground=TEXT,
                    relief="flat", font=FONT_BTN, cursor="hand2", padx=18, pady=8)
        tk.Button(ctrl, text="◀  Prev", command=self._prev, **bcfg).pack(side="left")
        self.play_btn = tk.Button(ctrl, text="⏸  Pause", command=self._toggle_pause,
                                  bg=ACCENT, fg="white", activebackground=ACCENT2,
                                  activeforeground="white", relief="flat",
                                  font=FONT_BTN, cursor="hand2", padx=18, pady=8)
        self.play_btn.pack(side="left", padx=10)
        tk.Button(ctrl, text="Next  ▶", command=self._next, **bcfg).pack(side="left")
        self.seek_var = tk.DoubleVar()
        sty = ttk.Style(); sty.theme_use("clam")
        sty.configure("IG.Horizontal.TScale", background=BG, troughcolor=SURFACE,
                      slidercolor=ACCENT, troughrelief="flat")
        self.seek_slider = ttk.Scale(ctrl, from_=0, to=100, orient="horizontal",
                                     variable=self.seek_var, command=self._on_seek,
                                     style="IG.Horizontal.TScale")
        self.seek_slider.pack(side="left", fill="x", expand=True, padx=(20,0))
        self.time_lbl = tk.Label(ctrl, text="0:00 / 0:00", bg=BG, fg=SUBTEXT, font=FONT_SUB)
        self.time_lbl.pack(side="left", padx=(10,0))

        self.bind("<Right>",  lambda e: self._next())
        self.bind("<Left>",   lambda e: self._prev())
        self.bind("<space>",  lambda e: self._toggle_pause())
        self.bind("<Escape>", lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll()

    # ── Story header update (NEW) ─────────────────────────────────────────────────
    def _update_story_header(self):
        """Refresh the avatar, title and counter in the story header row."""
        self.hdr_avatar_cv.delete("all")
        if self.active_coll is None:
            self.title_lbl.config(text="Select a highlight")
            self.counter_lbl.config(text="")
            return

        coll  = self.collections[self.active_coll]
        files = coll["_files"]
        raw   = coll.get("title", "Untitled")
        clean, cc = extract_country_code(raw)
        display = clean + (f"  [{cc}]" if cc else "")
        self.title_lbl.config(text=display)
        self.counter_lbl.config(text=f"{self.active_item + 1} / {len(files)}")

        # Draw gradient ring + circular avatar
        av = self.hdr_avatar_cv
        s  = int(av.cget("width"))
        cx = cy = s // 2
        # Smooth ring
        ring_ph = make_ring_photo(s, [ACCENT3, ACCENT, ACCENT2], thickness=2)
        self._photo_refs.append(ring_ph)
        av.create_image(0, 0, image=ring_ph, anchor="nw")

        thumb = self._get_cover_thumb(coll)
        if thumb:
            inner = s - 6
            ph = make_circle_image(thumb, inner)
            self._photo_refs.append(ph)
            av.create_image(cx, cy, image=ph)

    # ── Duration helpers ─────────────────────────────────────────────────────────
    def _get_photo_sec(self):
        try: return max(1, min(int(self.photo_sec_var.get()), 60))
        except ValueError: return DEFAULT_PHOTO_SEC
    def _inc_dur(self): self.photo_sec_var.set(str(self._get_photo_sec() + 1))
    def _dec_dur(self): self.photo_sec_var.set(str(max(1, self._get_photo_sec() - 1)))

    # ── Sidebar ──────────────────────────────────────────────────────────────────
    def _populate_sidebar(self):
        for w in self.sb_inner.winfo_children():
            w.destroy()
        old_refs = self._photo_refs
        self._photo_refs = []
        if not self.collections:
            tk.Label(self.sb_inner, text="No highlights.\nRun downloader first.",
                     bg=SURFACE, fg=SUBTEXT, font=FONT_SUB,
                     justify="center", wraplength=230).pack(pady=30, padx=10)
            return

        # Group by username — show section headers when multiple accounts present
        accounts = []
        seen = {}
        for coll in self.collections:
            u = coll.get("_username", "")
            if u not in seen:
                seen[u] = True
                accounts.append(u)
        multi_account = len(accounts) > 1 or (len(accounts) == 1 and accounts[0])

        last_user = None
        for idx, coll in enumerate(self.collections):
            u = coll.get("_username", "")
            if multi_account and u != last_user:
                last_user = u
                lbl_text = f"@{u}" if u else "unknown"
                tk.Label(self.sb_inner, text=lbl_text,
                         bg=SURFACE, fg=ACCENT,
                         font=("Segoe UI", 9, "bold"),
                         anchor="w").pack(fill="x", padx=16, pady=(10, 2))
                tk.Frame(self.sb_inner, bg="#2a2a2a", height=1).pack(fill="x", padx=10)
            self._make_sidebar_item(idx, coll)
        del old_refs

    def _make_sidebar_item(self, idx: int, coll: dict):
        frame = tk.Frame(self.sb_inner, bg=SURFACE, cursor="hand2")
        frame.pack(fill="x", pady=1)

        def hover_on(e, f=frame):
            f.config(bg=CARD_HOV)
            for c in f.winfo_children(): c.config(bg=CARD_HOV)
        def hover_off(e, f=frame):
            f.config(bg=SURFACE)
            for c in f.winfo_children(): c.config(bg=SURFACE)
        def click(e, i=idx): self._select_collection(i)

        frame.bind("<Enter>", hover_on)
        frame.bind("<Leave>", hover_off)
        frame.bind("<Button-1>", click)

        cv_size = COVER_SIZE + 8   # extra room for smooth ring
        cover_canvas = tk.Canvas(frame, bg=SURFACE, width=cv_size, height=cv_size,
                                  highlightthickness=0)
        cover_canvas.pack(side="left", padx=(10,8), pady=8)
        cover_canvas.bind("<Button-1>", click)
        cover_canvas.bind("<Enter>", hover_on)
        cover_canvas.bind("<Leave>", hover_off)
        # Smooth gradient ring via PIL supersampling
        ring_ph = make_ring_photo(cv_size, [ACCENT3, ACCENT, ACCENT2], thickness=3)
        self._sidebar_refs.append(ring_ph)
        cover_canvas.create_image(0, 0, image=ring_ph, anchor="nw")
        thumb = self._get_cover_thumb(coll)
        if thumb:
            photo = make_circle_image(thumb, COVER_SIZE)
            self._sidebar_refs.append(photo)
            cover_canvas.create_image(cv_size//2, cv_size//2, image=photo)

        tf = tk.Frame(frame, bg=SURFACE)
        tf.pack(side="left", fill="x", expand=True, pady=8, padx=(0,8))
        tf.bind("<Button-1>", click)
        tf.bind("<Enter>", hover_on)
        tf.bind("<Leave>", hover_off)

        raw_title = coll.get("title", "Untitled")
        clean_title, country_code = extract_country_code(raw_title)
        n = len(coll.get("_files", []))

        max_title_w = SIDEBAR_WIDTH - cv_size - 28
        title_img_normal = self._render_title_pil(clean_title, max_title_w,
                                                   bg=SURFACE, country_code=None)
        title_img_hover  = self._render_title_pil(clean_title, max_title_w,
                                                   bg=CARD_HOV, country_code=None)
        if title_img_normal and title_img_hover:
            ph_normal = ImageTk.PhotoImage(title_img_normal)
            ph_hover  = ImageTk.PhotoImage(title_img_hover)
            self._sidebar_refs.extend([ph_normal, ph_hover])
            title_canvas = tk.Canvas(tf, bg=SURFACE, highlightthickness=0,
                                     width=title_img_normal.width,
                                     height=title_img_normal.height)
            img_id = title_canvas.create_image(0, 0, image=ph_normal, anchor="nw")
            title_canvas.pack(anchor="w")
            title_canvas.bind("<Button-1>", click)
            title_canvas.bind("<Enter>", lambda e, tc=title_canvas, iid=img_id,
                              ph=ph_hover, col=CARD_HOV: (
                                  tc.config(bg=col), tc.itemconfig(iid, image=ph),
                                  hover_on(e)))
            title_canvas.bind("<Leave>", lambda e, tc=title_canvas, iid=img_id,
                              ph=ph_normal, col=SURFACE: (
                                  tc.config(bg=col), tc.itemconfig(iid, image=ph),
                                  hover_off(e)))
            if country_code:
                self._fetch_flag_async(clean_title, country_code, max_title_w,
                                       title_canvas, img_id)
        else:
            tk.Label(tf, text=clean_title + (f" [{country_code}]" if country_code else ""),
                     bg=SURFACE, fg=TEXT,
                     font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")

        cl = tk.Label(tf, text=f"{n} item{'s' if n!=1 else ''}",
                      bg=SURFACE, fg=SUBTEXT, font=FONT_SUB, anchor="w")
        cl.pack(fill="x")
        cl.bind("<Button-1>", click)
        cl.bind("<Enter>", hover_on)
        cl.bind("<Leave>", hover_off)

    def _render_title_pil(self, text: str, max_w: int, bg: str = SURFACE,
                          country_code: str | None = None) -> Image.Image | None:
        font = _load_emoji_font(14)
        if font is None: return None
        dummy = Image.new("RGBA", (1, 1))
        bb    = ImageDraw.Draw(dummy).textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0] + 4, bb[3] - bb[1] + 4
        flag_img  = _fetch_flag_image(country_code) if country_code else None
        gap       = 6 if flag_img else 0
        flag_w    = flag_img.width if flag_img else 0
        total_w   = max(tw + gap + flag_w, max_w)
        bg_rgb = _pil_colour(bg)
        img = Image.new("RGB", (total_w, th), bg_rgb)
        ImageDraw.Draw(img).text((2, 2), text, font=font, fill=_pil_colour(TEXT))
        if flag_img:
            fy = max(0, (th - flag_img.height) // 2)
            flag_rgb = Image.new("RGB", flag_img.size, bg_rgb)
            flag_rgb.paste(flag_img, mask=flag_img.split()[3])
            img.paste(flag_rgb, (tw + gap, fy))
        return img

    def _fetch_flag_async(self, text: str, country_code: str, max_w: int,
                          canvas: tk.Canvas, img_id: int):
        import threading
        def worker():
            flag = _fetch_flag_image(country_code)
            if flag is None: return
            img_n = self._render_title_pil(text, max_w, bg=SURFACE,  country_code=country_code)
            img_h = self._render_title_pil(text, max_w, bg=CARD_HOV, country_code=country_code)
            if img_n and img_h:
                self.after(0, lambda: self._apply_flag_images(canvas, img_id, img_n, img_h))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_flag_images(self, canvas: tk.Canvas, img_id: int,
                           img_normal: Image.Image, img_hover: Image.Image):
        try:
            if not canvas.winfo_exists(): return
        except Exception: return
        ph_n = ImageTk.PhotoImage(img_normal)
        ph_h = ImageTk.PhotoImage(img_hover)
        self._sidebar_refs.extend([ph_n, ph_h])
        canvas.config(width=img_normal.width, height=img_normal.height)
        canvas.itemconfig(img_id, image=ph_n)
        canvas.bind("<Enter>", lambda e, tc=canvas, iid=img_id, ph=ph_h, col=CARD_HOV: (
            tc.config(bg=col), tc.itemconfig(iid, image=ph)))
        canvas.bind("<Leave>", lambda e, tc=canvas, iid=img_id, ph=ph_n, col=SURFACE: (
            tc.config(bg=col), tc.itemconfig(iid, image=ph)))

    def _get_cover_thumb(self, coll: dict):
        cover_name = coll.get("cover")
        if cover_name:
            cover_path = coll["_dir"] / cover_name
            if cover_path.exists():
                try:
                    img = Image.open(cover_path); img.load(); return img.copy()
                except Exception: pass
        files = coll.get("_files", [])
        if not files: return None
        d = coll["_dir"]
        def _open(path):
            try:
                img = Image.open(path); img.load(); return img.copy()
            except Exception: return None
        first = files[0]
        if first.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            img = _open(first)
            if img: return img
        if first.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv"):
            tp = first.with_suffix(".thumb.jpg")
            if not tp.exists(): extract_thumbnail(first, tp)
            if tp.exists():
                img = _open(tp)
                if img: return img
        for jpg in sorted(d.glob("*.jpg")):
            img = _open(jpg)
            if img: return img
        return None

    # ── Collection select ────────────────────────────────────────────────────────
    def _select_collection(self, idx: int):
        self._stop_vlc()
        self._cancel_auto()
        self._playing    = True
        self.active_coll = idx
        self.active_item = 0
        self._update_strips()
        self._update_story_header()
        self._play_current()
        self._highlight_sidebar(idx)

    def _highlight_sidebar(self, idx: int):
        for i, f in enumerate(self.sb_inner.winfo_children()):
            col = CARD if i == idx else SURFACE
            f.config(bg=col)
            for c in f.winfo_children(): c.config(bg=col)

    def _update_strips(self):
        for w in self.strip_frame.winfo_children(): w.destroy()
        if self.active_coll is None: return
        files = self.collections[self.active_coll]["_files"]
        for i in range(len(files)):
            col = ACCENT if i < self.active_item else (TEXT if i == self.active_item else CARD)
            tk.Frame(self.strip_frame, bg=col, height=3).pack(
                side="left", fill="x", expand=True, padx=1)

    # ── Playback ─────────────────────────────────────────────────────────────────
    def _play_current(self):
        if self.active_coll is None: return
        coll  = self.collections[self.active_coll]
        files = coll["_files"]
        if not files or self.active_item >= len(files): return
        path  = files[self.active_item]
        self._update_story_header()   # keep counter in sync
        self._update_strips()
        if path.suffix.lower() in (".mp4",".mov",".avi",".mkv"):
            self._play_video(path)
        else:
            self._show_image(path)

    def _play_video(self, path: Path):
        if not VLC_OK or self.vlc_instance is None:
            self._show_no_vlc(); return
        self._stop_vlc()
        self.play_btn.config(text="⏸  Pause")
        self.update_idletasks()
        media  = self.vlc_instance.media_new(str(path))
        player = self.vlc_instance.media_player_new()
        player.set_media(media)
        player.set_hwnd(self.vid_canvas.winfo_id())
        self.vlc_player = player
        player.play()
        self.after(120, self._clear_photo_overlay)

    def _clear_photo_overlay(self):
        self.vid_canvas.delete("img_overlay")
        self._current_photo = None

    def _show_image(self, path: Path):
        try:
            img = Image.open(path); img.load()
            self.update_idletasks()
            w = self.vid_canvas.winfo_width()  or 640
            h = self.vid_canvas.winfo_height() or 480
            img.thumbnail((w, h), Image.LANCZOS)
            new_photo = ImageTk.PhotoImage(img)
        except Exception as e:
            self.vid_canvas.delete("all")
            self.vid_canvas.create_text(320, 240,
                text=f"Cannot display image:\n{e}", fill=TEXT, font=FONT_SUB)
            return
        self.vid_canvas.create_image(w//2, h//2, image=new_photo, tags="img_overlay")
        self.vid_canvas.delete("img_overlay_old")
        self.vid_canvas.addtag_withtag("img_overlay_old", "img_overlay")
        self._current_photo = new_photo
        self._photo_refs.append(new_photo)
        if len(self._photo_refs) > 20:
            self._photo_refs = self._photo_refs[-10:]
        self._stop_vlc()
        self.play_btn.config(text="▶  Play")
        self._cancel_auto()
        if self._playing:
            ms = self._get_photo_sec() * 1000
            self.after(50, lambda: self._start_photo_timer(ms))

    def _start_photo_timer(self, ms: int):
        if self._current_photo is None: return
        self._cancel_auto()
        self._auto_timer = self.after(ms, self._next)

    def _show_no_vlc(self):
        self.vid_canvas.delete("all")
        self.vid_canvas.create_text(400, 300,
            text="python-vlc not installed.\npip install python-vlc",
            fill=ACCENT, font=FONT_HEAD, justify="center")

    def _stop_vlc(self):
        if self.vlc_player:
            try: self.vlc_player.stop()
            except Exception: pass
            try: self.vlc_player.release()
            except Exception: pass
            self.vlc_player = None

    def _cancel_auto(self):
        if self._auto_timer:
            self.after_cancel(self._auto_timer); self._auto_timer = None

    # ── Navigation ───────────────────────────────────────────────────────────────
    def _next(self):
        if self.active_coll is None or self._advancing: return
        self._advancing = True
        self._cancel_auto()
        try:
            coll = self.collections[self.active_coll]
            if self.active_item < len(coll["_files"]) - 1:
                self.active_item += 1; self._play_current()
            elif self.active_coll < len(self.collections) - 1:
                self._select_collection(self.active_coll + 1)
        finally:
            self.after(300, lambda: setattr(self, "_advancing", False))

    def _prev(self):
        if self.active_coll is None: return
        self._cancel_auto()
        if self.active_item > 0:
            self.active_item -= 1; self._play_current()
        elif self.active_coll > 0:
            self._select_collection(self.active_coll - 1)

    def _toggle_pause(self):
        if self.vlc_player:
            self.vlc_player.pause()
            paused = VLC_OK and self.vlc_player.get_state() == vlc.State.Paused
            self.play_btn.config(text="▶  Play" if paused else "⏸  Pause")
        elif self._current_photo is not None:
            if not self._playing or self._auto_timer is None:
                self._playing = True
                self.play_btn.config(text="⏸  Pause")
                self._cancel_auto()
                self._auto_timer = self.after(self._get_photo_sec()*1000, self._next)
            else:
                self._cancel_auto()
                self.play_btn.config(text="▶  Play")

    def _on_canvas_click(self, event):
        w = self.vid_canvas.winfo_width()
        (self._prev if event.x < w//2 else self._next)()

    def _on_seek(self, val):
        if self.vlc_player:
            self.vlc_player.set_position(float(val)/100.0)

    # ── Poll loop ────────────────────────────────────────────────────────────────
    def _poll(self):
        if self.vlc_player:
            try:
                pos = self.vlc_player.get_position()
                length = self.vlc_player.get_length()
                t = self.vlc_player.get_time()
                if pos >= 0: self.seek_var.set(pos*100)
                def ms(x):
                    s = max(0,x)//1000; return f"{s//60}:{s%60:02d}"
                self.time_lbl.config(text=f"{ms(t)} / {ms(length)}")
                if VLC_OK and self.vlc_player.get_state() == vlc.State.Ended:
                    self._stop_vlc(); self.after(80, self._next)
            except Exception: pass
        self.after(500, self._poll)

    def _reload(self):
        self._stop_vlc(); self._cancel_auto()
        self.active_coll = None; self.active_item = 0
        self.collections = load_collections()
        self._populate_sidebar()
        self._update_story_header()

    def _on_close(self):
        self._stop_vlc(); self.destroy()


if __name__ == "__main__":
    if not HIGHLIGHTS_DIR.exists():
        r = tk.Tk(); r.withdraw()
        import tkinter.messagebox as mb
        mb.showinfo("No highlights", "Run downloader.py first.")
        r.destroy(); sys.exit(0)
    ViewerApp().mainloop()
