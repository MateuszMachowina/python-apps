# 🎮 World of Tanks Stats Viewer

A simple and interactive Python app to explore player stats from **World of Tanks** using the official Wargaming API.

## 🎯 Features

- 🔍 Search for World of Tanks players by username  
- 📊 View **total battles**, **win rate**, and **global rating**  
- 🛡️ See top-used tanks with detailed stats  
- 🎚️ Filter tanks by tier (e.g. 6,7,8 or all)  
- 🏅 Display **mastery badges**, **average damage**, **frags**, and **max frags**  
- 🔄 Easily switch between players or sessions  
- 🔐 API key management via `.env` file or manual input

## 🧪 Requirements

Make sure you have these Python packages installed:

```
requests  
tabulate  
python-dotenv
```

## 🛠️ Setup Instructions

1. **Download the following files**:
   - The script file (`wot_stats_viewer.py`)
   - `requirements.txt`

2. **Create a `.env` file** in the same folder and add your API key:

   ```env
   API_KEY=your_api_key_here
   ```

   🔑 Don't have a key yet? Get one here: [Wargaming Developer Portal](https://developers.wargaming.net/)

3. **Open Command Prompt / Terminal**

4. **Navigate to the script folder**:  
   *(If your script is on another drive, switch first by typing the drive letter)*
   
   ```bash
   E:
   cd "C:\Path\To\Your\Script"
   ```

6. **Install required libraries**:

   ```bash
   pip install -r requirements.txt
   ```

7. **Run the app**:

   ```bash
   python wot_stats_viewer.py
   ```

## 💬 Notes

- No API key in `.env`? The app will ask for one on launch.
- Designed for EU region (`api.worldoftanks.eu`); you can adjust for other regions if needed.
- Easily extendable for additional player or tank data! 

![World of Tanks Stats Viewer Screenshot](assets/screenshot.png)

