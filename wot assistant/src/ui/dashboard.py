from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout
from ..styles import Theme
from .widgets import StatCard

class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        
        # Title row
        title_layout = QHBoxLayout()
        title_label = QLabel('Player Profile')
        font = title_label.font()
        font.setPointSize(16)
        font.setBold(True)
        title_label.setFont(font)
        
        self.nickname_label = QLabel('-')
        self.nickname_label.setStyleSheet(f"color: {Theme.ACCENT}; font-size: 16px; font-weight: bold;")
        
        title_layout.addWidget(title_label)
        title_layout.addWidget(self.nickname_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)
        
        # Stats grid
        grid = QGridLayout()
        grid.setSpacing(20)
        
        self.card_wtr = StatCard('WTR Rating')
        self.card_battles = StatCard('Battles')
        self.card_wn8 = StatCard('Global WN8')
        self.card_winrate = StatCard('Win Rate')
        self.card_max_dmg = StatCard('Max Damage')
        self.card_max_frags = StatCard('Max Frags')
        
        grid.addWidget(self.card_wtr, 0, 0)
        grid.addWidget(self.card_battles, 0, 1)
        grid.addWidget(self.card_wn8, 0, 2)
        grid.addWidget(self.card_winrate, 1, 0)
        grid.addWidget(self.card_max_dmg, 1, 1)
        grid.addWidget(self.card_max_frags, 1, 2)
        
        layout.addLayout(grid)
        layout.addStretch()
        
    def update_stats(self, data: dict):
        self.nickname_label.setText(data.get('nickname', '-'))
        
        wtr = data.get('wtr', 0)
        battles = data.get('battles', 0)
        wn8 = data.get('wn8', 0)
        win_rate = data.get('win_rate', 0.0)
        
        self.card_wtr.set_value(str(wtr))
        self.card_battles.set_value(str(battles))
        
        wn8_color = Theme.get_wn8_color(wn8)
        self.card_wn8.set_value(str(wn8), wn8_color)
        
        self.card_winrate.set_value(f"{win_rate:.2f}%")
        
        max_damage = data.get('max_damage', 0)
        max_dmg_tank = data.get('max_damage_tank', '-')
        self.card_max_dmg.set_value(str(max_damage))
        self.card_max_dmg.set_subtext(max_dmg_tank)
        
        max_frags = data.get('max_frags', 0)
        max_frags_tank = data.get('max_frags_tank', '-')
        self.card_max_frags.set_value(str(max_frags))
        self.card_max_frags.set_subtext(max_frags_tank)
        
    def clear(self):
        self.nickname_label.setText('-')
        self.card_wtr.set_value('-')
        self.card_battles.set_value('-')
        self.card_wn8.set_value('-')
        self.card_winrate.set_value('-')
        self.card_max_dmg.set_value('-')
        self.card_max_dmg.set_subtext('')
        self.card_max_frags.set_value('-')
        self.card_max_frags.set_subtext('')
