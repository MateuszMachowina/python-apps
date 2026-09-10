"""
Instagram Highlights Downloader
Reads all Firefox Instagram cookies and downloads highlight reels
directly via Instagram's internal web API.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sqlite3
import shutil
import os
import json
import re
import time
import tempfile
from pathlib import Path
from datetime import datetime


# ─── Colours & fonts ────────────────────────────────────────────────────────────
BG        = "#0a0a0a"
SURFACE   = "#161616"
CARD      = "#1e1e1e"
ACCENT    = "#c13584"
ACCENT2   = "#833ab4"
GOLD      = "#f5a623"
TEXT      = "#f0f0f0"
SUBTEXT   = "#888888"
SUCCESS   = "#2ecc71"
ERROR     = "#e74c3c"
FONT_HEAD = ("Segoe UI", 22, "bold")
FONT_SUB  = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 9)
FONT_BTN  = ("Segoe UI", 11, "bold")

HIGHLIGHTS_DIR   = Path("highlights")
DEFAULT_USERNAME = ""      # ← your Instagram username
DEFAULT_USER_ID  = ""   # ← your numeric Instagram user ID


# ─── Firefox cookie extraction ───────────────────────────────────────────────────
def find_firefox_profile() -> Path | None:
    appdata = os.environ.get("APPDATA", "")
    profiles_root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
    if not profiles_root.exists():
        return None
    for p in profiles_root.iterdir():
        if p.is_dir() and ("default-release" in p.name or "default" in p.name):
            return p
    dirs = [p for p in profiles_root.iterdir() if p.is_dir()]
    return dirs[0] if dirs else None


def extract_instagram_cookies(profile_dir: Path) -> dict:
    """Return ALL instagram.com cookies from Firefox as {name: value}."""
    cookies_db = profile_dir / "cookies.sqlite"
    if not cookies_db.exists():
        return {}
        
    tmp_db = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(cookies_db, tmp_db)
    
    # FIX: Kopiowanie plików WAL i SHM, jeśli Firefox aktualnie działa
    for ext in ["-wal", "-shm"]:
        extra_file = cookies_db.with_name(cookies_db.name + ext)
        if extra_file.exists():
            shutil.copy2(extra_file, tmp_db.with_name(tmp_db.name + ext))
            
    try:
        conn = sqlite3.connect(tmp_db)
        cur  = conn.cursor()
        cur.execute("SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'")
        rows = cur.fetchall()
        conn.close()
        return {name: value for name, value in rows}
    finally:
        tmp_db.unlink(missing_ok=True)
        for ext in ["-wal", "-shm"]:
            tmp_db.with_name(tmp_db.name + ext).unlink(missing_ok=True)


def extract_instagram_sessionid(profile_dir: Path) -> str | None:
    return extract_instagram_cookies(profile_dir).get("sessionid")


# ─── Title sanitizing (protects flag emoji from a real IG API quirk) ─────────────
def _fix_title_unicode(title: str) -> str:
    """
    Instagram's private API occasionally returns emoji — including the flag
    emoji people put at the end of a highlight name, e.g. 'Paris 🇫🇷' — as
    unpaired UTF-16 surrogates when a response gets serialized oddly. A
    string like that looks fine in memory but raises UnicodeEncodeError the
    instant it's written to a UTF-8 file. Uncaught, that used to kill the
    *entire* sync silently (see the try/except added around each highlight
    below) — every highlight after the bad one in the list never got saved,
    which is a very plausible reason flags looked "missing": not just from
    that one highlight, but from everything that came after it.
    This repairs valid surrogate pairs back into real characters and drops
    anything genuinely unrepairable, instead of ever crashing the write.
    """
    if not title:
        return title
    try:
        title.encode("utf-8")
        return title
    except UnicodeEncodeError:
        try:
            return title.encode("utf-16", "surrogatepass").decode("utf-16")
        except Exception:
            return title.encode("utf-8", "replace").decode("utf-8")


# Same detection the exporter/viewer use, kept here only for a diagnostic log
# line — lets you see in the log whether Instagram actually sent a flag.
_FLAG_HINT_RE = re.compile(
    r'[\U0001f1e6-\U0001f1ff]{2}\s*$'      # real flag emoji
    r'|(?:\s|^)\[?[A-Za-z]{2}\]?\s*$'      # plain 2-letter code
)


# ─── Instagram API ───────────────────────────────────────────────────────────────
IG_APP_ID = "936619743392459"


def _make_session(all_cookies: dict):
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) "
            "Gecko/20100101 Firefox/126.0"
        ),
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
        "Origin":          "https://www.instagram.com",
        "Referer":         "https://www.instagram.com/",
    })
    for name, val in all_cookies.items():
        s.cookies.set(name, val, domain=".instagram.com", path="/")
    if "csrftoken" in all_cookies:
        s.headers["X-CSRFToken"] = all_cookies["csrftoken"]
    return s


def _warm_up(sess, log_fn):
    token = sess.cookies.get("csrftoken", domain=".instagram.com") or ""
    ds    = sess.cookies.get("ds_user_id", domain=".instagram.com") or ""
    if token and ds:
        log_fn(f"Session cookies OK  (csrftoken=OK  ds_user_id={ds})", SUBTEXT)
        sess.headers["X-CSRFToken"] = token
        return
    log_fn("Some cookies missing, fetching instagram.com …", SUBTEXT)
    try:
        sess.get("https://www.instagram.com/", timeout=20, headers={
            "Accept":         "text/html,application/xhtml+xml,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })
    except Exception as e:
        log_fn(f"Warm-up fetch failed: {e}", GOLD)
    token = sess.cookies.get("csrftoken", domain=".instagram.com") or ""
    ds    = sess.cookies.get("ds_user_id", domain=".instagram.com") or ""
    log_fn(f"csrftoken={'OK' if token else 'MISSING'}  ds_user_id={ds or 'MISSING'}", SUBTEXT)
    if not token:
        log_fn("WARNING: csrftoken missing — log into Instagram in Firefox first.", GOLD)
    if token:
        sess.headers["X-CSRFToken"] = token


def _api_headers() -> dict:
    return {
        "Accept":           "*/*",
        "X-IG-App-ID":      IG_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest":   "empty",
        "Sec-Fetch-Mode":   "cors",
        "Sec-Fetch-Site":   "same-origin",
    }


def _resolve_user_id(sess, username: str, user_id_hint: str, log_fn) -> str | None:
    """Return user ID — use hint directly if provided, otherwise fetch from API."""
    if user_id_hint.strip():
        log_fn(f"Using provided User ID: {user_id_hint.strip()}", SUBTEXT)
        return user_id_hint.strip()

    log_fn(f"Resolving user ID for @{username} …", SUBTEXT)
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        r = sess.get(url, timeout=20, headers=_api_headers())
    except Exception as e:
        log_fn(f"ERROR: request failed: {e}", ERROR)
        return None

    if r.status_code == 429:
        log_fn("ERROR 429: Instagram is rate-limiting this IP.", ERROR)
        log_fn("Enter your User ID manually in the field above to bypass this.", GOLD)
        return None
    if r.status_code != 200:
        log_fn(f"ERROR: {r.status_code} — {r.text[:200]}", ERROR)
        return None

    uid = r.json().get("data", {}).get("user", {}).get("id")
    if uid:
        log_fn(f"User ID resolved: {uid}", SUCCESS)
    else:
        log_fn("ERROR: could not find user ID in response.", ERROR)
    return uid


def _get_highlights_tray(sess, user_id: str, log_fn) -> list:
    log_fn("Fetching highlights list …", SUBTEXT)
    url = f"https://www.instagram.com/api/v1/highlights/{user_id}/highlights_tray/"
    r = sess.get(url, timeout=20, headers=_api_headers())
    if r.status_code == 429:
        log_fn("ERROR 429 on highlights_tray — IP still throttled.", ERROR)
        return []
    if r.status_code != 200:
        log_fn(f"ERROR: highlights_tray returned {r.status_code}: {r.text[:300]}", ERROR)
        return []
    tray = r.json().get("tray", [])
    log_fn(f"Found {len(tray)} highlight collection(s)", SUCCESS)
    return tray


def _get_reel_items(sess, reel_id: str, log_fn) -> list:
    if not reel_id.startswith("highlight:"):
        reel_id = f"highlight:{reel_id}"
    url = f"https://www.instagram.com/api/v1/feed/reels_media/?reel_ids={reel_id}"
    r = sess.get(url, timeout=20, headers=_api_headers())
    if r.status_code != 200:
        log_fn(f"  WARNING: reels_media returned {r.status_code}", GOLD)
        return []
    data  = r.json()
    reels = data.get("reels_media") or list(data.get("reels", {}).values())
    return reels[0].get("items", []) if reels else []


def _best_video_url(item: dict) -> str | None:
    versions = item.get("video_versions") or []
    versions.sort(key=lambda v: v.get("width", 0) * v.get("height", 0), reverse=True)
    return versions[0]["url"] if versions else None


def _best_image_url(item: dict) -> str | None:
    candidates = (item.get("image_versions2") or {}).get("candidates") or []
    candidates.sort(key=lambda c: c.get("width", 0) * c.get("height", 0), reverse=True)
    return candidates[0]["url"] if candidates else None


def _stream_download(sess, url: str, dest: Path):
    r = sess.get(url, stream=True, timeout=60)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            f.write(chunk)


# ─── Main orchestrator ───────────────────────────────────────────────────────────
def download_highlights(username: str, user_id_hint: str, session_id: str,
                        log_fn, progress_fn, done_fn):
    try:
        import requests as _chk
    except ImportError:
        log_fn("ERROR: requests not installed. Run: pip install requests", ERROR)
        done_fn(False)
        return

    # Load ALL Firefox Instagram cookies
    profile = find_firefox_profile()
    all_cookies = {}
    if profile:
        all_cookies = extract_instagram_cookies(profile)
        log_fn(f"Loaded {len(all_cookies)} cookies from Firefox profile", SUBTEXT)
    all_cookies["sessionid"] = session_id  # GUI field takes priority

    sess = _make_session(all_cookies)
    _warm_up(sess, log_fn)

    user_id = _resolve_user_id(sess, username, user_id_hint, log_fn)
    if not user_id:
        log_fn("Cannot continue without a valid User ID.", ERROR)
        done_fn(False)
        return

    trays = _get_highlights_tray(sess, user_id, log_fn)
    if not trays:
        log_fn("No highlights found.", GOLD)
        done_fn(True)
        return

    total    = sum(t.get("media_count", 0) for t in trays) or len(trays) * 5
    done_cnt = 0
    HIGHLIGHTS_DIR.mkdir(exist_ok=True)

    for tray in trays:
        try:
            title    = _fix_title_unicode(tray.get("title", "Untitled"))
            reel_id  = str(tray.get("id", ""))
            # Get Instagram highlight cover image
            cover_url = None

            cover = tray.get("cover_media", {})

            cover_url = (
                cover.get("cropped_image_version", {}).get("url")
            )

            if not cover_url:
                candidates = (
                    cover.get("image_versions2", {})
                        .get("candidates", [])
                )
                if candidates:
                    cover_url = candidates[0].get("url")
            safe     = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            safe     = safe or reel_id.replace(":", "_")
            coll_dir = HIGHLIGHTS_DIR / safe
            coll_dir.mkdir(exist_ok=True)
            cover_file = coll_dir / "cover.jpg"
            if cover_url and not cover_file.exists():
                try:
                    log_fn("  ↳ downloading cover image", SUBTEXT)
                    _stream_download(sess, cover_url, cover_file)
                except Exception as e:
                    log_fn(f"  ↳ cover download failed: {e}", GOLD)

            log_fn(f"\n📁  {title}", ACCENT)
            if _FLAG_HINT_RE.search(title):
                log_fn(f"  ↳ flag/country code detected in title: {title!r}", SUBTEXT)

            items = _get_reel_items(sess, reel_id, log_fn)
            if not items:
                log_fn("  (no items retrieved — skipping)", SUBTEXT)
                continue

            meta = {
                "title": title,
                "id": reel_id,
                "cover": "cover.jpg",
                "downloaded_at": datetime.utcnow().isoformat(),
                "items": [],
            }

            for idx, item in enumerate(items, 1):
                is_video  = item.get("media_type") == 2
                fname     = f"{idx:03d}"
                dest      = coll_dir / (f"{fname}.mp4" if is_video else f"{fname}.jpg")
                media_url = _best_video_url(item) if is_video else _best_image_url(item)
                ftype     = "video" if is_video else "image"

                if dest.exists():
                    log_fn(f"  ↳ [{idx}] already exists, skipping", SUBTEXT)
                elif media_url:
                    try:
                        log_fn(f"  ↳ [{idx}] {ftype} …", TEXT)
                        _stream_download(sess, media_url, dest)
                        log_fn(f"       ✔ {dest.name}", SUCCESS)
                    except Exception as e:
                        log_fn(f"       ✘ {e}", ERROR)
                else:
                    log_fn(f"  ↳ [{idx}] no media URL found", GOLD)

                meta["items"].append({"index": idx, "type": ftype, "file": dest.name})
                done_cnt += 1
                progress_fn(done_cnt, max(total, done_cnt))
                time.sleep(0.4)

            with open(coll_dir / "meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

        except Exception as e:
            log_fn(f"  ✘ Skipped '{tray.get('title', '?')}' due to an error: {e}", ERROR)
            continue

    log_fn(f"\n✅  Done! Saved to: {HIGHLIGHTS_DIR.resolve()}", SUCCESS)
    done_fn(True)


# ─── GUI ─────────────────────────────────────────────────────────────────────────
class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Highlights Downloader")
        self.geometry("760x660")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=SURFACE, height=64)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(header, text="✦ Highlights Sync", bg=SURFACE, fg=TEXT,
                 font=FONT_HEAD).pack(side="left", padx=20, pady=14)
        tk.Label(header, text="instagram → local", bg=SURFACE, fg=SUBTEXT,
                 font=FONT_SUB).pack(side="left", pady=14)

        # Form
        form = tk.Frame(self, bg=CARD, padx=24, pady=20)
        form.pack(fill="x", padx=20, pady=(20, 0))

        # Row 0 labels
        tk.Label(form, text="Instagram username", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w")
        tk.Label(form, text="User ID  (pre-filled, skip API lookup)", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w", padx=(12, 0))
        tk.Label(form, text="Session ID  (auto-detected)", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(12, 0))

        # Row 1 entries
        self.username_var = tk.StringVar(value=DEFAULT_USERNAME)
        tk.Entry(form, textvariable=self.username_var, bg=SURFACE,
                 fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=FONT_SUB, width=16).grid(
            row=1, column=0, sticky="ew", pady=(4, 12), ipady=6)

        self.userid_var = tk.StringVar(value=DEFAULT_USER_ID)
        tk.Entry(form, textvariable=self.userid_var, bg=SURFACE,
                 fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=FONT_SUB, width=16).grid(
            row=1, column=1, sticky="ew", padx=(12, 0), pady=(4, 12), ipady=6)

        self.session_var = tk.StringVar()
        tk.Entry(form, textvariable=self.session_var, bg=SURFACE,
                 fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=FONT_SUB, show="•", width=32).grid(
            row=1, column=2, sticky="ew", padx=(12, 0), pady=(4, 12), ipady=6)

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=2)

        self.detect_lbl = tk.Label(form, text="", bg=CARD, fg=SUBTEXT, font=("Segoe UI", 9))
        self.detect_lbl.grid(row=2, column=0, columnspan=3, sticky="w")

        # Progress
        prog_frame = tk.Frame(self, bg=BG, padx=20, pady=10)
        prog_frame.pack(fill="x")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("IG.Horizontal.TProgressbar",
                        troughcolor=SURFACE, background=ACCENT,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT2, thickness=8)
        self.progress = ttk.Progressbar(prog_frame, style="IG.Horizontal.TProgressbar",
                                        mode="determinate")
        self.progress.pack(fill="x")
        self.prog_lbl = tk.Label(prog_frame, text="Ready", bg=BG, fg=SUBTEXT,
                                 font=("Segoe UI", 9))
        self.prog_lbl.pack(anchor="e")

        # Log
        log_frame = tk.Frame(self, bg=SURFACE, padx=2, pady=2)
        log_frame.pack(fill="both", expand=True, padx=20)
        self.log = scrolledtext.ScrolledText(
            log_frame, bg="#0d0d0d", fg=TEXT, font=FONT_MONO,
            relief="flat", wrap="word", state="disabled",
            selectbackground=ACCENT2, padx=12, pady=10)
        self.log.pack(fill="both", expand=True)
        for tag, col in [("error", ERROR), ("success", SUCCESS),
                         ("accent", ACCENT), ("sub", SUBTEXT), ("gold", GOLD)]:
            self.log.tag_configure(tag, foreground=col)

        # Bottom bar
        bottom = tk.Frame(self, bg=SURFACE, padx=20, pady=14)
        bottom.pack(fill="x", side="bottom")
        self.sync_btn = tk.Button(
            bottom, text="⬇  Sync Highlights", command=self._start_download,
            bg=ACCENT, fg="white", activebackground=ACCENT2, activeforeground="white",
            relief="flat", font=FONT_BTN, cursor="hand2", padx=24, pady=10)
        self.sync_btn.pack(side="right")
        tk.Button(bottom, text="📂  Open folder", command=self._open_folder,
                  bg=CARD, fg=TEXT, activebackground=SURFACE, activeforeground=TEXT,
                  relief="flat", font=FONT_BTN, cursor="hand2",
                  padx=16, pady=10).pack(side="right", padx=(0, 10))
        self.status_dot = tk.Label(bottom, text="●", fg=SUBTEXT, bg=SURFACE,
                                   font=("Segoe UI", 14))
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(bottom, text="Idle", bg=SURFACE, fg=SUBTEXT, font=FONT_SUB)
        self.status_lbl.pack(side="left", padx=6)

    def _auto_detect(self):
        profile = find_firefox_profile()
        if not profile:
            self.detect_lbl.config(
                text="⚠  Firefox profile not found – paste session ID manually", fg=GOLD)
            return
            
        cookies = extract_instagram_cookies(profile)
        sid = cookies.get("sessionid")
        uid = cookies.get("ds_user_id") # To jest kluczowe numeryczne User ID!
        
        if sid:
            self.session_var.set(sid)
            if uid:
                self.userid_var.set(uid)
                self.detect_lbl.config(
                    text=f"✔  Session & User ID ({uid}) auto-detected!", fg=SUCCESS)
            else:
                self.detect_lbl.config(
                    text="⚠  Session found, but User ID missing.", fg=GOLD)
        else:
            self.detect_lbl.config(
                text="⚠  No Instagram session in Firefox – log in first", fg=GOLD)

    def _log(self, msg: str, colour: str = TEXT):
        tag_map = {ERROR: "error", SUCCESS: "success", ACCENT: "accent",
                   SUBTEXT: "sub", GOLD: "gold"}
        tag = tag_map.get(colour, "")
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n", tag if tag else ())
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_progress(self, done: int, total: int):
        pct = int(done / total * 100) if total else 0
        self.progress["value"] = pct
        self.prog_lbl.config(text=f"{done} / {total} items  ({pct}%)")

    def _set_status(self, text: str, colour: str = SUBTEXT):
        self.status_dot.config(fg=colour)
        self.status_lbl.config(text=text, fg=colour)

    def _start_download(self):
        username  = self.username_var.get().strip().lstrip("@")
        user_id   = self.userid_var.get().strip()
        session   = self.session_var.get().strip()
        
        if not user_id and not username:
            messagebox.showwarning("Missing", "Enter your User ID or Instagram username.")
            return
        if not session:
            messagebox.showwarning("Missing",
                "No session ID found. Log into Instagram in Firefox first.")
            return
        self.sync_btn.config(state="disabled", text="Syncing …")
        self.progress["value"] = 0
        self._set_status("Downloading …", ACCENT)
        self._log(f"Starting sync for @{username}  –  {datetime.now().strftime('%H:%M:%S')}")

        def run():
            try:
                download_highlights(
                    username, user_id, session,
                    log_fn=lambda m, c=TEXT: self.after(0, self._log, m, c),
                    progress_fn=lambda d, t: self.after(0, self._set_progress, d, t),
                    done_fn=lambda ok: self.after(0, self._on_done, ok),
                )
            except Exception as e:
                self.after(0, self._log, f"✘ Unexpected error: {e}", ERROR)
                self.after(0, self._on_done, False)
        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, ok: bool):
        self.sync_btn.config(state="normal", text="⬇  Sync Highlights")
        self._set_status("Done" if ok else "Failed", SUCCESS if ok else ERROR)
        if ok:
            self.progress["value"] = 100

    def _open_folder(self):
        HIGHLIGHTS_DIR.mkdir(exist_ok=True)
        os.startfile(HIGHLIGHTS_DIR.resolve())


if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()
