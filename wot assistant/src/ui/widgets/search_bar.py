from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt

class SearchBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('searchBar')
        self.setPlaceholderText('Search tank...')
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.clear()
            self.textChanged.emit("")
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(QColor('#8b949e'))
        pen.setWidth(2)
        painter.setPen(pen)
        
        y = self.height() // 2
        x = 12
        radius = 5
        
        # Magnifying glass circle
        painter.drawEllipse(x, y - radius - 1, radius * 2, radius * 2)
        # Handle
        painter.drawLine(x + radius + 2, y + 2, x + radius + 6, y + 6)
