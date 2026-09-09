"""
Instagram Highlights → MP4 Exporter
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading, subprocess, json, os, sys, shutil, tempfile, argparse, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import re

# ── Paths ─────────────────────────────────────────────────────────────────────
HIGHLIGHTS_DIR = Path("highlights")
EXPORTS_DIR    = Path("exports")

# ── Output spec ───────────────────────────────────────────────────────────────
W, H       = 1080, 1920
FPS        = 30
FADE_SEC   = 0.3          # crossfade duration
FADE_F     = int(FPS * FADE_SEC)

# ── UI overlay constants ───────────────────────────────────────────────────────
# All of these are modeled off the real Instagram story viewer at a 1080×1920
# (9:16) canvas, so the proportions match what you'd see on an actual phone.

# Progress bar row
BAR_Y            = 50     # top edge of the bar row (below the phone's safe area)
BAR_H            = 3
BAR_GAP          = 5
BAR_PAD_X        = 12
BAR_RADIUS       = 1

# Avatar + username row
AVATAR_R         = 34     # 68px diameter — IG's on-screen avatar is ~6-7% of width
AVATAR_GAP_BELOW = 14      # gap between the bar row and the avatar
AVATAR_Y         = BAR_Y + BAR_H + AVATAR_GAP_BELOW + AVATAR_R
AVATAR_CX        = BAR_PAD_X + AVATAR_R

TEXT_GAP         = 14      # gap between avatar and username
TEXT_X           = AVATAR_CX + AVATAR_R + TEXT_GAP

RIGHT_PAD_X      = BAR_PAD_X
ICON_GAP         = 30      # gap between "•••" and the close "X"

GRAD_H           = 230     # top dark gradient, for text/icon legibility

# Toggles (also exposed in the GUI and as CLI flags)
SHOW_COUNTER_DEFAULT   = True    # note: real IG highlights don't normally show this
COUNTER_GAP_Y          = 11     # vertical gap between username and the "n/n" line below it
TITLE_Y_OFFSET         = 6       # nudge the whole username (+counter) block down a few px; negative = up
SHOW_REPLY_BAR_DEFAULT = False    # bottom "Send message" bar, as seen viewing someone else's highlight
KEEP_AUDIO_DEFAULT     = True     # keep each video clip's original audio, mixed in at the right offset

# Bottom reply bar
BOTTOM_SAFE      = 54
PILL_H           = 74
ICON_R           = 16
BOTTOM_GRAD_H    = 260

# ── Colours ──────────────────────────────────────────────────────────────────
TEXT_COL   = (245, 245, 245)
SUBTEXT    = (220, 220, 220)

# ── GUI colours ───────────────────────────────────────────────────────────────
GBG    = "#0a0a0a"
GSURF  = "#161616"
GCARD  = "#1e1e1e"
GACC   = "#c13584"
GACC2  = "#833ab4"
GTXT   = "#f0f0f0"
GSUB   = "#888888"
GSUCC  = "#2ecc71"
GERR   = "#e74c3c"
GGOLD  = "#f5a623"


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _font(size, weight="regular"):
    """
    weight: "regular" | "medium" | "bold"
    Instagram's own typeface isn't redistributable, so we match it with the
    closest-looking system font available — SF Pro / Segoe UI / Helvetica /
    DejaVu Sans are all near-identical grotesque sans faces at these sizes.
    "medium" approximates IG's semibold username weight.
    """
    candidates = {
        "bold": [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "medium": [
            r"C:\Windows\Fonts\seguisb.ttf",     # Segoe UI Semibold (Win10/11)
            r"C:\Windows\Fonts\segoeui.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",   # closest match without a true medium weight
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "regular": [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ],
    }
    for p in candidates.get(weight, candidates["regular"]):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def _ffmpeg(*args, log_fn=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error"] + list(args)
    if log_fn:
        log_fn("  $ " + " ".join(str(a) for a in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error:\n{result.stderr[-800:]}")
    return result

def _check_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

_CC_RE = re.compile(r'\b([A-Z]{2})\s*$')
def clean_title(title: str) -> str:
    m = _CC_RE.search(title)
    return title[:m.start()].rstrip() if m else title

def _text_shadow(d, xy, text, font, fill, shadow_alpha=110, offset=(0, 2)):
    """Draw text with a soft, cheap drop shadow — IG renders top-bar text with
    a subtle shadow so it reads over any photo/video."""
    x, y = xy
    ox, oy = offset
    d.text((x + ox, y + oy), text, font=font, fill=(0, 0, 0, shadow_alpha))
    d.text((x, y), text, font=font, fill=fill)

def _fit_title(d, text, font, max_width):
    """Truncate with an ellipsis so long usernames never collide with the
    top-right icons, same as the real app."""
    if d.textlength(text, font=font) <= max_width:
        return text
    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if d.textlength(text[:mid] + ell, font=font) <= max_width:
            lo = mid
        else:
            hi = mid - 1
    return (text[:lo].rstrip() + ell) if lo > 0 else ell


# ══════════════════════════════════════════════════════════════════════════════
#  Overlay frame builder
# ══════════════════════════════════════════════════════════════════════════════

def _make_top_gradient() -> Image.Image:
    grad = Image.new("RGBA", (W, GRAD_H))
    for y in range(GRAD_H):
        alpha = int(190 * (1 - y / GRAD_H) ** 1.6)
        row = Image.new("RGBA", (W, 1), (0, 0, 0, alpha))
        grad.paste(row, (0, y))
    return grad

def _make_bottom_gradient() -> Image.Image:
    grad = Image.new("RGBA", (W, BOTTOM_GRAD_H))
    for y in range(BOTTOM_GRAD_H):
        alpha = int(170 * (y / BOTTOM_GRAD_H) ** 1.6)
        row = Image.new("RGBA", (W, 1), (0, 0, 0, alpha))
        grad.paste(row, (0, y))
    return grad

_TOP_GRAD = None
_BOTTOM_GRAD = None

def get_top_gradient():
    global _TOP_GRAD
    if _TOP_GRAD is None:
        _TOP_GRAD = _make_top_gradient()
    return _TOP_GRAD

def get_bottom_gradient():
    global _BOTTOM_GRAD
    if _BOTTOM_GRAD is None:
        _BOTTOM_GRAD = _make_bottom_gradient()
    return _BOTTOM_GRAD

def _draw_progress_bars(d, n_items: int, current_idx: int, progress_frac: float = 1.0):
    usable = W - 2 * BAR_PAD_X - BAR_GAP * (n_items - 1)
    bar_w  = max(3, usable // n_items)
    for i in range(n_items):
        x0 = BAR_PAD_X + i * (bar_w + BAR_GAP)
        x1 = x0 + bar_w
        y0, y1 = BAR_Y, BAR_Y + BAR_H
        d.rounded_rectangle([x0, y0, x1, y1], radius=BAR_RADIUS, fill=(255, 255, 255, 80))
        if i < current_idx:
            fill_x = x1
        elif i == current_idx:
            fill_x = int(x0 + (x1 - x0) * progress_frac)
        else:
            fill_x = x0
        if fill_x > x0:
            d.rounded_rectangle([x0, y0, fill_x, y1], radius=BAR_RADIUS, fill=(255, 255, 255, 240))

def _draw_avatar(overlay: Image.Image, thumb: Image.Image | None, cx: int, cy: int, r: int):
    """Paste a circular-cropped avatar with a soft drop shadow and a thin
    plain border. Note: the colourful gradient ring only ever appears on the
    profile-grid/tray thumbnail — inside the story/highlight viewer itself
    Instagram shows a plain avatar, so that's what we replicate here."""
    shadow = Image.new("RGBA", (r * 2 + 20, r * 2 + 20), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([10, 12, 10 + r * 2, 12 + r * 2], fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    overlay.paste(shadow, (cx - r - 10, cy - r - 10), shadow)

    size = r * 2
    if thumb is not None:
        img = thumb.convert("RGBA").resize((size, size), Image.LANCZOS)
    else:
        img = Image.new("RGBA", (size, size), (120, 120, 130, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    circle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circle.paste(img, mask=mask)
    overlay.paste(circle, (cx - r, cy - r), circle)

    ImageDraw.Draw(overlay).ellipse([cx - r, cy - r, cx + r, cy + r],
                                    outline=(255, 255, 255, 90), width=2)

def _draw_verified_badge(d, cx, cy, r=11):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(51, 153, 255, 255))
    pts = [(cx - r * 0.5, cy), (cx - r * 0.1, cy + r * 0.4), (cx + r * 0.55, cy - r * 0.4)]
    d.line(pts, fill=(255, 255, 255, 255), width=3, joint="curve")

def _draw_close_icon(d, cx, cy, size=12, color=(255, 255, 255, 235)):
    d.line([cx - size, cy - size, cx + size, cy + size], fill=color, width=2)
    d.line([cx - size, cy + size, cx + size, cy - size], fill=color, width=2)

def _draw_more_icon(d, cx, cy, r=2.6, gap=10, color=(255, 255, 255, 235)):
    for i in (-1, 0, 1):
        x = cx + i * gap
        d.ellipse([x - r, cy - r, x + r, cy + r], fill=color)

def _draw_heart_icon(d, cx, cy, scale=15, color=(255, 255, 255, 235), width=2):
    pts = []
    for i in range(61):
        t = math.pi * 2 * i / 60
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * scale / 16, cy + y * scale / 16))
    d.line(pts, fill=color, width=width, joint="curve")

def _draw_share_icon(d, cx, cy, size=16, color=(255, 255, 255, 235), width=2):
    """Simplified paper-plane / send silhouette."""
    p1 = (cx - size, cy - size * 0.55)
    p2 = (cx + size, cy)
    p3 = (cx - size, cy + size * 0.55)
    p4 = (cx - size * 0.25, cy)
    d.line([p1, p2, p3, p4, p1], fill=color, width=width, joint="curve")

def _draw_reply_bar(overlay: Image.Image):
    """The 'Send message' pill + heart/share icons seen at the bottom when
    viewing someone else's story or highlight."""
    d = ImageDraw.Draw(overlay)
    right_x2 = W - RIGHT_PAD_X - 6
    heart_cx = right_x2 - ICON_R
    share_cx = heart_cx - ICON_R * 2 - 26

    pill_x1 = BAR_PAD_X + 6
    pill_x2 = share_cx - ICON_R - 22
    pill_y2 = H - BOTTOM_SAFE
    pill_y1 = pill_y2 - PILL_H
    pill_cy = (pill_y1 + pill_y2) // 2

    d.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2],
                        radius=PILL_H // 2, outline=(255, 255, 255, 180), width=2)
    fn = _font(30, "regular")
    bbox = d.textbbox((0, 0), "Send message", font=fn)
    th = bbox[3] - bbox[1]
    d.text((pill_x1 + 30, pill_cy - th // 2 - bbox[1]), "Send message",
           font=fn, fill=(255, 255, 255, 220))

    _draw_heart_icon(d, heart_cx, pill_cy)
    _draw_share_icon(d, share_cx, pill_cy)

def build_overlay_frame(n_items: int, current_idx: int, title: str,
                         thumb: Image.Image | None,
                         progress_frac: float = 1.0,
                         verified: bool = False,
                         show_counter: bool = SHOW_COUNTER_DEFAULT,
                         show_reply_bar: bool = SHOW_REPLY_BAR_DEFAULT) -> Image.Image:
    """
    Returns a full 1080×1920 RGBA overlay image with:
      - top gradient + progress bars + avatar + username (+ verified badge)
      - "•••" and close "X" icons
      - optional bottom "Send message" reply bar
    Composite this onto the media frame.
    """
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    grad = get_top_gradient()
    overlay.paste(grad, (0, 0), grad)
    if show_reply_bar:
        bgrad = get_bottom_gradient()
        overlay.paste(bgrad, (0, H - BOTTOM_GRAD_H), bgrad)

    d = ImageDraw.Draw(overlay)
    _draw_progress_bars(d, n_items, current_idx, progress_frac)

    _draw_avatar(overlay, thumb, AVATAR_CX, AVATAR_Y, AVATAR_R)

    d = ImageDraw.Draw(overlay)
    close_cx = W - RIGHT_PAD_X - 13
    more_cx  = close_cx - ICON_GAP - 13
    max_text_w = more_cx - 18 - TEXT_X
    badge_w = 30 if verified else 0

    display  = _fit_title(d, clean_title(title), _font(34, "medium"), max_text_w - badge_w)
    fn_title = _font(34, "medium")
    tb = d.textbbox((0, 0), display, font=fn_title)
    title_h = tb[3] - tb[1]

    if show_counter:
        counter = f"{current_idx + 1}/{n_items}"
        fn_sub = _font(24, "regular")
        sb = d.textbbox((0, 0), counter, font=fn_sub)
        sub_h = sb[3] - sb[1]
        block_h = title_h + COUNTER_GAP_Y + sub_h
        top = AVATAR_Y - block_h // 2 + TITLE_Y_OFFSET
        ty = top - tb[1]
        sy = top + title_h + COUNTER_GAP_Y - sb[1]
        _text_shadow(d, (TEXT_X, ty), display, fn_title, (*TEXT_COL, 245))
        _text_shadow(d, (TEXT_X, sy), counter, fn_sub, (*SUBTEXT, 220))
    else:
        ty = AVATAR_Y - title_h // 2 - tb[1] + TITLE_Y_OFFSET
        _text_shadow(d, (TEXT_X, ty), display, fn_title, (*TEXT_COL, 245))

    if verified:
        tw = d.textlength(display, font=fn_title)
        title_center_y = ty + tb[1] + title_h / 2
        _draw_verified_badge(d, TEXT_X + tw + 18, int(title_center_y))

    _draw_more_icon(d, more_cx, AVATAR_Y)
    _draw_close_icon(d, close_cx, AVATAR_Y)

    if show_reply_bar:
        _draw_reply_bar(overlay)

    return overlay


# ══════════════════════════════════════════════════════════════════════════════
#  Frame-sequence builder (PIL → PNG temp frames)
# ══════════════════════════════════════════════════════════════════════════════

def _fit_frame(media_path: Path) -> Image.Image:
    """Open an image and letterbox/pillarbox it to W×H."""
    img = Image.open(media_path).convert("RGB")
    img.load()
    iw, ih = img.size
    scale  = min(W / iw, H / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img    = img.resize((nw, nh), Image.LANCZOS)
    out    = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(img, ((W - nw) // 2, (H - nh) // 2))
    return out

def _composite(base: Image.Image, overlay: Image.Image) -> Image.Image:
    out = base.convert("RGBA")
    out.paste(overlay, (0, 0), overlay)
    return out.convert("RGB")

def _save_frame(img: Image.Image, path: Path):
    img.save(path, "JPEG", quality=88)


def render_image_clip(media_path: Path, duration_sec: float,
                      n_items: int, item_idx: int,
                      title: str, thumb: Image.Image | None,
                      out_dir: Path, start_frame: int,
                      log_fn=None, verified=False,
                      show_counter=SHOW_COUNTER_DEFAULT,
                      show_reply_bar=SHOW_REPLY_BAR_DEFAULT) -> int:
    """
    Render <duration_sec> worth of frames for a still image.
    Returns number of frames written.
    """
    n_frames = int(duration_sec * FPS)
    base     = _fit_frame(media_path)
    frame_i  = start_frame
    for f in range(n_frames):
        frac    = (f + 1) / n_frames
        overlay = build_overlay_frame(n_items, item_idx, title, thumb, frac,
                                      verified, show_counter, show_reply_bar)
        comp    = _composite(base, overlay)
        _save_frame(comp, out_dir / f"f{frame_i:06d}.jpg")
        frame_i += 1
    return n_frames


def render_video_clip_frames(video_path: Path, n_items: int, item_idx: int,
                              title: str, thumb: Image.Image | None,
                              out_dir: Path, start_frame: int,
                              tmp_dir: Path, log_fn=None, verified=False,
                              show_counter=SHOW_COUNTER_DEFAULT,
                              show_reply_bar=SHOW_REPLY_BAR_DEFAULT) -> int:
    """
    Extract all frames from a video, composite overlay, write to out_dir.
    Frames are resampled to FPS on extraction (via -r) so the exported clip's
    visual duration always matches its real playback duration — this also
    keeps the original audio in sync when it's muxed back in afterwards.
    Returns number of frames written.
    """
    raw_dir = tmp_dir / f"raw_{item_idx}"
    raw_dir.mkdir(exist_ok=True)
    if log_fn:
        log_fn(f"    extracting video frames…")
    _ffmpeg(
        "-i", str(video_path),
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
               f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
        "-r", str(FPS),
        "-q:v", "3",
        str(raw_dir / "v%06d.jpg"),
        log_fn=None,
    )
    raw_frames = sorted(raw_dir.glob("v*.jpg"))
    n_frames   = len(raw_frames)
    if n_frames == 0:
        return 0

    frame_i = start_frame
    for fi, rf in enumerate(raw_frames):
        frac    = (fi + 1) / n_frames
        base    = Image.open(rf).convert("RGB")
        base.load()
        overlay = build_overlay_frame(n_items, item_idx, title, thumb, frac,
                                      verified, show_counter, show_reply_bar)
        comp    = _composite(base, overlay)
        _save_frame(comp, out_dir / f"f{frame_i:06d}.jpg")
        frame_i += 1

    shutil.rmtree(raw_dir, ignore_errors=True)
    return n_frames


def render_fade_frames(img_a: Image.Image, img_b: Image.Image,
                       n_items: int, idx_a: int, idx_b: int,
                       title: str, thumb: Image.Image | None,
                       out_dir: Path, start_frame: int, verified=False,
                       show_counter=SHOW_COUNTER_DEFAULT,
                       show_reply_bar=SHOW_REPLY_BAR_DEFAULT) -> int:
    """
    Render FADE_F crossfade frames between two already-composited base images.
    """
    frame_i = start_frame
    for f in range(FADE_F):
        t     = f / FADE_F             # 0 → 1
        blend = Image.blend(img_a, img_b, t)
        overlay = build_overlay_frame(n_items, idx_b, title, thumb, t,
                                      verified, show_counter, show_reply_bar)
        comp    = _composite(blend, overlay)
        _save_frame(comp, out_dir / f"f{frame_i:06d}.jpg")
        frame_i += 1
    return FADE_F


# ══════════════════════════════════════════════════════════════════════════════
#  Audio: extract each video clip's original audio and mux it back in at the
#  correct offset, over the fully-rendered (silent) overlay video.
# ══════════════════════════════════════════════════════════════════════════════

def _extract_clip_audio(media: Path, duration_sec: float, tmp_dir: Path,
                        idx: int, log_fn=None) -> Path | None:
    """Pull the original audio out of one video clip as a WAV file, trimmed
    to the same duration the clip occupies in the export. Returns None if the
    clip has no audio track (or extraction otherwise fails) — treated as
    silence for that segment."""
    wav_path = tmp_dir / f"aud_{idx}.wav"
    try:
        _ffmpeg(
            "-i", str(media),
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            "-t", f"{duration_sec:.3f}",
            str(wav_path),
            log_fn=None,
        )
    except RuntimeError:
        return None  # no audio stream in this clip
    if not wav_path.exists() or wav_path.stat().st_size < 100:
        return None
    return wav_path


def _mux_audio(silent_video: Path, audio_segments: list, total_frames: int,
              tmp_dir: Path, log_fn=None) -> bool:
    """
    audio_segments: list of (start_frame, n_frames, media_path) for each
    video clip in the export. Extracts each clip's audio, delays it to the
    right offset, mixes everything against a silent bed the full length of
    the export, and muxes the result back onto silent_video (in place).
    Returns True if any audio was actually added.
    """
    total_duration = total_frames / FPS
    extracted = []  # (delay_sec, wav_path)
    for idx, (start_frame, n_frames, media) in enumerate(audio_segments):
        wav = _extract_clip_audio(media, n_frames / FPS, tmp_dir, idx, log_fn=log_fn)
        if wav is not None:
            extracted.append((start_frame / FPS, wav))

    if not extracted:
        return False   # nothing to mux — leave the silent video as-is

    if log_fn:
        log_fn(f"  → muxing original audio from {len(extracted)} clip(s)…")

    cmd = ["-i", str(silent_video),
           "-f", "lavfi", "-t", f"{total_duration:.3f}",
           "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    for _, wav in extracted:
        cmd += ["-i", str(wav)]

    filter_parts = []
    mix_refs = ["[1:a]"]
    for j, (delay_sec, _wav) in enumerate(extracted, start=2):
        delay_ms = max(0, int(round(delay_sec * 1000)))
        filter_parts.append(f"[{j}:a]adelay=delays={delay_ms}|{delay_ms}[a{j}]")
        mix_refs.append(f"[a{j}]")

    filter_complex = ";".join(filter_parts)
    if filter_parts:
        filter_complex += ";"
    filter_complex += "".join(mix_refs) + f"amix=inputs={len(mix_refs)}:duration=first:dropout_transition=0[aout]"

    final_path = tmp_dir / "final_with_audio.mp4"
    cmd += ["-filter_complex", filter_complex,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-shortest", "-movflags", "+faststart",
            str(final_path)]

    _ffmpeg(*cmd, log_fn=log_fn)
    shutil.move(str(final_path), str(silent_video))
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  Main render pipeline per collection
# ══════════════════════════════════════════════════════════════════════════════

def get_cover_thumb(coll_dir: Path, meta: dict) -> Image.Image | None:
    cover = meta.get("cover")
    if cover:
        p = coll_dir / cover
        if p.exists():
            try:
                img = Image.open(p); img.load(); return img
            except Exception:
                pass
    for jpg in sorted(coll_dir.glob("*.jpg")):
        try:
            img = Image.open(jpg); img.load(); return img
        except Exception:
            pass
    return None


def render_collection(coll_dir: Path, photo_sec: float,
                      log_fn=None, progress_fn=None,
                      show_counter=SHOW_COUNTER_DEFAULT,
                      show_reply_bar=SHOW_REPLY_BAR_DEFAULT,
                      keep_audio=KEEP_AUDIO_DEFAULT) -> Path:
    """
    Render one highlight folder to exports/<name>.mp4.
    Returns path to output file.
    Set "verified": true in the collection's meta.json to render a blue
    verified badge next to the username, matching real IG accounts.
    If keep_audio is True (default), each video item's original audio is
    mixed back in at the point where that clip plays.
    """
    log = log_fn or (lambda m: print(m))

    meta_path = coll_dir / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"No meta.json in {coll_dir}")
    meta  = json.loads(meta_path.read_text(encoding="utf-8"))
    title = meta.get("title", coll_dir.name)
    verified = bool(meta.get("verified", False))
    items = [it for it in meta.get("items", [])
             if (coll_dir / it["file"]).exists()]
    if not items:
        raise ValueError(f"No media files found in {coll_dir}")

    n     = len(items)
    thumb = get_cover_thumb(coll_dir, meta)
    if thumb:
        thumb.thumbnail((200, 200))

    EXPORTS_DIR.mkdir(exist_ok=True)
    safe   = "".join(c for c in title if c.isalnum() or c in " _-").strip() or coll_dir.name
    output = EXPORTS_DIR / f"{safe}.mp4"

    log(f"▶  Rendering '{title}'  ({n} items)")

    with tempfile.TemporaryDirectory(prefix="hl_export_") as _td:
        tmp    = Path(_td)
        frames = tmp / "frames"
        frames.mkdir()

        frame_idx  = 0
        prev_base  = None   # last base frame (no overlay) for crossfade
        audio_segments = []  # (start_frame, n_frames, media_path) per video item

        for i, item in enumerate(items):
            media  = coll_dir / item["file"]
            ftype  = item.get("type", "image")
            pct    = int((i / n) * 80)
            if progress_fn:
                progress_fn(pct)
            log(f"  [{i+1}/{n}] {ftype}  {media.name}")

            if ftype == "image":
                base   = _fit_frame(media)

                if prev_base is not None and i > 0:
                    frame_idx += render_fade_frames(
                        prev_base, base, n, i - 1, i,
                        title, thumb, frames, frame_idx,
                        verified, show_counter, show_reply_bar,
                    )

                frame_idx += render_image_clip(
                    media, photo_sec, n, i, title, thumb,
                    frames, frame_idx, log_fn=log, verified=verified,
                    show_counter=show_counter, show_reply_bar=show_reply_bar,
                )
                prev_base = base

            else:  # video
                if prev_base is not None and i > 0:
                    try:
                        first_frame_path = tmp / f"vf_first_{i}.jpg"
                        _ffmpeg(
                            "-i", str(media),
                            "-vframes", "1", "-q:v", "3",
                            str(first_frame_path),
                            log_fn=None,
                        )
                        if first_frame_path.exists():
                            first_base = _fit_frame(first_frame_path)
                            frame_idx += render_fade_frames(
                                prev_base, first_base, n, i - 1, i,
                                title, thumb, frames, frame_idx,
                                verified, show_counter, show_reply_bar,
                            )
                    except Exception:
                        pass

                vstart = frame_idx
                nf = render_video_clip_frames(
                    media, n, i, title, thumb,
                    frames, frame_idx, tmp, log_fn=log, verified=verified,
                    show_counter=show_counter, show_reply_bar=show_reply_bar,
                )
                frame_idx += nf
                if nf > 0:
                    audio_segments.append((vstart, nf, media))

                last = sorted(frames.glob(f"f*.jpg"))
                if last:
                    prev_base = Image.open(last[-1]).convert("RGB")
                    prev_base.load()
                else:
                    prev_base = None

        total_frames = frame_idx
        log(f"  → {total_frames} frames total, encoding…")
        if progress_fn:
            progress_fn(85)

        _ffmpeg(
            "-framerate", str(FPS),
            "-i", str(frames / "f%06d.jpg"),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output),
            log_fn=log,
        )

        if progress_fn:
            progress_fn(92)

        if keep_audio and audio_segments:
            try:
                _mux_audio(output, audio_segments, total_frames, tmp, log_fn=log)
            except Exception as e:
                log(f"  ⚠ audio mux failed, keeping silent export: {e}")

    if progress_fn:
        progress_fn(100)
    log(f"  ✔  Saved → {output}")
    return output


# ══════════════════════════════════════════════════════════════════════════════
#  Load collections (reuse same logic as viewer)
# ══════════════════════════════════════════════════════════════════════════════

def load_collections():
    cols = []
    if not HIGHLIGHTS_DIR.exists():
        return cols
    for d in sorted(HIGHLIGHTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        mf = d / "meta.json"
        if not mf.exists():
            continue
        meta = json.loads(mf.read_text(encoding="utf-8"))
        items = [it for it in meta.get("items", [])
                 if (d / it["file"]).exists()]
        if items:
            cols.append({"dir": d, "meta": meta,
                         "title": meta.get("title", d.name),
                         "n": len(items)})
    return cols


# ══════════════════════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════════════════════

class ExporterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Highlights → MP4 Exporter")
        self.geometry("820x720")
        self.resizable(True, True)
        self.configure(bg=GBG)
        self.collections = load_collections()
        self._build_ui()
        self._populate_list()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=GSURF, height=64)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=GACC, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="✦ Highlights Exporter", bg=GSURF, fg=GTXT,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="→ MP4", bg=GSURF, fg=GSUB,
                 font=("Segoe UI", 11)).pack(side="left", pady=14)

        # Options row
        opt = tk.Frame(self, bg=GCARD, padx=20, pady=14)
        opt.pack(fill="x", padx=20, pady=(16, 0))

        tk.Label(opt, text="Photo duration (s):", bg=GCARD, fg=GSUB,
                 font=("Segoe UI", 10)).pack(side="left")
        self.photo_sec_var = tk.StringVar(value="4")
        tk.Entry(opt, textvariable=self.photo_sec_var, width=4,
                 bg=GSURF, fg=GTXT, insertbackground=GTXT, relief="flat",
                 font=("Segoe UI", 11, "bold"), justify="center").pack(
            side="left", padx=(6, 20), ipady=4)

        tk.Button(opt, text="Export Selected", command=self._export_selected,
                  bg=GACC, fg="white", activebackground=GACC2,
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  cursor="hand2", padx=16, pady=6).pack(side="left")
        tk.Button(opt, text="Export ALL", command=self._export_all,
                  bg=GACC2, fg="white", activebackground="#6a2fa0",
                  relief="flat", font=("Segoe UI", 10, "bold"),
                  cursor="hand2", padx=16, pady=6).pack(side="left", padx=(8, 0))
        tk.Button(opt, text="📂 Open exports/", command=self._open_exports,
                  bg=GCARD, fg=GTXT, activebackground=GSURF,
                  relief="flat", font=("Segoe UI", 10),
                  cursor="hand2", padx=14, pady=6).pack(side="right")

        # UI-accuracy toggles
        opt2 = tk.Frame(self, bg=GCARD, padx=20, pady=14)
        opt2.pack(fill="x", padx=20, pady=(0, 12))
        self.reply_bar_var = tk.BooleanVar(value=SHOW_REPLY_BAR_DEFAULT)
        self.counter_var   = tk.BooleanVar(value=SHOW_COUNTER_DEFAULT)
        self.audio_var      = tk.BooleanVar(value=KEEP_AUDIO_DEFAULT)
        tk.Checkbutton(opt2, text="Show reply bar", variable=self.reply_bar_var,
                       bg=GCARD, fg=GTXT, selectcolor=GSURF, activebackground=GCARD,
                       activeforeground=GTXT, font=("Segoe UI", 9)).pack(side="left")
        tk.Checkbutton(opt2, text='Show "n/n" counter (non-standard)', variable=self.counter_var,
                       bg=GCARD, fg=GTXT, selectcolor=GSURF, activebackground=GCARD,
                       activeforeground=GTXT, font=("Segoe UI", 9)).pack(side="left", padx=(16, 0))
        tk.Checkbutton(opt2, text="Keep original video audio", variable=self.audio_var,
                       bg=GCARD, fg=GTXT, selectcolor=GSURF, activebackground=GCARD,
                       activeforeground=GTXT, font=("Segoe UI", 9)).pack(side="left", padx=(16, 0))

        # Collection list
        list_frame = tk.Frame(self, bg=GSURF, padx=2, pady=2)
        list_frame.pack(fill="x", padx=20, pady=(12, 0))
        tk.Label(list_frame, text="COLLECTIONS", bg=GSURF, fg=GSUB,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(6, 2))

        lb_frame = tk.Frame(list_frame, bg=GSURF)
        lb_frame.pack(fill="x", padx=4, pady=(0, 4))
        scroll = ttk.Scrollbar(lb_frame, orient="vertical")
        self.listbox = tk.Listbox(
            lb_frame, bg=GCARD, fg=GTXT, selectbackground=GACC,
            selectforeground="white", activestyle="none",
            relief="flat", font=("Segoe UI", 10), height=8,
            yscrollcommand=scroll.set, selectmode="extended",
        )
        scroll.config(command=self.listbox.yview)
        scroll.pack(side="right", fill="y")
        self.listbox.pack(fill="x", expand=True)

        sel_row = tk.Frame(list_frame, bg=GSURF)
        sel_row.pack(anchor="w", padx=4, pady=(2, 6))
        tk.Button(sel_row, text="Select All", command=lambda: self.listbox.select_set(0, "end"),
                  bg=GSURF, fg=GSUB, relief="flat", font=("Segoe UI", 8),
                  cursor="hand2").pack(side="left")
        tk.Button(sel_row, text="Select None", command=lambda: self.listbox.selection_clear(0, "end"),
                  bg=GSURF, fg=GSUB, relief="flat", font=("Segoe UI", 8),
                  cursor="hand2").pack(side="left", padx=(8, 0))

        # Per-item progress bar + current item label
        prog_frame = tk.Frame(self, bg=GBG, padx=20, pady=6)
        prog_frame.pack(fill="x")
        self.item_lbl = tk.Label(prog_frame, text="", bg=GBG, fg=GSUB,
                                 font=("Segoe UI", 9))
        self.item_lbl.pack(anchor="w")
        sty = ttk.Style(self); sty.theme_use("clam")
        sty.configure("IG.Horizontal.TProgressbar",
                       troughcolor=GSURF, background=GACC,
                       bordercolor=GBG, lightcolor=GACC, darkcolor=GACC2, thickness=8)
        self.progress = ttk.Progressbar(prog_frame,
                                         style="IG.Horizontal.TProgressbar",
                                         mode="determinate")
        self.progress.pack(fill="x", pady=(2, 0))

        # Log
        log_frame = tk.Frame(self, bg=GSURF, padx=2, pady=2)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        self.log_box = tk.Text(
            log_frame, bg="#0d0d0d", fg=GTXT,
            font=("Consolas", 9), relief="flat",
            wrap="word", state="disabled",
            selectbackground=GACC2, padx=10, pady=8,
        )
        sb = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        self.log_box.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_box.pack(fill="both", expand=True)
        for tag, col in [("ok", GSUCC), ("err", GERR), ("acc", GACC), ("sub", GSUB), ("gold", GGOLD)]:
            self.log_box.tag_configure(tag, foreground=col)

        # Status bar
        bot = tk.Frame(self, bg=GSURF, padx=20, pady=10)
        bot.pack(fill="x", side="bottom")
        self.status_dot = tk.Label(bot, text="●", fg=GSUB, bg=GSURF, font=("Segoe UI", 14))
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(bot, text="Ready", bg=GSURF, fg=GSUB,
                                   font=("Segoe UI", 10))
        self.status_lbl.pack(side="left", padx=6)

    def _populate_list(self):
        self.listbox.delete(0, "end")
        if not self.collections:
            self.listbox.insert("end", "  No collections found — run downloader first")
            return
        for c in self.collections:
            self.listbox.insert("end",
                f"  {c['title']}   ({c['n']} item{'s' if c['n']!=1 else ''})")

    def _log(self, msg, tag=""):
        self.log_box.config(state="normal")
        self.log_box.insert("end", msg + "\n", tag or ())
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def _set_status(self, text, colour=GSUB):
        self.status_dot.config(fg=colour)
        self.status_lbl.config(text=text, fg=colour)

    def _get_photo_sec(self):
        try:
            return max(1.0, min(float(self.photo_sec_var.get()), 60.0))
        except ValueError:
            return 4.0

    def _export_selected(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Nothing selected", "Select at least one collection.")
            return
        cols = [self.collections[i] for i in sel]
        self._run_export(cols)

    def _export_all(self):
        if not self.collections:
            messagebox.showwarning("Empty", "No collections to export.")
            return
        self._run_export(self.collections)

    def _run_export(self, cols):
        if not _check_ffmpeg():
            messagebox.showerror("ffmpeg missing",
                "ffmpeg not found on PATH.\n"
                "Install from https://ffmpeg.org/download.html and add to PATH.")
            return

        photo_sec = self._get_photo_sec()
        show_reply_bar = self.reply_bar_var.get()
        show_counter   = self.counter_var.get()
        keep_audio     = self.audio_var.get()
        self.progress["value"] = 0
        self._set_status("Exporting…", GACC)

        def run():
            n_total = len(cols)
            for ci, c in enumerate(cols):
                self.after(0, lambda t=c["title"]: (
                    self._log(f"\n📁  {t}", "acc"),
                    self.item_lbl.config(text=f"Exporting: {t}  ({ci+1}/{n_total})"),
                ))
                try:
                    def log_fn(m, _ci=ci):
                        self.after(0, self._log, m)
                    def prog_fn(pct, _ci=ci, _n=n_total):
                        overall = int((_ci / _n) * 100 + pct / _n)
                        self.after(0, lambda: self.progress.config(value=overall))

                    render_collection(c["dir"], photo_sec,
                                      log_fn=log_fn, progress_fn=prog_fn,
                                      show_counter=show_counter,
                                      show_reply_bar=show_reply_bar,
                                      keep_audio=keep_audio)
                except Exception as e:
                    self.after(0, self._log, f"  ✘ ERROR: {e}", "err")

            self.after(0, self._on_done)

        threading.Thread(target=run, daemon=True).start()

    def _on_done(self):
        self.progress["value"] = 100
        self._set_status("Done ✓", GSUCC)
        self.item_lbl.config(text="")
        self._log("\n✅  All exports complete!", "ok")

    def _open_exports(self):
        EXPORTS_DIR.mkdir(exist_ok=True)
        os.startfile(EXPORTS_DIR.resolve())


# ══════════════════════════════════════════════════════════════════════════════
#  CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Instagram highlights to MP4")
    parser.add_argument("--all", action="store_true", help="Export all collections without GUI")
    parser.add_argument("--photo-sec", type=float, default=4.0,
                        help="Seconds each photo is shown (default 4)")
    parser.add_argument("--no-counter", action="store_true",
                        help='Hide the "n/n" counter text (shown by default)')
    parser.add_argument("--no-reply-bar", action="store_true",
                        help='Hide the bottom "Send message" reply bar')
    parser.add_argument("--mute", action="store_true",
                        help="Drop original video audio (kept by default)")
    args = parser.parse_args()

    if args.all:
        if not _check_ffmpeg():
            print("ERROR: ffmpeg not found on PATH.")
            sys.exit(1)
        cols = load_collections()
        if not cols:
            print("No collections found in highlights/")
            sys.exit(0)
        for c in cols:
            print(f"\n{'='*60}\n{c['title']}")
            try:
                render_collection(c["dir"], args.photo_sec,
                                  show_counter=not args.no_counter,
                                  show_reply_bar=not args.no_reply_bar,
                                  keep_audio=not args.mute)
            except Exception as e:
                print(f"ERROR: {e}")
    else:
        ExporterApp().mainloop()
