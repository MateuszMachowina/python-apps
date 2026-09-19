from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QSize
from ...styles.theme import Theme

class WN8BadgeDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        wn8_data = index.data(Qt.ItemDataRole.EditRole)
        try:
            wn8 = int(float(wn8_data)) if wn8_data is not None else 0
        except (ValueError, TypeError):
            wn8 = 0
            
        color_hex = Theme.get_wn8_color(wn8)
        color = QColor(color_hex)
        bg_color = QColor(color)
        bg_color.setAlpha(40)
        
        text = str(wn8)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()
        
        text_rect = fm.boundingRect(text)
        padding_x = 10
        padding_y = 4
        
        badge_width = text_rect.width() + padding_x * 2
        badge_height = fm.height() + padding_y * 2
        
        rect = option.rect
        x = rect.x() + (rect.width() - badge_width) // 2
        y = rect.y() + (rect.height() - badge_height) // 2
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(bg_color)
        painter.drawRoundedRect(x, y, badge_width, badge_height, 10, 10)
        
        painter.setPen(QColor('#ffffff'))
        painter.drawText(x, y, badge_width, badge_height, Qt.AlignmentFlag.AlignCenter, text)
        
        painter.restore()
        
    def sizeHint(self, option, index):
        return QSize(80, 30)
