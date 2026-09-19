import os
import sys

def get_project_root() -> str:
    """Gets the persistent root folder for data (DB, icon cache)."""
    if getattr(sys, 'frozen', False):
        # If running as an executable, use the folder where the .exe is located
        return os.path.dirname(sys.executable)
    else:
        # If running as script, use the folder two levels up from this file (wot assistant v8.0)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_resource_path(relative_path: str) -> str:
    """Gets the path to bundled resources (assets, styles)."""
    if getattr(sys, 'frozen', False):
        # PyInstaller extracts resources to _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Running as script, use project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base_path, relative_path)
