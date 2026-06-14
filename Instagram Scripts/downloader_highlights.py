"""
Instagram Highlights Downloader — multi-account support
Saves to highlights/<username>/<highlight_title>/
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading, sqlite3, shutil, os, json, time, tempfile
from pathlib import Path
from datetime import datetime

# ─── Colours ────────────────────────────────────────────────────────────────────
BG        = "#0a0a0a"; SURFACE = "#161616"; CARD    = "#1e1e1e"
ACCENT    = "#c13584"; ACCENT2 = "#833ab4"; GOLD    = "#f5a623"
TEXT      = "#f0f0f0"; SUBTEXT = "#888888"; SUCCESS = "#2ecc71"; ERROR = "#e74c3c"
FONT_HEAD = ("Segoe UI", 22, "bold"); FONT_SUB = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 9);          FONT_BTN = ("Segoe UI", 11, "bold")

HIGHLIGHTS_DIR = Path("highlights")


# ─── Firefox helpers ─────────────────────────────────────────────────────────────
def find_firefox_profile() -> Path | None:
    appdata = os.environ.get("APPDATA", "")
    root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
    if not root.exists(): return None
    for p in root.iterdir():
        if p.is_dir() and ("default-release" in p.name or "default" in p.name):
            return p
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return dirs[0] if dirs else None

def extract_instagram_cookies(profile_dir: Path) -> dict:
    db = profile_dir / "cookies.sqlite"
    if not db.exists(): return {}
    tmp = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(db, tmp)
    for ext in ["-wal", "-shm"]:
        src = db.with_name(db.name + ext)
        if src.exists(): shutil.copy2(src, tmp.with_name(tmp.name + ext))
    try:
        import sqlite3 as _sq
        conn = _sq.connect(tmp)
        rows = conn.cursor().execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        ).fetchall()
        conn.close()
        return {n: v for n, v in rows}
    finally:
        tmp.unlink(missing_ok=True)
        for ext in ["-wal", "-shm"]:
            tmp.with_name(tmp.name + ext).unlink(missing_ok=True)

def extract_instagram_sessionid(profile_dir: Path) -> str | None:
    return extract_instagram_cookies(profile_dir).get("sessionid")


# ─── Instagram API ───────────────────────────────────────────────────────────────
IG_APP_ID = "936619743392459"

def _make_session(cookies: dict):
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
    })
    for n, v in cookies.items():
        s.cookies.set(n, v, domain=".instagram.com", path="/")
    if "csrftoken" in cookies:
        s.headers["X-CSRFToken"] = cookies["csrftoken"]
    return s

def _warm_up(sess, log_fn):
    token = sess.cookies.get("csrftoken", domain=".instagram.com") or ""
    ds    = sess.cookies.get("ds_user_id", domain=".instagram.com") or ""
    if token and ds:
        log_fn(f"Session OK  (csrftoken=OK  ds_user_id={ds})", SUBTEXT)
        sess.headers["X-CSRFToken"] = token; return
    log_fn("Fetching instagram.com to refresh cookies …", SUBTEXT)
    try:
        sess.get("https://www.instagram.com/", timeout=20, headers={
            "Accept": "text/html,*/*", "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none"})
    except Exception as e:
        log_fn(f"Warm-up failed: {e}", GOLD)
    token = sess.cookies.get("csrftoken", domain=".instagram.com") or ""
    ds    = sess.cookies.get("ds_user_id", domain=".instagram.com") or ""
    log_fn(f"csrftoken={'OK' if token else 'MISSING'}  ds_user_id={ds or 'MISSING'}", SUBTEXT)
    if token: sess.headers["X-CSRFToken"] = token

def _ah() -> dict:
    return {"Accept": "*/*", "X-IG-App-ID": IG_APP_ID,
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"}

def _resolve_user_id(sess, username: str, uid_hint: str, log_fn) -> str | None:
    if uid_hint.strip():
        log_fn(f"Using User ID: {uid_hint.strip()}", SUBTEXT)
        return uid_hint.strip()
    log_fn(f"Resolving user ID for @{username} …", SUBTEXT)
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    try:
        r = sess.get(url, timeout=20, headers=_ah())
    except Exception as e:
        log_fn(f"ERROR: {e}", ERROR); return None
    if r.status_code == 429:
        log_fn("ERROR 429 — rate limited. Enter User ID manually.", ERROR); return None
    if r.status_code != 200:
        log_fn(f"ERROR {r.status_code}: {r.text[:200]}", ERROR); return None
    uid = r.json().get("data", {}).get("user", {}).get("id")
    if uid: log_fn(f"User ID: {uid}", SUCCESS)
    else:   log_fn("ERROR: user ID not found in response.", ERROR)
    return uid

def _get_tray(sess, user_id: str, log_fn) -> list:
    log_fn("Fetching highlights list …", SUBTEXT)
    r = sess.get(f"https://www.instagram.com/api/v1/highlights/{user_id}/highlights_tray/",
                 timeout=20, headers=_ah())
    if r.status_code == 429:
        log_fn("ERROR 429 on highlights_tray.", ERROR); return []
    if r.status_code != 200:
        log_fn(f"ERROR {r.status_code}: {r.text[:300]}", ERROR); return []
    tray = r.json().get("tray", [])
    log_fn(f"Found {len(tray)} highlight collection(s)", SUCCESS)
    return tray

def _get_items(sess, reel_id: str, log_fn) -> list:
    if not reel_id.startswith("highlight:"): reel_id = f"highlight:{reel_id}"
    r = sess.get(f"https://www.instagram.com/api/v1/feed/reels_media/?reel_ids={reel_id}",
                 timeout=20, headers=_ah())
    if r.status_code != 200:
        log_fn(f"  WARNING: reels_media {r.status_code}", GOLD); return []
    data  = r.json()
    reels = data.get("reels_media") or list(data.get("reels", {}).values())
    return reels[0].get("items", []) if reels else []

def _best_video(item): 
    v = sorted(item.get("video_versions") or [], key=lambda x: x.get("width",0)*x.get("height",0), reverse=True)
    return v[0]["url"] if v else None

def _best_image(item):
    c = sorted((item.get("image_versions2") or {}).get("candidates") or [],
               key=lambda x: x.get("width",0)*x.get("height",0), reverse=True)
    return c[0]["url"] if c else None

def _dl(sess, url: str, dest: Path):
    r = sess.get(url, stream=True, timeout=60); r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 16): f.write(chunk)


# ─── Main download logic ──────────────────────────────────────────────────────────
def download_highlights(username: str, uid_hint: str, session_id: str,
                        log_fn, progress_fn, done_fn):
    try:
        import requests as _r
    except ImportError:
        log_fn("ERROR: pip install requests", ERROR); done_fn(False); return

    profile = find_firefox_profile()
    cookies = extract_instagram_cookies(profile) if profile else {}
    if profile:
        log_fn(f"Loaded {len(cookies)} cookies from Firefox", SUBTEXT)
    cookies["sessionid"] = session_id

    sess = _make_session(cookies)
    _warm_up(sess, log_fn)

    user_id = _resolve_user_id(sess, username, uid_hint, log_fn)
    if not user_id:
        log_fn("Cannot continue without User ID.", ERROR); done_fn(False); return

    trays = _get_tray(sess, user_id, log_fn)
    if not trays:
        log_fn("No highlights found.", GOLD); done_fn(True); return

    total = sum(t.get("media_count", 0) for t in trays) or len(trays) * 5
    done_cnt = 0

    # ── highlights/<username>/ ────────────────────────────────────────────────
    user_dir = HIGHLIGHTS_DIR / username
    user_dir.mkdir(parents=True, exist_ok=True)

    for tray in trays:
        title   = tray.get("title", "Untitled")
        reel_id = str(tray.get("id", ""))
        safe    = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        if not safe: safe = "".join(c for c in reel_id if c.isalnum() or c in "_-")
        coll_dir = user_dir / safe
        coll_dir.mkdir(exist_ok=True)

        # Cover image
        cover_url = (tray.get("cover_media") or {}).get("cropped_image_version", {}).get("url")
        if not cover_url:
            cands = ((tray.get("cover_media") or {}).get("image_versions2") or {}).get("candidates", [])
            if cands: cover_url = cands[0].get("url")
        cover_file = coll_dir / "cover.jpg"
        if cover_url and not cover_file.exists():
            try:
                log_fn(f"  ↳ cover …", SUBTEXT)
                _dl(sess, cover_url, cover_file)
            except Exception as e:
                log_fn(f"  ↳ cover failed: {e}", GOLD)

        log_fn(f"\n📁  {title}", ACCENT)

        items = _get_items(sess, reel_id, log_fn)
        if not items:
            log_fn("  (no items — skipping)", SUBTEXT); continue

        meta = {"title": title, "id": reel_id, "cover": "cover.jpg",
                "username": username,
                "downloaded_at": datetime.utcnow().isoformat(), "items": []}

        for idx, item in enumerate(items, 1):
            is_vid = item.get("media_type") == 2
            fname  = f"{idx:03d}"
            dest   = coll_dir / (f"{fname}.mp4" if is_vid else f"{fname}.jpg")
            url    = _best_video(item) if is_vid else _best_image(item)
            ftype  = "video" if is_vid else "image"

            if dest.exists():
                log_fn(f"  ↳ [{idx}] exists, skip", SUBTEXT)
            elif url:
                try:
                    log_fn(f"  ↳ [{idx}] {ftype} …", TEXT)
                    _dl(sess, url, dest)
                    log_fn(f"       ✔ {dest.name}", SUCCESS)
                except Exception as e:
                    log_fn(f"       ✘ {e}", ERROR)
            else:
                log_fn(f"  ↳ [{idx}] no URL", GOLD)

            meta["items"].append({"index": idx, "type": ftype, "file": dest.name})
            done_cnt += 1
            progress_fn(done_cnt, max(total, done_cnt))
            time.sleep(0.4)

        with open(coll_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

    log_fn(f"\n✅  Done! → {user_dir.resolve()}", SUCCESS)
    done_fn(True)


# ─── GUI ─────────────────────────────────────────────────────────────────────────
class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Highlights Downloader")
        self.geometry("780x680")
        self.resizable(True, True)
        self.configure(bg=BG)
        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=SURFACE, height=64)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(hdr, text="✦ Highlights Sync", bg=SURFACE, fg=TEXT,
                 font=FONT_HEAD).pack(side="left", padx=20, pady=14)
        tk.Label(hdr, text="instagram → local", bg=SURFACE, fg=SUBTEXT,
                 font=FONT_SUB).pack(side="left", pady=14)

        form = tk.Frame(self, bg=CARD, padx=24, pady=20)
        form.pack(fill="x", padx=20, pady=(20,0))

        labels = ["Instagram username", "User ID  (auto-detected or manual)", "Session ID  (auto-detected)"]
        for col, txt in enumerate(labels):
            tk.Label(form, text=txt, bg=CARD, fg=SUBTEXT,
                     font=("Segoe UI", 9)).grid(row=0, column=col, sticky="w",
                     padx=(12 if col else 0, 0))

        self.username_var = tk.StringVar()
        self.userid_var   = tk.StringVar()
        self.session_var  = tk.StringVar()

        for col, (var, show, w) in enumerate([
            (self.username_var, "", 16),
            (self.userid_var,   "", 16),
            (self.session_var,  "•", 32),
        ]):
            tk.Entry(form, textvariable=var, bg=SURFACE, fg=TEXT,
                     insertbackground=TEXT, relief="flat", font=FONT_SUB,
                     show=show, width=w).grid(
                row=1, column=col, sticky="ew",
                padx=(12 if col else 0, 0), pady=(4,12), ipady=6)

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)
        form.columnconfigure(2, weight=2)

        self.detect_lbl = tk.Label(form, text="", bg=CARD, fg=SUBTEXT,
                                    font=("Segoe UI", 9))
        self.detect_lbl.grid(row=2, column=0, columnspan=3, sticky="w")

        prog_frame = tk.Frame(self, bg=BG, padx=20, pady=10)
        prog_frame.pack(fill="x")
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("IG.Horizontal.TProgressbar",
                        troughcolor=SURFACE, background=ACCENT,
                        bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT2, thickness=8)
        self.progress = ttk.Progressbar(prog_frame, style="IG.Horizontal.TProgressbar",
                                         mode="determinate")
        self.progress.pack(fill="x")
        self.prog_lbl = tk.Label(prog_frame, text="Ready", bg=BG, fg=SUBTEXT,
                                  font=("Segoe UI", 9))
        self.prog_lbl.pack(anchor="e")

        log_frame = tk.Frame(self, bg=SURFACE, padx=2, pady=2)
        log_frame.pack(fill="both", expand=True, padx=20)
        self.log = scrolledtext.ScrolledText(
            log_frame, bg="#0d0d0d", fg=TEXT, font=FONT_MONO,
            relief="flat", wrap="word", state="disabled",
            selectbackground=ACCENT2, padx=12, pady=10)
        self.log.pack(fill="both", expand=True)
        for tag, col in [("error",ERROR),("success",SUCCESS),("accent",ACCENT),
                         ("sub",SUBTEXT),("gold",GOLD)]:
            self.log.tag_configure(tag, foreground=col)

        bot = tk.Frame(self, bg=SURFACE, padx=20, pady=14)
        bot.pack(fill="x", side="bottom")
        self.sync_btn = tk.Button(
            bot, text="⬇  Sync Highlights", command=self._start_download,
            bg=ACCENT, fg="white", activebackground=ACCENT2, activeforeground="white",
            relief="flat", font=FONT_BTN, cursor="hand2", padx=24, pady=10)
        self.sync_btn.pack(side="right")
        tk.Button(bot, text="📂  Open folder", command=self._open_folder,
                  bg=CARD, fg=TEXT, activebackground=SURFACE, activeforeground=TEXT,
                  relief="flat", font=FONT_BTN, cursor="hand2",
                  padx=16, pady=10).pack(side="right", padx=(0,10))
        self.status_dot = tk.Label(bot, text="●", fg=SUBTEXT, bg=SURFACE,
                                    font=("Segoe UI", 14))
        self.status_dot.pack(side="left")
        self.status_lbl = tk.Label(bot, text="Idle", bg=SURFACE, fg=SUBTEXT, font=FONT_SUB)
        self.status_lbl.pack(side="left", padx=6)

    def _auto_detect(self):
        profile = find_firefox_profile()
        if not profile:
            self.detect_lbl.config(
                text="⚠  Firefox profile not found – paste session ID manually", fg=GOLD)
            return
        cookies = extract_instagram_cookies(profile)
        sid = cookies.get("sessionid")
        uid = cookies.get("ds_user_id")
        if sid:
            self.session_var.set(sid)
            if uid:
                self.userid_var.set(uid)
                self.detect_lbl.config(
                    text=f"✔  Session & User ID ({uid}) auto-detected", fg=SUCCESS)
            else:
                self.detect_lbl.config(
                    text="✔  Session detected (User ID missing — enter manually)", fg=GOLD)
        else:
            self.detect_lbl.config(
                text="⚠  No Instagram session in Firefox – log in first", fg=GOLD)

    def _log(self, msg: str, colour: str = TEXT):
        tag = {ERROR:"error",SUCCESS:"success",ACCENT:"accent",SUBTEXT:"sub",GOLD:"gold"}.get(colour,"")
        self.log.config(state="normal")
        self.log.insert("end", msg+"\n", tag if tag else ())
        self.log.see("end")
        self.log.config(state="disabled")

    def _set_progress(self, done, total):
        pct = int(done/total*100) if total else 0
        self.progress["value"] = pct
        self.prog_lbl.config(text=f"{done} / {total}  ({pct}%)")

    def _set_status(self, text, colour=SUBTEXT):
        self.status_dot.config(fg=colour)
        self.status_lbl.config(text=text, fg=colour)

    def _start_download(self):
        username = self.username_var.get().strip().lstrip("@")
        user_id  = self.userid_var.get().strip()
        session  = self.session_var.get().strip()
        if not username:
            messagebox.showwarning("Missing", "Enter Instagram username."); return
        if not session:
            messagebox.showwarning("Missing", "No session ID. Log into Instagram in Firefox."); return
        self.sync_btn.config(state="disabled", text="Syncing …")
        self.progress["value"] = 0
        self._set_status("Downloading …", ACCENT)
        self._log(f"Starting sync for @{username}  –  {datetime.now().strftime('%H:%M:%S')}")

        def run():
            download_highlights(
                username, user_id, session,
                log_fn=lambda m, c=TEXT: self.after(0, self._log, m, c),
                progress_fn=lambda d, t: self.after(0, self._set_progress, d, t),
                done_fn=lambda ok: self.after(0, self._on_done, ok),
            )
        threading.Thread(target=run, daemon=True).start()

    def _on_done(self, ok):
        self.sync_btn.config(state="normal", text="⬇  Sync Highlights")
        self._set_status("Done" if ok else "Failed", SUCCESS if ok else ERROR)
        if ok: self.progress["value"] = 100

    def _open_folder(self):
        HIGHLIGHTS_DIR.mkdir(exist_ok=True)
        os.startfile(HIGHLIGHTS_DIR.resolve())


if __name__ == "__main__":
    DownloaderApp().mainloop()