# 🐍 Python Apps

Welcome to my Python Apps Collection! Here I share various simple Python applications I've been working on. Each app serves as a fun way for me to learn and experiment with Python.

## 🧩 About the Projects

The apps in this collection vary in purpose and complexity, but they typically focus on:

- 🔍 Working with external APIs and real-time data
- 📊 Data processing, analysis, and visualization
- 💻 CLI tools and simple desktop applications
- 📁 File handling (e.g., Excel automation)
- 🎨 Building clean and functional user interfaces

Each project is designed to explore a specific concept or technology, often in a practical, hands-on way.

## ⚙️ Common Features

Depending on the project, you may find:

- 🔑 Secure handling of API keys (e.g., via .env)
- 🔁 Interactive command-line workflows
- 📊 Data transformation and reporting
- 🌍 Integration with third-party services
- 🖥️ Simple GUI applications (e.g., Tkinter-based tools)

## ⚙️ Technologies Used

- Python 3.13  
- `requests` (API communication)  
- `tabulate` (terminal table output)  
- `os` & `dotenv` (environment variable handling)  
- `openpyxl` (Excel file handling)  
- `tkinter` (file dialog for Excel script)

## 🚀 Installation & Running the Script

1. **Download the necessary files**:
   - The `.py` script you want to run
   - `requirements.txt` (if available)
   - other files if necessary

2. **Create a `.env` file** in the same folder as the script and add your API key (name can vary depending on the project):

   ```env
   API_KEY=your_api_key_here
   ```

3. **Open Command Prompt**

4. **Navigate to the script folder**:  
   *(If your script is on another drive, switch first by typing the drive letter)*

   ```bash
   E:
   cd "Path\To\Your\Script"
   ```

5. **Install required libraries**:
   
   *(if `requirements.txt` is available)*
   
   ```bash
   pip install -r requirements.txt
   ```

7. **Run the script**:

   ```bash
   python script_name.py
   ```

## 📦 Optional: Build your own `.exe` file

If you want to run the app without the black console window or share it easily, you can compile it into a single standalone executable using PyInstaller.

1. **Install PyInstaller**:
   ```bash
   py -m pip install pyinstaller
   ```
2. **Build the executable**:
   ```bash
   py -m PyInstaller --noconsole --onefile --icon=icon.ico app_name.py
   ```
(Note: If you are not using a custom icon, simply remove `--icon=icon.ico` from the command).
  
3. **Once finished**, your ready-to-use `app_name.exe` will be located in the newly created `dist` folder.
