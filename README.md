# Simple Python Apps Collection

Welcome to my Python Apps Collection! Here I share various simple Python applications I've been working on. Each app serves as a fun way for me to learn and experiment with Python.

## Apps

### 1. **World of Tanks Stats Viewer**

A simple app that allows users to search for their World of Tanks player statistics and view detailed information about their most-used tanks.

**Features:**
- Search World of Tanks players by username  
- View total battles, win rate, and global rating  
- Display top-used tanks with detailed stats  
- Filter tanks by tier  
- Show mastery badges, average damage, frags, and more  
- Switch easily between players or sessions  
- API key handling via `.env` file or manual input  

### 2. **Other Apps**

This repository will continue to grow with different mini-projects I build as I learn more Python. Stay tuned for more!

## Technologies Used

- Python 3.13  
- `requests` (for API calls)  
- `tabulate` (for tabular output formatting)  
- `os` (for environment variable access)  
- `python-dotenv` (for loading `.env` files)

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/MateuszMachowina/python-apps.git
    cd python-apps
    ```

2. Install the required packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the project root and add your API key, for example [World of Tanks API key](https://developers.wargaming.net/):

    ```env
    API_KEY=your_api_key_here
    ```

4. Run the desired application:

    ```bash
    python app_name.py
    ```
