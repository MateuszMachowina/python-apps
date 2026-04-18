import sys
import os
import sqlite3
import requests
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QTableWidget, QTableWidgetItem, QComboBox, 
                             QStyledItemDelegate, QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QEvent, QSize
from PyQt6.QtGui import QColor, QPainter, QPixmap, QIcon, QStandardItemModel, QStandardItem, QKeySequence

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_URL = "https://api.worldoftanks.eu/wot"

class DatabaseManager:
    def __init__(self, db_name="wot_stats.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS Players (account_id INTEGER PRIMARY KEY, nickname TEXT UNIQUE)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Tanks_Dict (
                tank_id INTEGER PRIMARY KEY, name TEXT, tier INTEGER, type TEXT, nation TEXT, image_url TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Player_Tanks (
                account_id INTEGER, tank_id INTEGER, battles INTEGER, wins INTEGER, 
                damage INTEGER DEFAULT 0, frags INTEGER DEFAULT 0, spotted INTEGER DEFAULT 0, def_pts INTEGER DEFAULT 0,
                fun_rating INTEGER DEFAULT 0, comp_rating INTEGER DEFAULT 0, 
                is_favourite INTEGER DEFAULT 0, moe INTEGER DEFAULT 0,
                PRIMARY KEY (account_id, tank_id)
            )
        ''')
        
        for col in ["is_favourite", "moe", "damage", "frags", "spotted", "def_pts"]:
            try:
                cursor.execute(f"ALTER TABLE Player_Tanks ADD COLUMN {col} INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass 
                
        self.conn.commit()

    def upsert_player(self, account_id, nickname):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO Players (account_id, nickname) VALUES (?, ?) 
            ON CONFLICT(account_id) DO UPDATE SET nickname=excluded.nickname
        ''', (account_id, nickname))
        self.conn.commit()

    def insert_tanks_dict(self, tanks_data):
        cursor = self.conn.cursor()
        records = [
            (tid, data.get('name'), data.get('tier'), data.get('type'), data.get('nation'), data.get('images', {}).get('contour_icon', ''))
            for tid, data in tanks_data.items() if data is not None
        ]
        cursor.executemany('INSERT OR IGNORE INTO Tanks_Dict VALUES (?, ?, ?, ?, ?, ?)', records)
        self.conn.commit()

    def upsert_player_tanks(self, account_id, tanks_list):
        cursor = self.conn.cursor()
        records = [
            (
                account_id, tank['tank_id'], 
                tank.get('all', {}).get('battles', 0), 
                tank.get('all', {}).get('wins', 0),
                tank.get('all', {}).get('damage_dealt', 0),
                tank.get('all', {}).get('frags', 0),
                tank.get('all', {}).get('spotted', 0),
                tank.get('all', {}).get('dropped_capture_points', 0)
            )
            for tank in tanks_list if 'tank_id' in tank
        ]
        cursor.executemany('''
            INSERT INTO Player_Tanks (account_id, tank_id, battles, wins, damage, frags, spotted, def_pts) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, tank_id) DO UPDATE SET 
                battles=excluded.battles, wins=excluded.wins, 
                damage=excluded.damage, frags=excluded.frags, 
                spotted=excluded.spotted, def_pts=excluded.def_pts
        ''', records)
        self.conn.commit()

    def get_missing_tank_ids(self, tank_ids):
        if not tank_ids:
            return []
        cursor = self.conn.cursor()
        placeholders = ','.join('?' for _ in tank_ids)
        cursor.execute(f'SELECT tank_id FROM Tanks_Dict WHERE tank_id IN ({placeholders})', tank_ids)
        existing = {row[0] for row in cursor.fetchall()}
        return [tid for tid in tank_ids if tid not in existing]

    def get_tank_info(self, tank_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT name, image_url FROM Tanks_Dict WHERE tank_id = ?', (tank_id,))
        return cursor.fetchone()

    def update_rating(self, account_id, tank_id, category, rating):
        col = "fun_rating" if category == "fun" else "comp_rating"
        self.conn.cursor().execute(f"UPDATE Player_Tanks SET {col} = ? WHERE account_id = ? AND tank_id = ?", (rating, account_id, tank_id))
        self.conn.commit()

    def update_favourite(self, account_id, tank_id, is_fav):
        self.conn.cursor().execute("UPDATE Player_Tanks SET is_favourite = ? WHERE account_id = ? AND tank_id = ?", (1 if is_fav else 0, account_id, tank_id))
        self.conn.commit()

    def update_moe(self, account_id, tank_id, moe):
        self.conn.cursor().execute("UPDATE Player_Tanks SET moe = ? WHERE account_id = ? AND tank_id = ?", (moe, account_id, tank_id))
        self.conn.commit()

class StarRatingDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        rating = index.data(Qt.ItemDataRole.EditRole)
        rating = rating if isinstance(rating, int) else 0
        
        painter.save()
        font = painter.font()
        font.setPointSize(16)
        painter.setFont(font)
        
        x_start = option.rect.x() + (option.rect.width() - 100) // 2 
        y = option.rect.y() + (option.rect.height() + font.pointSize()) // 2 - 4
        
        for i in range(5):
            painter.setPen(QColor(255, 200, 0) if i < rating else QColor(180, 180, 180))
            painter.drawText(x_start + i * 20, y, "★")
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            x_start = option.rect.x() + (option.rect.width() - 100) // 2
            clicked = int((event.position().x() - x_start) // 20) + 1
            model.setData(index, max(0, min(5, clicked)), Qt.ItemDataRole.EditRole)
            return True
        return False

class NumericSortItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            val1 = self.data(Qt.ItemDataRole.UserRole)
            if val1 is None: val1 = self.data(Qt.ItemDataRole.EditRole)
            
            val2 = other.data(Qt.ItemDataRole.UserRole)
            if val2 is None: val2 = other.data(Qt.ItemDataRole.EditRole)
            
            return float(val1) < float(val2)
        except (ValueError, TypeError):
            return super().__lt__(other)

class CheckableComboBox(QComboBox):
    def __init__(self):
        super().__init__()
        self.setModel(QStandardItemModel(self))
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setStyleSheet("border: none; background: transparent;")
        self.model().dataChanged.connect(self.update_text)
        self.view().viewport().installEventFilter(self)

    def eventFilter(self, widget, event):
        if widget == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.position().toPoint())
            item = self.model().itemFromIndex(index)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
            return True
        return super().eventFilter(widget, event)

    def update_text(self):
        checked = self.get_checked_items()
        self.setEditText("Wszystko" if len(checked) == self.model().rowCount() else (", ".join(checked) if checked else "Nic"))

    def addItems(self, texts):
        for text in texts:
            item = QStandardItem(text)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setData(Qt.CheckState.Checked if "Wszystkie" in text else Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
            self.model().appendRow(item)
        self.update_text()

    def get_checked_items(self):
        return [self.model().item(i).text() for i in range(self.model().rowCount()) if self.model().item(i).checkState() == Qt.CheckState.Checked]

class WoTStatsApp(QMainWindow):
    TIER_MAP = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII', 9:'IX', 10:'X', 11:'XI'}
    TYPE_MAP = {"lightTank": "Light Tank", "mediumTank": "Medium Tank", "heavyTank": "Heavy Tank", "AT-SPG": "Tank Destroyer", "SPG": "Artillery"}

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_account_id = None
        self.expected_vals = {}
        self.cache_dir = "icons_cache"
        if not os.path.exists(self.cache_dir): 
            os.makedirs(self.cache_dir)
        self.initUI()

    def format_tier(self, tier):
        return self.TIER_MAP.get(tier, str(tier))

    def format_type(self, t):
        return self.TYPE_MAP.get(t, str(t).capitalize())

    def format_nation(self, n):
        if not n: return "Unknown"
        return n.upper() if n.lower() in ["usa", "ussr", "uk"] else n.capitalize()

    def get_wn8_color(self, wn8_val):
        if wn8_val >= 2450: return "#8b29e6"
        elif wn8_val >= 2000: return "#00a9ff"
        elif wn8_val >= 1600: return "#4a8520"
        elif wn8_val >= 1140: return "#d7b600"
        elif wn8_val >= 650: return "#ff8500"
        else: return "#cd3333"

    def initUI(self):
        self.setWindowTitle("WoT Stats Assistant")
        self.resize(1350, 750)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Top connection layout
        login_layout = QHBoxLayout()
        self.nick_input = QLineEdit()
        self.nick_input.setPlaceholderText("Wpisz nick gracza...")
        self.login_btn = QPushButton("Synchronizuj")
        self.login_btn.setDefault(True)
        self.login_btn.clicked.connect(self.sync_player)
        self.login_btn.setShortcut(QKeySequence("Return"))
        self.status_label = QLabel("Status: Gotowy")
        
        login_layout.addWidget(QLabel("Nick:"))
        login_layout.addWidget(self.nick_input)
        login_layout.addWidget(self.login_btn)
        login_layout.addWidget(self.status_label)
        
        # Player Stats Card
        self.stats_group = QGroupBox("Wizytówka gracza")
        self.stats_layout = QHBoxLayout(self.stats_group)
        
        self.lbl_wtr = QLabel("<b>WTR:</b> -")
        self.lbl_wn8 = QLabel("<b>WN8:</b> -")
        self.lbl_battles = QLabel("<b>Bitwy:</b> -")
        self.lbl_winrate = QLabel("<b>Zwycięstwa:</b> -")
        
        self.lbl_max_dmg_icon = QLabel()
        self.lbl_max_dmg_text = QLabel("<b>Max DMG:</b> -")
        
        self.lbl_max_frags_icon = QLabel()
        self.lbl_max_frags_text = QLabel("<b>Max Frags:</b> -")
        
        self.stats_layout.addWidget(self.lbl_wtr)
        self.stats_layout.addWidget(self.lbl_wn8)
        self.stats_layout.addWidget(self.lbl_battles)
        self.stats_layout.addWidget(self.lbl_winrate)
        self.stats_layout.addStretch()
        self.stats_layout.addWidget(self.lbl_max_dmg_icon)
        self.stats_layout.addWidget(self.lbl_max_dmg_text)
        self.stats_layout.addSpacing(20)
        self.stats_layout.addWidget(self.lbl_max_frags_icon)
        self.stats_layout.addWidget(self.lbl_max_frags_text)

        # Filters
        filter_layout = QHBoxLayout()
        self.tier_filter = CheckableComboBox()
        self.tier_filter.addItems(["Wszystkie Tiery"] + [self.format_tier(i) for i in range(1, 12)])
        
        self.type_filter = CheckableComboBox()
        self.type_filter.addItems(["Wszystkie Typy", "Light Tank", "Medium Tank", "Heavy Tank", "Tank Destroyer", "Artillery"])
        
        self.nation_filter = CheckableComboBox()
        self.nation_filter.addItems(["Wszystkie Nacje", "USA", "USSR", "UK", "Germany", "France", "Japan", "China", "Poland", "Sweden", "Italy"])
        
        self.fav_filter = QComboBox()
        self.fav_filter.addItems(["Wszystkie", "Tylko Ulubione"])

        self.battles_filter = QComboBox()
        self.battles_filter.addItems(["Wszystkie bitwy", "Min. 20 bitew", "Min. 50 bitew"])
        self.battles_filter.currentIndexChanged.connect(self.load_table_data)

        for f in [self.tier_filter, self.type_filter, self.nation_filter]: 
            f.model().dataChanged.connect(self.load_table_data)
        self.fav_filter.currentIndexChanged.connect(self.load_table_data)

        filter_layout.addWidget(QLabel("Tiery:"))
        filter_layout.addWidget(self.tier_filter)
        filter_layout.addWidget(QLabel("Typy:"))
        filter_layout.addWidget(self.type_filter)
        filter_layout.addWidget(QLabel("Nacje:"))
        filter_layout.addWidget(self.nation_filter)
        filter_layout.addWidget(QLabel("Ulubione:"))
        filter_layout.addWidget(self.fav_filter)
        filter_layout.addWidget(QLabel("Bitwy:"))
        filter_layout.addWidget(self.battles_filter)
        filter_layout.addStretch()

        # Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(15) 
        self.table.setHorizontalHeaderLabels(["ID", "Fav.", "MoE", "Ikona", "Czołg", "Tier", "Typ", "Nacja", "Bitwy", "Zwycięstwa", "WN8", "Śr. DMG", "Śr. Fragi", "Dobra zabawa", "Konkurencyjność"])
        self.table.hideColumn(0)
        self.table.setIconSize(QSize(100, 30))
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) 
        
        for col, width in [(1, 45), (2, 60), (13, 140), (14, 140)]:
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(col, width)

        self.star_delegate = StarRatingDelegate(self.table)
        self.table.setItemDelegateForColumn(13, self.star_delegate)
        self.table.setItemDelegateForColumn(14, self.star_delegate)

        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.cellClicked.connect(self.on_cell_clicked)
        self.table.cellDoubleClicked.connect(self.on_cell_clicked)
        self.table.setSortingEnabled(True)

        main_layout.addLayout(login_layout)
        main_layout.addWidget(self.stats_group)
        main_layout.addLayout(filter_layout)
        main_layout.addWidget(self.table)
        self.nick_input.setFocus()

    def sync_player(self, *args):
        nick = self.nick_input.text().strip()
        if not nick: return
        
        self.status_label.setText("Szukanie...")
        QApplication.processEvents()
        
        search_res = requests.get(f"{API_URL}/account/list/", params={"application_id": API_KEY, "search": nick}).json()
        if not search_res.get("data"): 
            self.status_label.setText("Nie znaleziono gracza.")
            return
            
        acc_id = search_res["data"][0]["account_id"]
        self.current_account_id = acc_id
        self.db.upsert_player(acc_id, search_res["data"][0]["nickname"])

        self.expected_vals = self.get_wn8_expected()

        # Pobieranie ogólnych info konta i czołgów
        info_res = requests.get(f"{API_URL}/account/info/", params={"application_id": API_KEY, "account_id": acc_id, "fields": "statistics.all"}).json()
        wtr_res = requests.get(f"{API_URL}/account/wtr/", params={"application_id": API_KEY, "account_id": acc_id}).json()
        tanks_res = requests.get(f"{API_URL}/tanks/stats/", params={"application_id": API_KEY, "account_id": acc_id}).json()
        tanks = tanks_res.get("data", {}).get(str(acc_id), [])

        info_data = info_res.get("data", {}).get(str(acc_id), {}).get("statistics", {}).get("all", {})
        tank_ids_to_check = [t["tank_id"] for t in tanks if 'tank_id' in t]
        if info_data.get("max_damage_tank_id"): tank_ids_to_check.append(info_data["max_damage_tank_id"])
        if info_data.get("max_frags_tank_id"): tank_ids_to_check.append(info_data["max_frags_tank_id"])

        missing = self.db.get_missing_tank_ids(tank_ids_to_check)
        if missing:
            for i in range(0, len(missing), 100):
                chunk = ",".join(map(str, missing[i:i+100]))
                details = requests.get(f"{API_URL}/encyclopedia/vehicles/", params={
                    "application_id": API_KEY, "tank_id": chunk, "fields": "name,tier,type,nation,images"
                }).json()
                if details.get("data"): 
                    self.db.insert_tanks_dict(details["data"])

        self.db.upsert_player_tanks(acc_id, tanks)
        
        # Odrzucanie elementów z błędem w WTR
        wtr_data = wtr_res.get("data", {}).get(str(acc_id), {})
        wtr_val = wtr_data.get("rating", 0) if wtr_data else 0
        
        battles = info_data.get("battles", 0)
        wins = info_data.get("wins", 0)
        win_rate = (wins / battles * 100) if battles > 0 else 0

        # WN8 Globalne wyliczenie z zebranych czołgów
        wn8_val = self.calculate_wn8(info_data, tanks, self.expected_vals)
        wn8_color = self.get_wn8_color(wn8_val)
        
        self.lbl_wtr.setText(f"<b>WTR:</b> {wtr_val}")
        self.lbl_wn8.setText(f"<b>WN8:</b> <span style='color:{wn8_color}'>{wn8_val}</span>")
        self.lbl_battles.setText(f"<b>Bitwy:</b> {battles}")
        self.lbl_winrate.setText(f"<b>Zwycięstwa:</b> {win_rate:.2f}%")
        
        self.update_record_ui(self.lbl_max_dmg_icon, self.lbl_max_dmg_text, "Max DMG", info_data.get("max_damage", 0), info_data.get("max_damage_tank_id"))
        self.update_record_ui(self.lbl_max_frags_icon, self.lbl_max_frags_text, "Max Frags", info_data.get("max_frags", 0), info_data.get("max_frags_tank_id"))

        self.load_table_data()
        self.status_label.setText(f"Zalogowano: {search_res['data'][0]['nickname']}")

    def get_wn8_expected(self):
        try:
            res = requests.get("https://static.modxvm.com/wn8-data-exp/json/wn8exp.json", timeout=5).json()
            return {item["IDNum"]: item for item in res["data"]}
        except Exception as e:
            print(f"Błąd pobierania wartości oczekiwanych WN8: {e}")
            return {}

    def calculate_wn8(self, info_data, player_tanks, expected_values):
        if not expected_values or not player_tanks: return 0

        exp_dmg = exp_spot = exp_frag = exp_def = exp_win = 0.0

        for tank in player_tanks:
            tid = tank.get('tank_id')
            battles = tank.get('all', {}).get('battles', 0)
            
            if tid in expected_values and battles > 0:
                exp = expected_values[tid]
                exp_dmg += exp['expDamage'] * battles
                exp_spot += exp['expSpot'] * battles
                exp_frag += exp['expFrag'] * battles
                exp_def += exp['expDef'] * battles
                exp_win += (exp['expWinRate'] / 100.0) * battles

        if exp_dmg == 0: return 0

        act_dmg = info_data.get('damage_dealt', 0)
        act_spot = info_data.get('spotted', 0)
        act_frag = info_data.get('frags', 0)
        act_def = info_data.get('dropped_capture_points', 0)
        act_win = info_data.get('wins', 0)

        rDAMAGE = act_dmg / exp_dmg
        rSPOT   = act_spot / exp_spot if exp_spot > 0 else 0
        rFRAG   = act_frag / exp_frag if exp_frag > 0 else 0
        rDEF    = act_def / exp_def if exp_def > 0 else 0
        rWIN    = act_win / exp_win if exp_win > 0 else 0

        rWINc    = max(0, (rWIN    - 0.71) / (1 - 0.71))
        rDAMAGEc = max(0, (rDAMAGE - 0.22) / (1 - 0.22))
        rFRAGc   = max(0, min(rDAMAGEc + 0.2, (rFRAG   - 0.12) / (1 - 0.12)))
        rSPOTc   = max(0, min(rDAMAGEc + 0.1, (rSPOT   - 0.38) / (1 - 0.38)))
        rDEFc    = max(0, min(rDAMAGEc + 0.1, (rDEF    - 0.10) / (1 - 0.10)))

        wn8 = 980 * rDAMAGEc + 210 * rDAMAGEc * rFRAGc + 155 * rFRAGc * rSPOTc + 75 * rDEFc * rFRAGc + 145 * rWINc
        
        return int(round(wn8))

    def calculate_tank_wn8(self, tid, bat, wins, damage, frags, spotted, def_pts):
        if tid not in self.expected_vals or bat <= 0: return 0
        
        exp = self.expected_vals[tid]
        eDmg = exp['expDamage'] * bat
        eSpot = exp['expSpot'] * bat
        eFrag = exp['expFrag'] * bat
        eDef = exp['expDef'] * bat
        eWin = (exp['expWinRate'] / 100.0) * bat
        
        if eDmg == 0: return 0

        rDAMAGE = damage / eDmg
        rSPOT   = spotted / eSpot if eSpot > 0 else 0
        rFRAG   = frags / eFrag if eFrag > 0 else 0
        rDEF    = def_pts / eDef if eDef > 0 else 0
        rWIN    = wins / eWin if eWin > 0 else 0

        rWINc    = max(0, (rWIN    - 0.71) / (1 - 0.71))
        rDAMAGEc = max(0, (rDAMAGE - 0.22) / (1 - 0.22))
        rFRAGc   = max(0, min(rDAMAGEc + 0.2, (rFRAG   - 0.12) / (1 - 0.12)))
        rSPOTc   = max(0, min(rDAMAGEc + 0.1, (rSPOT   - 0.38) / (1 - 0.38)))
        rDEFc    = max(0, min(rDAMAGEc + 0.1, (rDEF    - 0.10) / (1 - 0.10)))

        wn8 = 980 * rDAMAGEc + 210 * rDAMAGEc * rFRAGc + 155 * rFRAGc * rSPOTc + 75 * rDEFc * rFRAGc + 145 * rWINc
        return int(round(wn8))

    def update_record_ui(self, icon_label, text_label, prefix, value, tank_id):
        if not tank_id:
            text_label.setText(f"<b>{prefix}:</b> {value}")
            icon_label.clear()
            return
            
        tank_info = self.db.get_tank_info(tank_id)
        if not tank_info:
            text_label.setText(f"<b>{prefix}:</b> {value} (Nieznany czołg)")
            icon_label.clear()
            return
            
        name, img_url = tank_info
        text_label.setText(f"<b>{prefix}:</b> {value} ({name})")
        
        path = os.path.join(self.cache_dir, f"{tank_id}.png")
        if not os.path.exists(path) and img_url:
            try:
                r = requests.get(img_url, timeout=3)
                with open(path, 'wb') as f:
                    f.write(r.content)
            except requests.RequestException:
                pass
                
        if os.path.exists(path):
            pixmap = QPixmap(path)
            icon_label.setPixmap(pixmap.scaledToHeight(25, Qt.TransformationMode.SmoothTransformation))
        else:
            icon_label.clear()

    def load_table_data(self):
        if not self.current_account_id: return
        
        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        fav_f = self.fav_filter.currentText()
        battles_f = self.battles_filter.currentText()
        t_f = self.tier_filter.get_checked_items()
        type_f = self.type_filter.get_checked_items()
        n_f = self.nation_filter.get_checked_items()

        
        t_map = {v: k for k, v in self.TIER_MAP.items()}
        ty_map = {v: k for k, v in self.TYPE_MAP.items()}

        query = """
            SELECT pt.tank_id, d.name, d.tier, d.type, d.nation, pt.battles, pt.wins, 
                   pt.damage, pt.frags, pt.spotted, pt.def_pts, 
                   pt.fun_rating, pt.comp_rating, d.image_url, pt.is_favourite, pt.moe 
            FROM Player_Tanks pt 
            JOIN Tanks_Dict d ON pt.tank_id = d.tank_id 
            WHERE pt.account_id = ?
        """
        params = [self.current_account_id]

        if "Wszystkie Tiery" not in t_f and t_f: 
            query += f" AND d.tier IN ({','.join('?'*len(t_f))})"
            params.extend([t_map.get(x) for x in t_f])
        if "Wszystkie Typy" not in type_f and type_f: 
            query += f" AND d.type IN ({','.join('?'*len(type_f))})"
            params.extend([ty_map.get(x) for x in type_f])
        if "Wszystkie Nacje" not in n_f and n_f: 
            query += f" AND d.nation IN ({','.join('?'*len(n_f))})"
            params.extend([x.lower() for x in n_f])
        if fav_f == "Tylko Ulubione": 
            query += " AND pt.is_favourite = 1"
        if battles_f == "Min. 50 bitew":
            query += " AND pt.battles >= 50"
        elif battles_f == "Min. 20 bitew":
            query += " AND pt.battles >= 20"

        cursor = self.db.conn.cursor()
        cursor.execute(query + " ORDER BY pt.battles DESC", params)
        
        for row_idx, row in enumerate(cursor.fetchall()):
            self.table.insertRow(row_idx)
            tid, name, tier, ty, nat, bat, wins, damage, frags, spotted, def_pts, fun, comp, img, fav, moe = row
            
            wr = (wins / bat * 100) if bat > 0 else 0
            avg_dmg = (damage / bat) if bat > 0 else 0
            avg_frags = (frags / bat) if bat > 0 else 0
            tank_wn8 = self.calculate_tank_wn8(tid, bat, wins, damage, frags, spotted, def_pts)

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(tid)))
            
            f_item = NumericSortItem()
            f_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            f_item.setCheckState(Qt.CheckState.Checked if fav else Qt.CheckState.Unchecked)
            f_item.setData(Qt.ItemDataRole.EditRole, 1 if fav else 0)
            f_item.setData(Qt.ItemDataRole.DisplayRole, "")
            self.table.setItem(row_idx, 1, f_item)

            moe_text = "★" * moe if moe > 0 else "-"
            moe_item = NumericSortItem(moe_text)
            moe_item.setData(Qt.ItemDataRole.UserRole, moe)
            moe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            moe_item.setFlags(moe_item.flags() & ~Qt.ItemFlag.ItemIsEditable) 
            self.table.setItem(row_idx, 2, moe_item)

            img_item = QTableWidgetItem()
            path = os.path.join(self.cache_dir, f"{tid}.png")
            if not os.path.exists(path) and img:
                try: 
                    r = requests.get(img, timeout=2)
                    with open(path, 'wb') as f: 
                        f.write(r.content)
                except requests.RequestException: 
                    pass
                    
            if os.path.exists(path): 
                img_item.setIcon(QIcon(QPixmap(path)))
            self.table.setItem(row_idx, 3, img_item)

            self.table.setItem(row_idx, 4, QTableWidgetItem(str(name)))
            
            t_item = NumericSortItem(self.format_tier(tier))
            t_item.setData(Qt.ItemDataRole.UserRole, tier)
            self.table.setItem(row_idx, 5, t_item)
            
            self.table.setItem(row_idx, 6, QTableWidgetItem(self.format_type(ty)))
            self.table.setItem(row_idx, 7, QTableWidgetItem(self.format_nation(nat)))
            
            b_item = NumericSortItem()
            b_item.setData(Qt.ItemDataRole.EditRole, bat)
            self.table.setItem(row_idx, 8, b_item)
            
            # 9: Win Rate (%)
            wr_item = NumericSortItem(f"{round(wr, 2)} %")
            wr_item.setData(Qt.ItemDataRole.UserRole, wr) 
            wr_item.setForeground(QColor(self.get_wn8_color(wr * 40))) 
            f = wr_item.font(); f.setBold(True); wr_item.setFont(f)
            self.table.setItem(row_idx, 9, wr_item)

            # 10: WN8 Czołgu
            t_wn8_item = NumericSortItem()
            t_wn8_item.setData(Qt.ItemDataRole.EditRole, tank_wn8)
            t_wn8_item.setForeground(QColor(self.get_wn8_color(tank_wn8)))
            f = t_wn8_item.font(); f.setBold(True); t_wn8_item.setFont(f)
            self.table.setItem(row_idx, 10, t_wn8_item)

            # 11: Średni DMG
            dmg_item = NumericSortItem()
            dmg_item.setData(Qt.ItemDataRole.EditRole, round(avg_dmg, 0))
            self.table.setItem(row_idx, 11, dmg_item)

            # 12: Średnie Fragi
            frag_item = NumericSortItem()
            frag_item.setData(Qt.ItemDataRole.EditRole, round(avg_frags, 2))
            self.table.setItem(row_idx, 12, frag_item)

            # 13, 14: Oceny użytkownika
            for col, val in [(13, fun), (14, comp)]:
                star_item = NumericSortItem()
                star_item.setData(Qt.ItemDataRole.EditRole, val)
                self.table.setItem(row_idx, col, star_item)

            # Wyłączenie edycji komórek z wyjątkiem checkboksa i ocen
            for c in range(3, 13):
                item = self.table.item(row_idx, c)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)

    def on_cell_clicked(self, row, col):
        if col == 2:
            item = self.table.item(row, col)
            tid = int(self.table.item(row, 0).text())
            
            try:
                current_moe = int(item.data(Qt.ItemDataRole.UserRole))
            except (ValueError, TypeError):
                current_moe = 0
                
            new_moe = (current_moe + 1) % 4
            
            self.table.blockSignals(True)
            item.setData(Qt.ItemDataRole.UserRole, new_moe)
            item.setData(Qt.ItemDataRole.DisplayRole, "★" * new_moe if new_moe > 0 else "-")
            self.table.blockSignals(False)
            
            self.db.update_moe(self.current_account_id, tid, new_moe)

    def on_cell_changed(self, row, col):
        if not self.current_account_id: return
        tid_item = self.table.item(row, 0)
        if not tid_item: return
        tid = int(tid_item.text())
        
        self.table.blockSignals(True)
        if col == 1:
            item = self.table.item(row, col)
            is_checked = item.checkState() == Qt.CheckState.Checked
            item.setData(Qt.ItemDataRole.EditRole, 1 if is_checked else 0)
            item.setData(Qt.ItemDataRole.DisplayRole, "")
            self.db.update_favourite(self.current_account_id, tid, is_checked)
        elif col in [13, 14]:
            val = self.table.item(row, col).data(Qt.ItemDataRole.EditRole)
            self.db.update_rating(self.current_account_id, tid, "fun" if col == 13 else "comp", val)
        self.table.blockSignals(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = WoTStatsApp()
    w.show()
    sys.exit(app.exec())
