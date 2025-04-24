# 🐍 Simple Python Apps Collection

Welcome to my Python Apps Collection! Here I share various simple Python applications I've been working on. Each app serves as a fun way for me to learn and experiment with Python.

## 🧩 Apps

### 1. **World of Tanks Stats Viewer** 🎮

A lightweight CLI app to fetch and display World of Tanks player stats using the official API.

**Highlights:**
- 🔍 Search players by username  
- 📊 View battles, win rate, and global rating  
- 🛡️ See top-used tanks with detailed stats  
- 🎯 Filter tanks by tier  
- 🔐 Supports API key via `.env` or manual input

### 2. **FX Rates Checker** 💱

This mini-project includes two CLI scripts that fetch exchange rates from two different APIs: Fixer.io and ExchangeRate-API.

**Scripts:**
- `exchange-rates-fixer.py`: Fetches EUR-based rates via the **Fixer.io API**.  
- `exchange-rates-er.py`: Supports multiple base currencies via the **ExchangeRate-API**.

**Highlights:**
- 🔑 Secure API key management via `.env`
- 🔁 Continuous prompt for target currencies
- 🌍 Real-time currency data

### 3. **Currency Converter for Excel** 📊

Converts invoice amounts in Excel files from EUR to a target currency using real-time exchange rates.

**Highlights:**
- 📁 Supports `.xlsx` and `.xlsm` (macros preserved)
- 💱 Fetches live exchange rates from ExchangeRate-API
- 📌 Updates values directly in the spreadsheet
- 💾 Saves converted file with target currency in the name

---

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
