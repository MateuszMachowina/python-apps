from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QComboBox, QStackedWidget, QMessageBox,
    QStyledItemDelegate
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QRect, QObject
from PyQt6.QtGui import QColor, QIcon
import json

from ..database.manager import DatabaseManager
from ..api.wg_client import WGApiClient
from ..api.wn8_provider import WN8Provider
from ..utils.icon_cache import IconCache
from ..utils.wn8_calculator import calculate_global_wn8
from ..config import TIER_MAP_REVERSE, TYPE_MAP_REVERSE, NATION_LIST

from .sidebar import Sidebar
from .dashboard import DashboardView
from .tank_table import TankTableView
from .session_view import SessionView
from .settings_view import SettingsView

class DeleteDelegate(QStyledItemDelegate):
    delete_requested = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hovered_row = -1
        self.hover_x = False
        
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        rect = option.rect
        delete_rect = QRect(rect.right() - 25, rect.top(), 25, rect.height())
        
        painter.save()
        if self.hovered_row == index.row() and self.hover_x:
            painter.setPen(QColor('#f85149'))
        else:
            painter.setPen(QColor('#8b949e'))
            
        font = painter.font()
        font.setPixelSize(14)
        painter.setFont(font)
        painter.drawText(delete_rect, Qt.AlignmentFlag.AlignCenter, "✕")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseMove:
            self.hovered_row = index.row()
            rect = option.rect
            delete_rect = QRect(rect.right() - 25, rect.top(), 25, rect.height())
            self.hover_x = delete_rect.contains(event.pos())
            if hasattr(option, 'widget') and option.widget:
                option.widget.viewport().update()
                
        elif event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            rect = option.rect
            delete_rect = QRect(rect.right() - 25, rect.top(), 25, rect.height())
            if delete_rect.contains(event.pos()):
                nickname = index.data(Qt.ItemDataRole.DisplayRole)
                self.delete_requested.emit(nickname)
                return True
                
        return super().editorEvent(event, model, option, index)

class ComboViewEventFilter(QObject):
    def __init__(self, combo, delegate):
        super().__init__(combo)
        self.combo = combo
        self.delegate = delegate
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            view = self.combo.view()
            pos = event.pos()
            index = view.indexAt(pos)
            if index.isValid():
                rect = view.visualRect(index)
                delete_rect = QRect(rect.right() - 25, rect.top(), 25, rect.height())
                if delete_rect.contains(pos):
                    nickname = index.data(Qt.ItemDataRole.DisplayRole)
                    # Close popup manually since we're intercepting the click
                    self.combo.hidePopup()
                    self.delegate.delete_requested.emit(nickname)
                    return True
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('WoT Stats Assistant')
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(1400, 800)
        
        self.db = DatabaseManager()
        self.api_client = WGApiClient(self.db)
        self.wn8_provider = WN8Provider()
        self.icon_cache = IconCache()
        
        self.expected_values = self.wn8_provider.get_expected_values()
        self.current_account_id = None
        self.sync_worker = None
        
        self._build_ui()
        self._connect_signals()
        self.load_local_data()

    def load_local_data(self):
        player = self.db.get_last_player()
        if not player or not player[0]:
            return
            
        self.current_account_id, nickname, wtr, max_dmg, max_dmg_tank_id, max_frags, max_frags_tank_id = player
        self.nick_input.setCurrentText(nickname)
        self.status_label.setText(f'Logged in: {nickname} (local data)')
        
        latest_snap = self.db.get_latest_snapshot(self.current_account_id)
        if latest_snap:
            total_battles = latest_snap['total_battles']
            total_wins = latest_snap['total_wins']
            total_wn8 = latest_snap['total_wn8']
            win_rate = (total_wins / total_battles * 100) if total_battles > 0 else 0
            
            max_dmg_tank = '-'
            max_frags_tank = '-'
            
            try:
                cursor = self.db.conn.cursor()
                if max_dmg_tank_id:
                    cursor.execute('SELECT name FROM Tanks_Dict WHERE tank_id = ?', (max_dmg_tank_id,))
                    row = cursor.fetchone()
                    if row: max_dmg_tank = row[0]
                if max_frags_tank_id:
                    cursor.execute('SELECT name FROM Tanks_Dict WHERE tank_id = ?', (max_frags_tank_id,))
                    row = cursor.fetchone()
                    if row: max_frags_tank = row[0]
            except Exception as e:
                print(e)
                
            stats = {
                'nickname': nickname,
                'wtr': wtr,
                'battles': total_battles,
                'wn8': total_wn8,
                'win_rate': win_rate,
                'max_damage': max_dmg,
                'max_damage_tank': max_dmg_tank,
                'max_frags': max_frags,
                'max_frags_tank': max_frags_tank
            }
            self.dashboard_view.update_stats(stats)
            
            snapshots = self.db.get_session_snapshots(self.current_account_id)
            current_stats = {'battles': total_battles, 'wins': total_wins, 'wn8': total_wn8}
            self.session_view.update_session(current_stats, snapshots)
            
        self.load_table_data()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Top Bar
        self.top_bar = QFrame()
        self.top_bar.setObjectName('topBar')
        top_layout = QHBoxLayout(self.top_bar)
        
        self.nick_input = QComboBox()
        self.nick_input.setEditable(True)
        self.nick_input.setObjectName('nickInput')
        
        self.delete_delegate = DeleteDelegate(self.nick_input)
        self.nick_input.view().setItemDelegate(self.delete_delegate)
        self.nick_input.view().setMouseTracking(True)
        self.delete_delegate.delete_requested.connect(self.delete_player)
        
        self.combo_filter = ComboViewEventFilter(self.nick_input, self.delete_delegate)
        self.nick_input.view().viewport().installEventFilter(self.combo_filter)
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT nickname FROM Players ORDER BY nickname')
            for row in cursor.fetchall():
                self.nick_input.addItem(row[0])
        except Exception:
            pass
            
        self.nick_input.setCurrentText('koks516')
        top_layout.addWidget(self.nick_input)
        
        self.sync_btn = QPushButton('Sync')
        self.sync_btn.setObjectName('syncBtn')
        top_layout.addWidget(self.sync_btn)
        
        self.status_label = QLabel('Status: Ready')
        self.status_label.setObjectName('statusLabel')
        top_layout.addWidget(self.status_label)
        top_layout.addStretch()
        
        right_layout.addWidget(self.top_bar)
        
        # Pages container
        self.stacked_widget = QStackedWidget()
        
        self.dashboard_view = DashboardView()
        self.tank_table_view = TankTableView()
        self.session_view = SessionView()
        self.settings_view = SettingsView()
        
        self.stacked_widget.addWidget(self.dashboard_view)
        self.stacked_widget.addWidget(self.tank_table_view)
        self.stacked_widget.addWidget(self.session_view)
        self.stacked_widget.addWidget(self.settings_view)
        
        right_layout.addWidget(self.stacked_widget)
        main_layout.addLayout(right_layout)

    def _connect_signals(self):
        self.sidebar.page_changed.connect(self._switch_page)
        self.sync_btn.clicked.connect(self.sync_player)
        self.nick_input.lineEdit().returnPressed.connect(self.sync_player)
        
        self.tank_table_view.filters_changed.connect(self.load_table_data)
        self.tank_table_view.cell_data_changed.connect(self.on_cell_data_changed)

    def _switch_page(self, page_name: str):
        pages = {
            'dashboard': 0,
            'tanks': 1,
            'session': 2,
            'settings': 3
        }
        if page_name in pages:
            self.stacked_widget.setCurrentIndex(pages[page_name])

    def delete_player(self, nickname: str):
        reply = QMessageBox.question(self, 'Delete Player', f"Are you sure you want to delete '{nickname}' from the database?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_player_by_nickname(nickname)
            # Remove from combobox
            idx = self.nick_input.findText(nickname)
            if idx >= 0:
                self.nick_input.removeItem(idx)
            if self.nick_input.currentText() == nickname:
                self.nick_input.setCurrentText("")
                self.dashboard_view.clear()
                self.session_view.clear()
                self.tank_table_view.load_data([], self.icon_cache, self.expected_values)
                self.current_account_id = None

    def sync_player(self):
        nick = self.nick_input.currentText().strip()
        if not nick:
            return
            
        self.sync_btn.setEnabled(False)
        self.status_label.setText('Status: Synchronizing...')
        
        try:
            self.sync_worker = self.api_client.search_player(nick)
            self.sync_worker.progress.connect(self.status_label.setText)
            self.sync_worker.error.connect(self._on_sync_error)
            self.sync_worker.finished.connect(self.on_sync_finished)
            self.sync_worker.start()
        except Exception as e:
            self._on_sync_error(str(e))

    def _on_sync_error(self, err_msg: str):
        self.status_label.setText(f'Error: {err_msg}')
        self.sync_btn.setEnabled(True)

    def on_sync_finished(self, result: dict):
        self.sync_btn.setEnabled(True)
        self.current_account_id = result.get('account_id')
        nickname = result.get('nickname', 'Unknown')
        wtr = result.get('wtr', 0)
        
        if not self.current_account_id:
            return
            
        self.status_label.setText(f'Logged in: {nickname}')
        
        if self.nick_input.findText(nickname) == -1:
            self.nick_input.addItem(nickname)
        
        info_data = result.get('info_data', {})
        tanks_api_data = result.get('tanks', [])
        
        # Calculate stats from info_data
        total_battles = info_data.get('battles', 0)
        total_wins = info_data.get('wins', 0)
        
        global_wn8 = calculate_global_wn8(info_data, tanks_api_data, self.expected_values)
        win_rate = (total_wins / total_battles * 100) if total_battles > 0 else 0
        
        max_dmg = info_data.get('max_damage', 0)
        max_dmg_tank_id = info_data.get('max_damage_tank_id', 0)
        max_dmg_tank = '-'
        
        max_frags = info_data.get('max_frags', 0)
        max_frags_tank_id = info_data.get('max_frags_tank_id', 0)
        max_frags_tank = '-'
        
        try:
            cursor = self.db.conn.cursor()
            if max_dmg_tank_id:
                cursor.execute('SELECT name FROM Tanks_Dict WHERE tank_id = ?', (max_dmg_tank_id,))
                md_row = cursor.fetchone()
                if md_row:
                    max_dmg_tank = md_row[0]
                    
            if max_frags_tank_id:
                cursor.execute('SELECT name FROM Tanks_Dict WHERE tank_id = ?', (max_frags_tank_id,))
                mf_row = cursor.fetchone()
                if mf_row:
                    max_frags_tank = mf_row[0]
        except Exception as e:
            print(f"Error fetching max stats: {e}")
            
        self.db.upsert_player(self.current_account_id, nickname, wtr, max_dmg, max_dmg_tank_id, max_frags, max_frags_tank_id)
        
        stats = {
            'nickname': nickname,
            'wtr': wtr,
            'battles': total_battles,
            'wn8': int(global_wn8),
            'win_rate': win_rate,
            'max_damage': max_dmg,
            'max_damage_tank': max_dmg_tank,
            'max_frags': max_frags,
            'max_frags_tank': max_frags_tank
        }
        
        self.dashboard_view.update_stats(stats)
        
        # Save snapshot
        snapshot_data = json.dumps([{'tank_id': t.get('tank_id', 0), 'battles': t.get('all', {}).get('battles', 0)} for t in tanks_api_data])
        self.db.save_session_snapshot(self.current_account_id, total_battles, total_wins, int(global_wn8), snapshot_data)
        
        self.load_table_data()
        
        snapshots = self.db.get_session_snapshots(self.current_account_id)
        current_stats = {'battles': total_battles, 'wins': total_wins, 'wn8': int(global_wn8)}
        self.session_view.update_session(current_stats, snapshots)

    def load_table_data(self):
        if not self.current_account_id:
            return
            
        filters = self.tank_table_view.get_filter_bar().get_filters()
        
        query = '''
            SELECT p.tank_id, d.name, d.tier, d.type, d.nation,
                   p.battles, p.wins, p.damage, p.frags, p.spotted, p.def_pts,
                   p.fun_rating, p.comp_rating, d.image_url, p.is_favourite, p.moe
            FROM Player_Tanks p
            JOIN Tanks_Dict d ON p.tank_id = d.tank_id
            WHERE p.account_id = ?
        '''
        params = [self.current_account_id]
        
        search = filters.get('search', '')
        if search:
            query += " AND d.name LIKE ?"
            params.append(f"%{search}%")
            
        if filters.get('fav_only'):
            query += " AND p.is_favourite = 1"
            
        if filters.get('new_only'):
            snapshots = self.db.get_session_snapshots(self.current_account_id, limit=2)
            new_ids = []
            if snapshots and len(snapshots) >= 2:
                latest = json.loads(snapshots[0][6])
                prev = json.loads(snapshots[1][6])
                latest_ids = {t['tank_id'] for t in latest}
                prev_ids = {t['tank_id'] for t in prev}
                new_ids = list(latest_ids - prev_ids)
                
            if new_ids:
                query += f" AND p.tank_id IN ({','.join('?'*len(new_ids))})"
                params.extend(new_ids)
            else:
                query += " AND 0" # return nothing if no new tanks
            
        min_battles = filters.get('min_battles', 0)
        if min_battles > 0:
            query += " AND p.battles >= ?"
            params.append(min_battles)
            
        tiers = filters.get('tiers', [])
        if tiers and len(tiers) < 11:
            tier_ints = [TIER_MAP_REVERSE.get(t, 0) for t in tiers]
            query += " AND d.tier IN ({})".format(','.join('?' * len(tier_ints)))
            params.extend(tier_ints)
            
        types = filters.get('types', [])
        if types and len(types) < 5:
            type_strs = [TYPE_MAP_REVERSE.get(t, '') for t in types]
            query += " AND d.type IN ({})".format(','.join('?' * len(type_strs)))
            params.extend(type_strs)
            
        nations = filters.get('nations', [])
        if nations and len(nations) < len(NATION_LIST):
            nation_strs = [n.lower() for n in nations]
            query += " AND d.nation IN ({})".format(','.join('?' * len(nation_strs)))
            params.extend(nation_strs)
            
        cursor = self.db.conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        self.tank_table_view.load_data(rows, self.icon_cache, self.expected_values)

    def on_cell_data_changed(self, tank_id, col, value):
        if not self.current_account_id:
            return
            
        if col == 1:
            self.db.update_favourite(self.current_account_id, tank_id, value)
        elif col == 12:
            self.db.update_rating(self.current_account_id, tank_id, 'fun', value)
        elif col == 13:
            self.db.update_rating(self.current_account_id, tank_id, 'comp', value)
