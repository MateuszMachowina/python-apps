import os
import requests
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPolygon, QPen, QBrush
from PyQt6.QtCore import Qt, QPoint
from .paths import get_project_root

class IconCache:
    def __init__(self, cache_dir='icons_cache'):
        self.cache_dir = os.path.join(get_project_root(), cache_dir)
        if not os.path.exists(self.cache_dir): 
            os.makedirs(self.cache_dir)

    def get_icon_path(self, tank_id: int) -> str:
        return os.path.join(self.cache_dir, f"{tank_id}.png")

    def download_icon(self, tank_id: int, url: str) -> bool:
        path = self.get_icon_path(tank_id)
        if not os.path.exists(path) and url:
            try:
                r = requests.get(url, timeout=3)
                if r.status_code == 200:
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    return True
            except requests.RequestException:
                pass
        return False

    def get_pixmap(self, tank_id: int, url: str = None) -> QPixmap | None:
        return self.get_pixmap_by_name(str(tank_id), url)

    def get_pixmap_by_name(self, name: str, url: str = None) -> QPixmap | None:
        path = os.path.join(self.cache_dir, f"{name}.png")
        if not os.path.exists(path):
            if url:
                try:
                    r = requests.get(url, timeout=3)
                    if r.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(r.content)
                except requests.RequestException:
                    pass
        
        if os.path.exists(path):
            return QPixmap(path)
        return None

    def get_class_icon(self, class_name: str, color='#8b949e', size=20) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(color)))
        
        center = size / 2.0
        
        if class_name == 'lightTank':
            poly = QPolygon([
                QPoint(int(center), 2), QPoint(size - 2, int(center)),
                QPoint(int(center), size - 2), QPoint(2, int(center))
            ])
            painter.drawPolygon(poly)
        elif class_name == 'AT-SPG':
            poly = QPolygon([
                QPoint(2, 4), QPoint(size - 2, 4), QPoint(int(center), size - 4)
            ])
            painter.drawPolygon(poly)
        elif class_name == 'SPG':
            painter.drawRect(4, 4, size - 8, size - 8)
        elif class_name == 'mediumTank':
            from PyQt6.QtCore import QRectF
            painter.translate(center, center)
            painter.rotate(45)
            w = size * 0.55
            gap = 1.5
            painter.drawRect(QRectF(-w/2, -w/2, w/2 - gap/2.0, w))
            painter.drawRect(QRectF(gap/2.0, -w/2, w/2 - gap/2.0, w))
        elif class_name == 'heavyTank':
            from PyQt6.QtCore import QRectF
            painter.translate(center, center)
            painter.rotate(45)
            w = size * 0.6
            gap = 1.5
            part = (w - gap*2) / 3.0
            painter.drawRect(QRectF(-w/2, -w/2, part, w))
            painter.drawRect(QRectF(-w/2 + part + gap, -w/2, part, w))
            painter.drawRect(QRectF(-w/2 + 2*part + 2*gap, -w/2, part, w))
            
        painter.end()
        return pixmap

    def get_moe_icon(self, moe: int, size=24) -> QPixmap:
        if moe == 0:
            return QPixmap()
            
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        from PyQt6.QtGui import QLinearGradient
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0.0, QColor("#30363d"))
        gradient.setColorAt(0.3, QColor("#8b949e"))
        gradient.setColorAt(0.5, QColor("#ffffff"))
        gradient.setColorAt(0.7, QColor("#8b949e"))
        gradient.setColorAt(1.0, QColor("#30363d"))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        
        center = size / 2.0
        from PyQt6.QtCore import QRectF
        painter.translate(center, center)
        painter.shear(-0.35, 0)
        
        w = size * 0.55
        h = size * 0.65
        gap = 2
        part = (w - gap*2) / 3.0
        
        if moe == 1:
            painter.drawRect(QRectF(-part/2, -h/2, part, h))
        elif moe == 2:
            total_w = part * 2 + gap
            painter.drawRect(QRectF(-total_w/2, -h/2, part, h))
            painter.drawRect(QRectF(-total_w/2 + part + gap, -h/2, part, h))
        elif moe >= 3:
            painter.drawRect(QRectF(-w/2, -h/2, part, h))
            painter.drawRect(QRectF(-w/2 + part + gap, -h/2, part, h))
            painter.drawRect(QRectF(-w/2 + 2*part + 2*gap, -h/2, part, h))
            
        painter.end()
        return pixmap
