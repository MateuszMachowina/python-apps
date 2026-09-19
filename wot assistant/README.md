# <img src="icon.png" width="40" height="40"> WoT Assistant Pro

An advanced, interactive graphical Python application (GUI) to explore player stats, track tank performance, and calculate **WN8** in real-time using Wargaming and XVM APIs.

## 🎯 Features

- 🔍 Search for World of Tanks players by username
- 📊 View **WTR**, **global WN8**, **win rate**, and **total battles** at a glance
- 📈 Real-time **WN8 calculation** for individual tanks based on current XVM Expected Values
- 🎚️ Advanced filtering by **Tier**, **Type**, **Nation**, **Favorites**, and **Minimum Battles**
- ⭐ Personal rating system: Rate your tanks for **Fun** and **Competitiveness** (1-5 stars)
- 🏅 Track **Marks of Excellence (MoE)** directly in the app
- ⚡ Blazing fast performance with local **SQLite database** caching and auto-downloaded tank icons
- 🔐 API key management via `.env` file

## 🧪 Requirements

Make sure you have these Python packages installed (all listed in `requirements.txt`):

```text
PyQt6
requests
python-dotenv
```

## 🛠️ Setup Instructions

1. **Clone or download this repository** to your local machine.

2. **Set up your API Key**:
   - Rename the provided `.env.example` file to `.env` (or create a new `.env` file).
   - Add your Wargaming API key inside:
   ```env
   API_KEY=your_api_key_here
   ```
   🔑 Don't have a key yet? Get one here: [Wargaming Developer Portal](https://developers.wargaming.net/)

3. **Open Command Prompt / Terminal**

4. **Navigate to the project folder**:  
   *(If your folder is on another drive, switch first by typing the drive letter)*
   
   ```bash
   D:
   cd "D:\Path\To\Your\Project"
   ```

5. **Install required libraries**:

   ```bash
   pip install -r requirements.txt
   ```

6. **Run the app**:

   ```bash
   python main.py
   ```

### 📦 Optional: Build your own `.exe` file

If you want to run the app without the black console window or share it easily, you can compile it into a single standalone executable using PyInstaller.

1. **Install PyInstaller**:
   ```bash
   pip install pyinstaller
   ```
2. **Build the executable**:
   ```bash
   pyinstaller --noconsole --onefile --icon=icon.ico main.py
   ```
*(Note: If your project has additional static assets inside the `src` folder, you might need to use the `--add-data` flag to include them in the `.exe`)*
  
3. **Once finished**, your ready-to-use `main.exe` (or `wot_assistant.exe` if you used `--name`) will be located in the newly created `dist` folder.

*(Note: Move the `.exe` file wherever you like, but always remember to keep your `.env` file and `wot_stats.db` database in the exact same folder next to it! Just make a shortcut to the `.exe` and place it in your preferred location.)*


## 💬 Notes

- The initial synchronization may take a bit longer than usual. The app will automatically create a local `wot_stats.db` database and an `icons_cache` folder.
- Designed for the EU region (`api.worldoftanks.eu`). You can adjust the `API_URL` variable in the `src/config.py` script for other regions if needed.

![WoT Stats Assistant Screenshot](screenshot.png)
