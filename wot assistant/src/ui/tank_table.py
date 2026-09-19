from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
import os
from .filters import FilterBar
from ..utils.wn8_calculator import calculate_tank_wn8
from ..utils.formatters import format_tier, format_type, format_nation, format_number
from .delegates import StarRatingDelegate, WN8BadgeDelegate, WinRateBarDelegate

class NumericSortItem(QTableWidgetItem):
    def __init__(self, val, display_str=None):
        super().__init__(display_str if display_str is not None else str(val))
        self.val = val

    def __lt__(self, other):
        if isinstance(other, NumericSortItem):
            return self.val < other.val
        return super().__lt__(other)

class TankTableView(QWidget):
    filters_changed = pyqtSignal()
    cell_data_changed = pyqtSignal(int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        self.filter_bar = FilterBar()
        self.filter_bar.filters_changed.connect(self.filters_changed.emit)
        layout.addWidget(self.filter_bar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(14)
        self.table.setHorizontalHeaderLabels([
            'ID', 'Fav', 'MoE', 'Nation', 'Type', 'Tier', 'Tank', 
            'Battles', 'Wins', 'WN8', 'Avg DMG', 'Avg Frags', 'Fun Rating', 'Comp Rating'
        ])
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setIconSize(QSize(100, 30))
        
        from PyQt6.QtWidgets import QAbstractItemView
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnHidden(0, True)
        self.table.verticalHeader().setVisible(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Fixed widths for icon/status columns
        self.table.setColumnWidth(1, 45)  # Fav
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 50)  # MoE
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 65)  # Nation
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 50)  # Type
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 50)  # Tier
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        
        self.table.setColumnWidth(12, 120) # Fun Rating
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(13, 120) # Comp Rating
        header.setSectionResizeMode(13, QHeaderView.ResizeMode.Fixed)
        
        self.table.setItemDelegateForColumn(8, WinRateBarDelegate(self.table))
        self.table.setItemDelegateForColumn(9, WN8BadgeDelegate(self.table))
        self.table.setItemDelegateForColumn(12, StarRatingDelegate(self.table))
        self.table.setItemDelegateForColumn(13, StarRatingDelegate(self.table))
        
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellClicked.connect(self._on_cell_clicked)
        
        layout.addWidget(self.table)
        
    def get_filter_bar(self) -> FilterBar:
        return self.filter_bar

    def load_data(self, rows: list, icon_cache, expected_values: dict):
        self.icon_cache = icon_cache
        self.table.setSortingEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        
        from ..utils.paths import get_resource_path
        assets_dir = get_resource_path(os.path.join('src', 'assets'))
        
        for row_data in rows:
            tank_id, name, tier, type_, nation, battles, wins, damage, frags, spotted, def_pts, fun_rating, comp_rating, image_url, is_favourite, moe = row_data
            
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)
            
            win_rate = (wins / battles * 100) if battles > 0 else 0
            avg_dmg = damage / battles if battles > 0 else 0
            avg_frags = frags / battles if battles > 0 else 0
            
            tank_wn8 = calculate_tank_wn8(tank_id, battles, wins, damage, frags, spotted, def_pts, expected_values)
            
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(tank_id)))
            
            fav_item = NumericSortItem(1 if is_favourite else 0, "")
            fav_item.setCheckState(Qt.CheckState.Checked if is_favourite else Qt.CheckState.Unchecked)
            fav_item.setFlags(fav_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_idx, 1, fav_item)
            
            moe_item = NumericSortItem(moe, "")
            moe_pix = icon_cache.get_moe_icon(moe)
            if not moe_pix.isNull():
                moe_item.setIcon(QIcon(moe_pix))
            moe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            moe_item.setFlags(moe_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_idx, 2, moe_item)
            
            nation_item = QTableWidgetItem()
            flag_path = os.path.join(assets_dir, 'nations', f'{nation}.png')
            
            nation_pix = None
            if os.path.exists(flag_path):
                nation_pix = QPixmap(flag_path)
                
            if nation_pix and not nation_pix.isNull():
                scaled_w = int(nation_pix.width() * 0.49)
                scaled_h = int(nation_pix.height() * 0.49)
                scaled_pix = nation_pix.scaled(scaled_w, scaled_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                nation_item.setIcon(QIcon(scaled_pix))
            else:
                nation_item.setText(format_nation(nation))
            self.table.setItem(row_idx, 3, nation_item)
            
            type_item = QTableWidgetItem()
            type_pix = icon_cache.get_class_icon(type_)
            if type_pix:
                type_item.setIcon(QIcon(type_pix))
            else:
                type_item.setText(format_type(type_))
            self.table.setItem(row_idx, 4, type_item)
            
            self.table.setItem(row_idx, 5, NumericSortItem(tier, format_tier(tier)))
            
            tank_item = QTableWidgetItem(name)
            pixmap = icon_cache.get_pixmap(tank_id, image_url)
            if pixmap:
                tank_item.setIcon(QIcon(pixmap))
            self.table.setItem(row_idx, 6, tank_item)
            
            self.table.setItem(row_idx, 7, NumericSortItem(battles, str(battles)))
            
            wr_item = NumericSortItem(win_rate, f"{win_rate:.2f}%")
            wr_item.setData(Qt.ItemDataRole.UserRole, float(win_rate))
            self.table.setItem(row_idx, 8, wr_item)
            
            wn8_item = NumericSortItem(tank_wn8, str(int(tank_wn8)))
            wn8_item.setData(Qt.ItemDataRole.EditRole, int(tank_wn8))
            self.table.setItem(row_idx, 9, wn8_item)
            
            self.table.setItem(row_idx, 10, NumericSortItem(avg_dmg, f"{avg_dmg:.0f}"))
            self.table.setItem(row_idx, 11, NumericSortItem(avg_frags, f"{avg_frags:.2f}"))
            
            fun_item = NumericSortItem(fun_rating, str(fun_rating))
            fun_item.setData(Qt.ItemDataRole.EditRole, fun_rating)
            self.table.setItem(row_idx, 12, fun_item)
            
            comp_item = NumericSortItem(comp_rating, str(comp_rating))
            comp_item.setData(Qt.ItemDataRole.EditRole, comp_rating)
            self.table.setItem(row_idx, 13, comp_item)
            
        self.table.blockSignals(False)
        self.table.setSortingEnabled(True)
        self.table.sortItems(7, Qt.SortOrder.DescendingOrder)

    def _on_cell_changed(self, row, col):
        tank_id_item = self.table.item(row, 0)
        if not tank_id_item:
            return
        tank_id = int(tank_id_item.text())
        
        if col == 1:
            is_fav = 1 if self.table.item(row, col).checkState() == Qt.CheckState.Checked else 0
            self.cell_data_changed.emit(tank_id, col, is_fav)
        elif col in (12, 13):
            val = int(self.table.item(row, col).data(Qt.ItemDataRole.EditRole))
            self.cell_data_changed.emit(tank_id, col, val)

    def _on_cell_clicked(self, row, col):
        pass
