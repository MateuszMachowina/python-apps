import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from src.styles import Theme
from src.ui.main_window import MainWindow
from src.utils.paths import get_resource_path

def main():
    # Ensure current working directory is the resource path so relative paths in QSS work correctly
    os.chdir(get_resource_path(''))
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Base style
    
    # Apply modern stylesheet
    app.setStyleSheet(Theme.load_stylesheet())
    
    # Set default font
    font = QFont(Theme.FONT_FAMILY, Theme.FONT_SIZE_BASE)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
