# PackOpenerF15 Data Tools 🛠️

This repository contains Python scripts and supporting files used to prepare and manage the data and images for the **FIFA 15 Pack Opener** web simulator. These tools handle CSV-to-JSON conversion, image verification, format conversion, and maintain the master player table.

[Link to the main project ⚽](https://github.com/MateuszMachowina/PackOpenerF15)

---
## 📂 Contents

- `csv_to_json.py` – Converts raw CSV player data into a structured JSON format for use in the simulator.  
- `images_checker.py` – Verifies that all required player, club, and nation images exist and are correctly named; reports any missing or inconsistent files.  
- `webp_to_png.py` – Converts WebP image files (from the source data) into PNG format compatible with the web application.  
- `players_table.xlsx` – Master Excel table containing all players, their ratings, positions, card versions, and other statistics used to generate card data.

---

## ⚙️ Usage

1. **Prepare the CSV** – Place the raw CSV player data in the repository folder.  
2. **Run `csv_to_json.py`** – Generate `players.json` to be used by the simulator.  
3. **Run `images_checker.py`** – Ensure all image assets are present and correctly named.  
4. **Run `webp_to_png.py`** – Convert any WebP images from the source to PNG format for the web app.  

> ⚠️ Make sure Python 3.x is installed and required packages (if any) are available before running the scripts.

---

## 📊 Notes

- The tools were created to automate the preparation of **408 players** and **720 cards** for the simulator.  
- All graphics and data originally come from **Foodbin** and **SoFIFA.com**.  
- This repository is **non-commercial** and intended for **personal use and educational purposes**.

---

## 👨‍💻 Author

[Mateusz Machowina – © 2025](https://github.com/MateuszMachowina)
