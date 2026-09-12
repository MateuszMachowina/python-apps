# ✦ Instagram Local Scripts

A set of Python scripts for downloading, viewing, exporting, and tracking your Instagram data - all running locally on your machine, no third-party services involved.

**Key advantage:** The scripts never touch your browser, cookies, or saved passwords. You paste your own Instagram session ID by hand for each sync — it's held only in memory for that run and is never written to disk.

---

## 📦 Requirements

| Tool | Why it's needed |
|------|----------------|
| **Python 3.10+** | Runtime for all scripts |
| **An Instagram session ID** | Grabbed manually from your browser (see below) and pasted into each tool — nothing is read automatically |
| **FFmpeg** | Video processing and thumbnail extraction — add to Windows PATH |
| **VLC Media Player** | Video playback in the viewer — must be 64-bit, matching Python |

> Built and tested on Windows (font paths and the "Open folder" buttons are Windows-specific). The core download/export logic is plain Python and should run elsewhere, but a few conveniences won't.

### Install Python dependencies

```
pip install requests pillow python-vlc
```

### Getting a session ID

None of these tools read your browser anymore. To get a `sessionid`: log into Instagram in any browser, open dev tools → Application/Storage → Cookies → `instagram.com`, and copy the value of the `sessionid` cookie. Paste it into the tool's Session ID field when you sync. It's never saved to disk by any of these scripts.

---

## 🗂️ Folder structure

```
project/
├── downloader_highlights.py
├── viewer_highlights.py
├── export_highlights.py
├── unfollowers_tracker.py
│
├── highlights/                  ← created by downloader
│   └── Example/
│       ├── cover.jpg
│       ├── 001.mp4
│       ├── 002.jpg
│       └── meta.json
│
├── exports/                     ← created by exporter
│   └── Example.mp4
│
├── flags/                       ← flag PNGs, auto-downloaded and cached
│   ├── pl.png
│   └── sg.png
│
└── unfollowers_data/            ← created by tracker
    ├── profiles.json
    └── <user_id>/
        └── current_state.json
```

Highlights and exports aren't split into per-account subfolders — everything you sync lands together in `highlights/` and `exports/`, named after each highlight's title. The tracker is the one tool that keeps multiple accounts separate, via its own profile list.

---

## 📥 `downloader_highlights.py` — Highlights Downloader

Downloads all highlights from any Instagram account you have access to, using a session ID you paste in by hand.

**Features:**
- Manual session only — never inspects Firefox, cookie databases, or saved passwords; the token lives in memory for the run and nowhere else
- Numeric User ID field skips the username-lookup API call entirely (the call most likely to get rate-limited)
- Downloads original quality MP4s and JPEGs at the highest available resolution, plus the highlight's cover image (`cover.jpg`)
- Skips already-downloaded files on re-run — safe to sync repeatedly
- Repairs titles Instagram occasionally sends with broken emoji encoding (a real API quirk affecting flag emoji) instead of failing on them
- Always produces a valid folder name, even for a title that's pure emoji with nothing else usable in it
- Logs a hint whenever a title looks like it contains a flag emoji or country code, so you can confirm Instagram actually sent one
- Saves `meta.json` alongside each collection for use by the viewer and exporter

**Usage:**
1. Run `python downloader_highlights.py`
2. Paste your session ID (see [Getting a session ID](#getting-a-session-id) above)
3. Enter a numeric User ID if you have one, or an Instagram username to look it up
4. Click **⬇ Sync Highlights**

> **💡 Tip on 429 errors:** Instagram rate-limits repeated requests from the same IP. If you see a 429, wait 15–30 minutes before trying again. Since the app no longer auto-detects your User ID, grab it once from Instagram's own network requests in your browser's dev tools and paste it into the User ID field — that skips the lookup call that most often triggers the limit.

---

## 👁️ `viewer_highlights.py` — Highlights Viewer

A local viewer that plays your downloaded highlights with an Instagram-style interface.

**Features:**
- Sidebar with gradient avatar rings, smooth supersampled thumbnails, and cover images
- Story progress strips and a header row with avatar, collection title, country flag, and a `4 / 21`-style counter
- Click the left/right half of the video to go prev/next — just like Instagram
- VLC-powered video playback with original audio
- Country flags downloaded automatically and cached to `flags/`
- Adjustable photo display duration (the `+`/`−` control in the top-right corner)
- Keyboard shortcuts: `←` `→` to navigate, `Space` to pause, `↑` `↓` to switch collections, `Esc` to close

**Usage:**
```
python viewer_highlights.py
```

Requires highlights to be downloaded first with `downloader_highlights.py`.

---

## 🎬 `export_highlights.py` — Highlight Exporter

Converts downloaded highlight collections into single MP4 files that look like a real Instagram story being viewed.

**Features:**
- **1080×1920** output (Instagram story resolution)
- Instagram-accurate overlay: dark gradient scrim, progress bars, plain circular avatar with a soft shadow (no gradient ring — real Instagram only shows that in the profile tray, not while a story is actually playing), username, country flag, and the "•••" / "✕" icons
- Optional blue verified badge — set `"verified": true` on a collection in its `meta.json`
- Optional "n/n" counter under the username (on by default, toggle in the GUI — flagged as non-standard since real Instagram doesn't show one)
- Optional bottom "Send message" reply bar with heart/share icons, matching the view you'd get looking at someone else's story (off by default)
- Original audio from video clips is extracted and mixed back in at the correct offset, in sync even across clips with different frame rates (toggle to mute)
- Smooth ~0.3s crossfade transitions between clips
- Titles that are entirely emoji (no letters or numbers at all) render using Windows' emoji font so they show correctly instead of as boxes — Windows-only; other platforms fall back to plain text
- Configurable photo display duration (3 seconds by default)
- Scrollable checklist to export exactly the highlights you want, or everything at once
- Outputs to `exports/<highlight_title>.mp4`

**Usage:**
```
python export_highlights.py
```

Requires `ffmpeg` on PATH and highlights downloaded first.

---

## 🕵️ `unfollowers_tracker.py` — Unfollowers Tracker

A local dashboard for tracking who doesn't follow you back and what's changed since your last check — across as many accounts as you like. (Note: the interface itself is in Polish.)

**Features:**
- Save any number of Instagram accounts locally by name and numeric User ID, and switch between them in the sidebar
- Session ID is pasted per sync through a popup dialog and is never saved — same manual, memory-only approach as the downloader
- Compares the current follower/following lists against the last saved snapshot to work out who's new, who unfollowed you, and who you follow that doesn't follow back
- Four browsable, searchable lists per account: non-followers, new followers, people who unfollowed you, and your full follower list
- Summary cards show follower/following counts and the last sync time at a glance
- Built-in 4-second delay between paginated requests to avoid rate limiting
- Clear error messages if Instagram rate-limits or rejects a request

**Usage:**
```
python unfollowers_tracker.py
```

Add a profile (name + numeric User ID), select it, then click **Synchronizuj** and paste a session ID to run a sync. Data for each account is saved under `unfollowers_data/`, so re-running later shows what changed.

---

## 🔒 Security & Privacy

These scripts run entirely on your local machine. None of them read your browser, cookie storage, or saved passwords, and none of them send your credentials anywhere except directly to Instagram. Every session ID is something you paste in by hand for that run, held only in memory, and never written to disk.

**Never commit your personal data to version control.** Add this to your `.gitignore`:

```
highlights/
exports/
flags/
unfollowers_data/
__pycache__/
*.pyc
```

---

## 🛠️ Troubleshooting

**Session ID rejected / requests fail right away**
Your pasted `sessionid` has probably expired. Log into Instagram again in your browser and copy a fresh value from the `instagram.com` cookies.

**VLC not working / black video screen**
Make sure you have the **64-bit** version of VLC installed matching your Python. Try adding `C:\Program Files\VideoLAN\VLC` to your system PATH.

**FFmpeg not found**
Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add the `bin/` folder to your Windows PATH environment variable. Restart your terminal after.

**Error 429 — rate limited**
Instagram temporarily blocked requests from your IP. Wait 15–30 minutes. In the downloader, paste your numeric User ID into the User ID field to skip the lookup call that usually triggers this; the tracker's built-in 4-second delay between pages exists for the same reason — don't reduce it.

**Thumbnails missing in viewer sidebar**
FFmpeg is required for extracting video thumbnails. Install it and add it to PATH.

**Flags not showing**
Flags are only added when a highlight's title ends in a real flag emoji or a plain two-letter country code (like `US` or `[US]`) — the downloader's log tells you when it spots one. Flag images themselves are downloaded from `flagcdn.com` on first use, so you'll need an internet connection the first time; after that they're cached locally in `flags/` and work offline.

**A highlight titled entirely in emoji doesn't export cleanly**
Emoji-only titles rely on Windows' built-in emoji font in the exporter. This only works on Windows — elsewhere, that title will fall back to the plain text font.

---

## ⚠️ Legal Disclaimer

This project is for personal, educational use only. It is not affiliated with Meta Platforms, Inc. or Instagram in any way.

The scripts use unofficial Instagram internal API endpoints which may change without notice. Use them responsibly — excessive or frequent automated requests can trigger Instagram's rate limiting (Error 429) or temporary account restrictions.
