# 🛠️ Instagram Local Scripts

A set of four secure, locally running Python scripts for managing, downloading, and analyzing Instagram data.

Main advantage: The scripts do not require you to provide your username or password in the code. Instead, they automatically and securely read your active session from your local Mozilla Firefox browser profile.

## 📦 System Requirements

To fully use the tools, make sure you have:

- Python 3.8 or newer.
- Mozilla Firefox - you must be logged into your Instagram account on it.
- FFmpeg - required for rendering video and extracting thumbnails (you must download it, install it, and add it to your Windows PATH environment variables).
- VLC media player - required for playing videos in the highlights viewer (viewer.py script).

## Python Libraries Installation

Open your terminal and install the required packages:
``pip install requests pillow python-vlc``

## Available Tools

- 📥 Highlights Downloader (``downloader_highlights.py``)
A tool with a graphical user interface (GUI) for mass downloading saved highlights of any Instagram user.
Features: Downloads all videos and photos from highlighted stories and organizes them in a clear folder structure. It also creates meta.json files.
Usage: Enter the username in the GUI and click Sync.
- 👁️ Highlights Viewer (``viewer_highlights.py``)
A local viewer for downloaded highlights. Plays photos and videos imitating the classic Instagram interface (progress bars at the top, avatar, smooth transitions).
Features: Video support (thanks to VLC), supersampling for smooth interfaces, automatic downloading of national emoji flags, adjustable photo display duration.
Requirements: Prior data download using the Downloader.
- 🎬 Highlight Exporter (``exporter_highlights.py``)
A converter that turns a folder of downloaded highlight frames into a single, cohesive .mp4 file.
Features: The resulting video looks like a screen recording from a smartphone. The script automatically adds black backgrounds, the Instagram interface, animated progress bars, and applies smooth transitions (crossfades) between video clips.
- 🕵️‍♂️ Followers Tracker (``unfollowers_tracker.py``)
A console script that analyzes the dynamics of your followers and following.
Features: Saves the account state and generates a clear report in a .txt file upon the next run. You will find out:
* Who stopped following you (unfollowers),
* Who newly started following you,
* Who (among those you follow) does not follow you back (non-followers).

## 🔒 Security and Privacy (VERY IMPORTANT)

These scripts operate on your private data. If you intend to fork, download, or share this repository further, make sure you do not push your private media or identifiers to the server.

Remember to include a .gitignore file in your project with the following content:

- Ignore downloaded media and exported videos
highlights/
exports/

- Ignore databases and follower tracking reports (they contain your account ID)
followers_state_*.json
raport_*.txt

- Downloaded flags from the API
flags/

- Python environment temporary files
**pycache**/
*.pyc

## ⚠️ Legal Disclaimer

This project was created solely for educational and hobbyist purposes. It is in no way affiliated with Meta Platforms, Inc. or Instagram.

The scripts use unofficial Instagram API endpoints.
Use them responsibly - overly aggressive and frequent API requests (especially in the tracker.py and downloader.py scripts) can result in a temporary ban (Rate Limit - Error 429) on your account by Instagram's security mechanisms.
A safe time delay is embedded in the tracker.py script. Do not reduce it if you do not want to risk a ban!
