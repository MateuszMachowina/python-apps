from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from ..config import API_KEY

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        title = QLabel('Settings')
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        info_label = QLabel('Version: v8.0\nAPI Status: Active')
        layout.addWidget(info_label)
        
        masked_key = API_KEY[:4] + '*' * (len(API_KEY) - 4) if API_KEY and len(API_KEY) > 4 else 'None'
        key_label = QLabel(f'API Key: {masked_key}')
        layout.addWidget(key_label)
        
        clear_cache_btn = QPushButton('Clear icon cache')
        clear_cache_btn.setFixedWidth(200)
        layout.addWidget(clear_cache_btn)
        
        about_label = QLabel('WoT Stats Assistant v8.0')
        about_label.setWordWrap(True)
        layout.addWidget(about_label)
        
        layout.addStretch()
