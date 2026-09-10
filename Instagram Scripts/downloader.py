"""Instagram Highlights Downloader — manual-session edition.

This application never reads browser profiles, cookie databases, passwords, or
other local credentials. It uses only the session token that the account owner
explicitly pastes into the window for the current run; the token is held in
memory and is never written to disk.
"""

import json
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


HIGHLIGHTS_DIR = Path("highlights")
IG_APP_ID = "936619743392459"

BG, SURFACE, CARD = "#0a0a0a", "#161616", "#1e1e1e"
ACCENT, ACCENT2 = "#c13584", "#833ab4"
TEXT, SUBTEXT, SUCCESS, ERROR, GOLD = "#f0f0f0", "#888888", "#2ecc71", "#e74c3c", "#f5a623"

_FLAG_HINT_RE = re.compile(
    r"[\U0001f1e6-\U0001f1ff]{2}\s*$|(?:\s|^)\[?[A-Za-z]{2}\]?\s*$"
)
_WINDOWS_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def fix_title_unicode(title: str) -> str:
    """Repair malformed UTF-16 surrogate pairs occasionally returned by Instagram."""
    if not title:
        return title
    try:
        title.encode("utf-8")
        return title
    except UnicodeEncodeError:
        try:
            return title.encode("utf-16", "surrogatepass").decode("utf-16")
        except UnicodeError:
            return title.encode("utf-8", "replace").decode("utf-8")


def collection_folder_name(title: str, reel_id: str) -> str:
    """Create a valid Windows folder name while preserving the original title in meta.json."""
    safe = "".join(char for char in title if char.isalnum() or char in " _-").strip(" .")
    if safe:
        return safe
    fallback = _WINDOWS_FORBIDDEN.sub("_", reel_id).strip(" .")
    return fallback or "untitled_highlight"


def make_session(session_id: str):
    import requests

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
    })
    # The user has supplied this value explicitly. Do not persist it anywhere.
    session.cookies.set("sessionid", session_id, domain=".instagram.com", path="/")
    return session


def api_headers() -> dict[str, str]:
    return {
        "Accept": "*/*",
        "X-IG-App-ID": IG_APP_ID,
        "X-Requested-With": "XMLHttpRequest",
    }


def resolve_user_id(session, username: str, supplied_id: str, log) -> str | None:
    if supplied_id:
        return supplied_id
    if not username:
        return None
    log(f"Resolving user ID for @{username} …", SUBTEXT)
    try:
        response = session.get(
            "https://www.instagram.com/api/v1/users/web_profile_info/",
            params={"username": username}, headers=api_headers(), timeout=20,
        )
        response.raise_for_status()
        return response.json().get("data", {}).get("user", {}).get("id")
    except Exception as exc:
        log(f"Could not resolve User ID: {exc}", ERROR)
        return None


def get_highlight_tray(session, user_id: str):
    response = session.get(
        f"https://www.instagram.com/api/v1/highlights/{user_id}/highlights_tray/",
        headers=api_headers(), timeout=20,
    )
    response.raise_for_status()
    return response.json().get("tray", [])


def get_reel_items(session, reel_id: str):
    reel_id = reel_id if reel_id.startswith("highlight:") else f"highlight:{reel_id}"
    response = session.get(
        "https://www.instagram.com/api/v1/feed/reels_media/",
        params={"reel_ids": reel_id}, headers=api_headers(), timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    reels = data.get("reels_media") or list(data.get("reels", {}).values())
    return reels[0].get("items", []) if reels else []


def best_media_url(item: dict, is_video: bool) -> str | None:
    if is_video:
        versions = item.get("video_versions") or []
    else:
        versions = (item.get("image_versions2") or {}).get("candidates") or []
    versions.sort(key=lambda version: version.get("width", 0) * version.get("height", 0), reverse=True)
    return versions[0].get("url") if versions else None


def download_file(session, url: str, target: Path):
    with session.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with target.open("wb") as file:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    file.write(chunk)


def cover_url_from(tray: dict) -> str | None:
    cover = tray.get("cover_media") or {}
    url = (cover.get("cropped_image_version") or {}).get("url")
    if url:
        return url
    candidates = (cover.get("image_versions2") or {}).get("candidates") or []
    return candidates[0].get("url") if candidates else None


def sync_highlights(username: str, user_id: str, session_id: str, log, progress) -> None:
    try:
        import requests  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install dependencies first: pip install -r requirements.txt") from exc

    session = make_session(session_id)
    resolved_id = resolve_user_id(session, username, user_id, log)
    if not resolved_id:
        raise RuntimeError("Enter a numeric User ID, or enter a valid username.")

    log("Fetching highlight collections …", SUBTEXT)
    try:
        trays = get_highlight_tray(session, resolved_id)
    except Exception as exc:
        raise RuntimeError(f"Could not load highlights: {exc}") from exc
    if not trays:
        log("No highlights were returned.", GOLD)
        return

    total = sum(tray.get("media_count", 0) for tray in trays) or len(trays)
    done = 0
    HIGHLIGHTS_DIR.mkdir(exist_ok=True)

    for tray in trays:
        title = fix_title_unicode(str(tray.get("title") or "Untitled"))
        reel_id = str(tray.get("id") or "")
        folder = HIGHLIGHTS_DIR / collection_folder_name(title, reel_id)
        folder.mkdir(exist_ok=True)
        log(f"\n📁  {title}", ACCENT)
        if _FLAG_HINT_RE.search(title):
            log("  ↳ country flag/code detected in the title", SUBTEXT)

        cover_file = folder / "cover.jpg"
        if not cover_file.exists() and (url := cover_url_from(tray)):
            try:
                download_file(session, url, cover_file)
            except Exception as exc:
                log(f"  ↳ cover download failed: {exc}", GOLD)

        try:
            items = get_reel_items(session, reel_id)
        except Exception as exc:
            log(f"  ✘ could not load items: {exc}", ERROR)
            continue
        if not items:
            log("  ↳ no items found", GOLD)
            continue

        meta = {
            "title": title,
            "id": reel_id,
            "cover": "cover.jpg",
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "items": [],
        }
        for index, item in enumerate(items, 1):
            is_video = item.get("media_type") == 2
            kind, suffix = ("video", ".mp4") if is_video else ("image", ".jpg")
            target = folder / f"{index:03d}{suffix}"
            if target.exists():
                log(f"  ↳ [{index}] already exists", SUBTEXT)
            elif url := best_media_url(item, is_video):
                try:
                    download_file(session, url, target)
                    log(f"  ↳ [{index}] saved {target.name}", SUCCESS)
                except Exception as exc:
                    log(f"  ✘ [{index}] download failed: {exc}", ERROR)
            else:
                log(f"  ✘ [{index}] no media URL", ERROR)
            meta["items"].append({"index": index, "type": kind, "file": target.name})
            done += 1
            progress(done, max(total, done))
            time.sleep(0.4)

        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


class DownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Highlights Downloader — Manual Session")
        self.geometry("760x680")
        self.configure(bg=BG)
        self._build()

    def _build(self):
        header = tk.Frame(self, bg=SURFACE, height=64)
        header.pack(fill="x"); header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(header, text="✦ Highlights Sync", bg=SURFACE, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left", padx=20)
        tk.Label(header, text="manual session", bg=SURFACE, fg=SUBTEXT, font=("Segoe UI", 11)).pack(side="left")

        form = tk.Frame(self, bg=CARD, padx=24, pady=18)
        form.pack(fill="x", padx=20, pady=20)
        self.username = tk.StringVar()
        self.user_id = tk.StringVar()
        self.session_id = tk.StringVar()
        fields = (("Instagram username (optional)", self.username, False),
                  ("Numeric User ID (recommended)", self.user_id, False),
                  ("Session ID — paste manually; never saved", self.session_id, True))
        for row, (label, variable, hidden) in enumerate(fields):
            tk.Label(form, text=label, bg=CARD, fg=SUBTEXT, font=("Segoe UI", 9)).grid(row=row * 2, column=0, sticky="w", pady=(0, 3))
            tk.Entry(form, textvariable=variable, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=("Segoe UI", 10), show="•" if hidden else "").grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 10), ipady=6)
        form.columnconfigure(0, weight=1)
        tk.Label(form, text="This app does not inspect Firefox, browser cookies, or local credentials. The pasted token remains only in memory for this run.",
                 bg=CARD, fg=GOLD, font=("Segoe UI", 9), wraplength=660, justify="left").grid(row=6, column=0, sticky="w", pady=(4, 0))

        panel = tk.Frame(self, bg=BG, padx=20)
        panel.pack(fill="x")
        self.progress = ttk.Progressbar(panel, mode="determinate")
        self.progress.pack(fill="x")
        self.progress_label = tk.Label(panel, text="Ready", bg=BG, fg=SUBTEXT, font=("Segoe UI", 9))
        self.progress_label.pack(anchor="e")

        self.log_box = scrolledtext.ScrolledText(self, bg="#0d0d0d", fg=TEXT, font=("Consolas", 9),
                                                   relief="flat", state="disabled", wrap="word", height=17)
        self.log_box.pack(fill="both", expand=True, padx=20, pady=12)
        self.button = tk.Button(self, text="⬇  Sync Highlights", command=self.start, bg=ACCENT, fg="white",
                                activebackground=ACCENT2, relief="flat", font=("Segoe UI", 11, "bold"), padx=24, pady=10)
        self.button.pack(anchor="e", padx=20, pady=(0, 16))

    def log(self, message, _colour=TEXT):
        self.log_box.config(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.config(state="disabled")

    def set_progress(self, done, total):
        percent = int(done / total * 100) if total else 0
        self.progress.config(value=percent)
        self.progress_label.config(text=f"{done} / {total} items ({percent}%)")

    def start(self):
        username, user_id, session_id = self.username.get().strip().lstrip("@"), self.user_id.get().strip(), self.session_id.get().strip()
        if not session_id:
            messagebox.showwarning("Session ID required", "Paste your own Instagram session ID. It is not read from the browser and is not saved.")
            return
        if not user_id and not username:
            messagebox.showwarning("Account required", "Enter a numeric User ID or Instagram username.")
            return
        self.button.config(state="disabled", text="Syncing …")
        def run():
            try:
                sync_highlights(username, user_id, session_id,
                                lambda message, colour=TEXT: self.after(0, self.log, message, colour),
                                lambda done, total: self.after(0, self.set_progress, done, total))
                self.after(0, self.finish, True)
            except Exception as exc:
                self.after(0, self.log, f"✘ {exc}", ERROR)
                self.after(0, self.finish, False)
        threading.Thread(target=run, daemon=True).start()

    def finish(self, success):
        self.button.config(state="normal", text="⬇  Sync Highlights")
        if success:
            self.progress.config(value=100)
            self.log("✅ Done", SUCCESS)


if __name__ == "__main__":
    DownloaderApp().mainloop()
