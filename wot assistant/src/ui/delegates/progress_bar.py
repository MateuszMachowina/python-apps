from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from ...styles.theme import Theme

class WinRateBarDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        win_rate_data = index.data(Qt.ItemDataRole.UserRole)
        try:
            win_rate = float(win_rate_data) if win_rate_data is not None else 0.0
        except (ValueError, TypeError):
            win_rate = 0.0
            
        display_text = index.data(Qt.ItemDataRole.DisplayRole)
        if not display_text:
            display_text = f"{win_rate:.2f} %"
            
        rect = option.rect
        bar_height = 20
        bar_width = rect.width() - 20
        
        x = rect.x() + 10
        y = rect.y() + (rect.height() - bar_height) // 2
        
        # Background bar
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor('#1c2333'))
        painter.drawRoundedRect(x, y, bar_width, bar_height, 4, 4)
        
        # Filled portion
        fill_width = int(bar_width * (win_rate / 100.0))
        fake_wn8 = int(win_rate * 40)
        fill_color_hex = Theme.get_wn8_color(fake_wn8)
        
        if fill_width > 0:
            painter.setBrush(QColor(fill_color_hex))
            painter.drawRoundedRect(x, y, fill_width, bar_height, 4, 4)
            
        # Draw text
        font = painter.font()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)
        painter.setPen(QColor('#ffffff'))
        painter.drawText(x, y, bar_width, bar_height, Qt.AlignmentFlag.AlignCenter, display_text)
        
        painter.restore()
        
    def sizeHint(self, option, index):
        return QSize(120, 28)
