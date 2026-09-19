from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QPushButton, QButtonGroup
from PyQt6.QtCore import pyqtSignal, Qt

class Sidebar(QFrame):
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sidebar')
        self.setFixedWidth(220)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        layout = QVBoxLayout(self)
        
        # Title and version
        title_label = QLabel('WoT Assistant')
        title_label.setObjectName('sidebarTitle')
        layout.addWidget(title_label)
        
        # Spacer
        layout.addSpacing(20)
        
        # Navigation buttons
        nav_items = [
            ('📊  Dashboard', 'dashboard'),
            ('🎯  Tanks', 'tanks'),
            ('📈  Sessions', 'session'),
            ('⚙️  Settings', 'settings')
        ]
        
        self.buttons = {}
        for idx, (text, page) in enumerate(nav_items):
            btn = QPushButton(text)
            btn.setObjectName('sidebarBtn')
            btn.setCheckable(True)
            btn.setProperty('page', page)
            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)
            self.buttons[page] = btn
            
            btn.clicked.connect(lambda checked, p=page: self.page_changed.emit(p))
            
        # Default checked
        self.buttons['dashboard'].setChecked(True)
        
        # Bottom stretch
        layout.addStretch()
        
        # Copyright
        copyright_label = QLabel('© 2026 <a href="https://github.com/MateuszMachowina" style="color: #8b949e; text-decoration: none;">Mateusz Machowina</a>')
        copyright_label.setOpenExternalLinks(True)
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copyright_label.setStyleSheet('color: #8b949e;')
        layout.addWidget(copyright_label)
        
    def set_active_page(self, page: str):
        if page in self.buttons:
            self.buttons[page].setChecked(True)
            self.page_changed.emit(page)
