Icon Generator for WoT Assistant

A lightweight Python utility script designed to solve the problem of blurry or distorted Windows icons. It converts any PNG image into a professional-grade .ico file containing a full suite of resolutions.
🚀 Key Features

    Auto-Squaring: Automatically creates a transparent square canvas and centers your image (perfect for non-square tank renders).

    Multi-size Bundle: Packages multiple resolutions (from 16x16 up to 256x256) into a single .ico container. This ensures the icon stays crisp on the taskbar, desktop, and file explorer.

    Transparency Support: Full support for RGBA alpha channels to maintain clean edges.

🛠️ Requirements

This script requires the Pillow library for image processing:

pip install Pillow

📖 How to Use

    Place your source image (ikonka.png) in the same directory as the script.

    Run the generator:

    python generate_icon.py

    Your high-quality icon.ico will be generated instantly in the same folder.

💡 Why use this?

Standard online converters often only include a single small resolution (like 32x32), causing Windows to stretch the image and create "pixelated" icons. This script ensures that Windows always has the correct size available for every display mode.
