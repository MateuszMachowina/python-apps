# 🎯 Icon Generator for WoT Assistant

A lightweight Python utility that solves the problem of blurry or distorted Windows icons.  
It converts any PNG image into a high-quality `.ico` file containing a full set of resolutions.

---

## 🚀 Key Features

- **Auto-Squaring**  
  Automatically creates a transparent square canvas and centers your image — perfect for non-square renders (e.g. tanks).

- **Multi-size Bundle**  
  Generates a single `.ico` file with multiple resolutions (from **16×16 up to 256×256**), ensuring sharp icons across:
  - taskbar  
  - desktop  
  - file explorer  

- **Transparency Support**  
  Full support for RGBA alpha channels, preserving clean edges and smooth visuals.

---

## 🛠️ Requirements

This script uses the **Pillow** library for image processing:

```bash
pip install Pillow
```

## 📖 Usage
1. Place your source image (e.g. ikonka.png) in the same directory as the script.
2. Run the generator:
```python icon_maker.py```
3. Done!
Your high-quality icon.ico will be created in the same folder.

## 💡 Why use this?

Most online converters generate only a single low-resolution icon (e.g. 32×32).
Windows then scales it up, which leads to blurry or pixelated results.

This tool avoids that problem by embedding multiple resolutions into one .ico file, so Windows always picks the optimal size for each context.

## 📦 Output
```icon.ico``` — optimized, multi-resolution Windows icon ready for use.

## 🧰 Use Cases
Desktop applications
Game tools (like WoT Assistant)
Custom shortcuts
Installer assets

## ✨ Tip

For best results, use a high-resolution PNG (at least 512×512) with a transparent background.
