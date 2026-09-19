from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtCore import Qt

class StatCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName('dashCard')
        self.setMinimumWidth(180)
        self.setFixedHeight(140)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(10)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName('cardTitle')
        
        self.value_layout = QHBoxLayout()
        self.value_layout.setContentsMargins(0, 0, 0, 0)
        
        self.icon_label = QLabel()
        self.icon_label.hide()
        
        self.value_label = QLabel('-')
        self.value_label.setObjectName('cardValue')
        
        self.value_layout.addWidget(self.icon_label)
        self.value_layout.addWidget(self.value_label)
        self.value_layout.addStretch()
        
        self.subtext_label = QLabel('')
        self.subtext_label.setObjectName('cardSubtext')
        
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.value_layout)
        self.main_layout.addWidget(self.subtext_label)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

    def set_value(self, value: str, color: str = None):
        """Updates cardValue text and optionally sets color."""
        self.icon_label.hide()
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color};")
            
    def set_subtext(self, text: str):
        """Updates cardSubtext."""
        self.subtext_label.setText(text)
        
    def set_icon_and_text(self, pixmap: QPixmap, text: str):
        """Shows an icon next to the value text."""
        self.icon_label.setPixmap(pixmap)
        self.icon_label.show()
        self.value_label.setText(text)
