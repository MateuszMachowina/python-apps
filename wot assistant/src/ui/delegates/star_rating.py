from PyQt6.QtWidgets import QStyledItemDelegate
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QSize, QEvent

class StarRatingDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.star_active = QColor('#fbbf24')
        self.star_inactive = QColor('#3d444d')
        self.font_size = 16
        
    def paint(self, painter: QPainter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rating = index.data(Qt.ItemDataRole.EditRole)
        try:
            rating = int(rating)
        except (ValueError, TypeError):
            rating = 0
            
        font = painter.font()
        font.setPointSize(self.font_size)
        painter.setFont(font)
        
        rect = option.rect
        star_width = painter.fontMetrics().horizontalAdvance("★")
        
        total_width = star_width * 5
        start_x = rect.x() + (rect.width() - total_width) // 2
        y = rect.y() + (rect.height() + painter.fontMetrics().ascent() - painter.fontMetrics().descent()) // 2
        
        for i in range(5):
            painter.setPen(self.star_active if i < rating else self.star_inactive)
            painter.drawText(start_x + i * star_width, y, "★")
            
        painter.restore()
        
    def sizeHint(self, option, index):
        font = option.font
        font.setPointSize(self.font_size)
        fm = option.fontMetrics
        return QSize(fm.horizontalAdvance("★") * 5 + 10, fm.height() + 10)
        
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            rect = option.rect
            star_width = option.fontMetrics.horizontalAdvance("★")
            total_width = star_width * 5
            start_x = rect.x() + (rect.width() - total_width) // 2
            
            click_x = event.position().x()
            if start_x <= click_x <= start_x + total_width:
                rating = int((click_x - start_x) // star_width) + 1
                model.setData(index, rating, Qt.ItemDataRole.EditRole)
                return True
        return super().editorEvent(event, model, option, index)
