from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QComboBox
from PyQt6.QtCore import pyqtSignal
from ..config import NATION_LIST
from .widgets import CheckableComboBox, SearchBar

class FilterBar(QFrame):
    filters_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('filterBar')
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.search_bar = SearchBar()
        layout.addWidget(self.search_bar)
        
        def add_filter(text, widget):
            lbl = QLabel(text)
            lbl.setObjectName('filterLabel')
            layout.addWidget(lbl)
            layout.addWidget(widget)
            
        self.combo_tiers = CheckableComboBox()
        self.combo_tiers.addItems(['All Tiers', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI'])
        add_filter('Tiers:', self.combo_tiers)
        
        self.combo_types = CheckableComboBox()
        self.combo_types.addItems(['All Types', 'Light Tank', 'Medium Tank', 'Heavy Tank', 'Tank Destroyer', 'Artillery'])
        add_filter('Types:', self.combo_types)
        
        self.combo_nations = CheckableComboBox()
        self.combo_nations.addItems(['All Nations'] + NATION_LIST)
        add_filter('Nations:', self.combo_nations)
        
        self.combo_fav = QComboBox()
        self.combo_fav.addItems(['All', 'Favorites Only'])
        add_filter('Favorites:', self.combo_fav)
        
        self.combo_battles = QComboBox()
        self.combo_battles.addItems(['All battles', 'Min. 20 battles', 'Min. 50 battles'])
        add_filter('Battles:', self.combo_battles)
        
        self.combo_new = QComboBox()
        self.combo_new.addItems(['All', 'New Only'])
        add_filter('Added:', self.combo_new)
        
        # Connect signals
        self.search_bar.textChanged.connect(self.filters_changed.emit)
        self.combo_fav.currentIndexChanged.connect(self.filters_changed.emit)
        self.combo_battles.currentIndexChanged.connect(self.filters_changed.emit)
        self.combo_new.currentIndexChanged.connect(self.filters_changed.emit)
        
        try:
            self.combo_tiers.model().dataChanged.connect(self.filters_changed.emit)
            self.combo_types.model().dataChanged.connect(self.filters_changed.emit)
            self.combo_nations.model().dataChanged.connect(self.filters_changed.emit)
        except AttributeError:
            pass
        
    def get_filters(self) -> dict:
        fav_text = self.combo_fav.currentText()
        bat_text = self.combo_battles.currentText()
        
        min_battles = 0
        if bat_text == 'Min. 20 battles':
            min_battles = 20
        elif bat_text == 'Min. 50 battles':
            min_battles = 50
            
        def get_checked(combo):
            if hasattr(combo, 'get_checked_items'):
                return combo.get_checked_items()
            return []
            
        return {
            'search': self.search_bar.text(),
            'tiers': get_checked(self.combo_tiers),
            'types': get_checked(self.combo_types),
            'nations': get_checked(self.combo_nations),
            'fav_only': fav_text == 'Favorites Only',
            'new_only': self.combo_new.currentText() == 'New Only',
            'min_battles': min_battles
        }
