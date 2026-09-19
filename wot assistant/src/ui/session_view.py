from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea
from ..styles import Theme

class SessionView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel('Session Tracking')
        font = title.font()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)
        
        self.summary_frame = QFrame()
        self.summary_frame.setObjectName('sessionCard')
        self.summary_layout = QVBoxLayout(self.summary_frame)
        self.summary_label = QLabel('No session data')
        self.summary_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_frame)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.history_container = QWidget()
        self.history_layout = QVBoxLayout(self.history_container)
        self.history_layout.addStretch()
        scroll.setWidget(self.history_container)
        
        layout.addWidget(scroll)
        
    def update_session(self, current_stats: dict, snapshots: list):
        # Clear history layout (except stretch)
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not snapshots:
            self.summary_label.setText('No previous session data.')
            return
            
        last_snap = snapshots[0]
        # (id, account_id, timestamp, total_battles, total_wins, total_wn8, tanks_data_json)
        last_battles = last_snap[3]
        last_wins = last_snap[4]
        last_wn8 = last_snap[5]
        
        curr_battles = current_stats.get('battles', 0)
        curr_wins = current_stats.get('wins', 0)
        curr_wn8 = current_stats.get('wn8', 0)
        
        d_battles = curr_battles - last_battles
        
        if last_battles > 0:
            last_wr = (last_wins / last_battles) * 100
        else:
            last_wr = 0
            
        if curr_battles > 0:
            curr_wr = (curr_wins / curr_battles) * 100
        else:
            curr_wr = 0
            
        d_wr = curr_wr - last_wr
        d_wn8 = curr_wn8 - last_wn8
        
        summary_text = (
            f"Battles: {d_battles:+d} | "
            f"Win Rate: {d_wr:+.2f}% | "
            f"WN8: {d_wn8:+d}"
        )
        self.summary_label.setText(summary_text)
        
        if d_wn8 > 0:
            self.summary_label.setObjectName('deltaPositive')
            self.summary_label.setStyleSheet(f"color: {Theme.SUCCESS}")
        elif d_wn8 < 0:
            self.summary_label.setObjectName('deltaNegative')
            self.summary_label.setStyleSheet(f"color: {Theme.DANGER}")
        else:
            self.summary_label.setObjectName('')
            self.summary_label.setStyleSheet("")
            
        # Display history
        for snap in snapshots[:20]:
            card = QFrame()
            card.setObjectName('sessionCard')
            card_lay = QVBoxLayout(card)
            
            ts = snap[2]
            b = snap[3]
            w = snap[4]
            wn = snap[5]
            wr = (w / b * 100) if b > 0 else 0
            
            lbl = QLabel(f"Date: {ts} | Battles: {b} | WN8: {wn} | WR: {wr:.2f}%")
            card_lay.addWidget(lbl)
            self.history_layout.insertWidget(self.history_layout.count() - 1, card)
            
    def clear(self):
        self.summary_label.setText('No session data')
        self.summary_label.setStyleSheet("")
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
