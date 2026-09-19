import sqlite3
import os
from ..utils.paths import get_project_root

class DatabaseManager:
    def __init__(self, db_name=None):
        if db_name is None:
            db_name = os.path.join(get_project_root(), 'wot_stats.db')
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Players (
                account_id INTEGER PRIMARY KEY, 
                nickname TEXT UNIQUE,
                wtr INTEGER DEFAULT 0,
                max_damage INTEGER DEFAULT 0,
                max_damage_tank_id INTEGER DEFAULT 0,
                max_frags INTEGER DEFAULT 0,
                max_frags_tank_id INTEGER DEFAULT 0
            )
        ''')
        
        for col in ["wtr", "max_damage", "max_damage_tank_id", "max_frags", "max_frags_tank_id"]:
            try:
                cursor.execute(f"ALTER TABLE Players ADD COLUMN {col} INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
                
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
                
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                account_id INTEGER, 
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP, 
                total_battles INTEGER, 
                total_wins INTEGER, 
                total_wn8 INTEGER, 
                tanks_data_json TEXT
            )
        ''')
        self.conn.commit()

    def upsert_player(self, account_id, nickname, wtr=0, max_damage=0, max_damage_tank_id=0, max_frags=0, max_frags_tank_id=0):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO Players (account_id, nickname, wtr, max_damage, max_damage_tank_id, max_frags, max_frags_tank_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?) 
            ON CONFLICT(account_id) DO UPDATE SET 
                nickname=excluded.nickname,
                wtr=excluded.wtr,
                max_damage=excluded.max_damage,
                max_damage_tank_id=excluded.max_damage_tank_id,
                max_frags=excluded.max_frags,
                max_frags_tank_id=excluded.max_frags_tank_id
        ''', (account_id, nickname, wtr, max_damage, max_damage_tank_id, max_frags, max_frags_tank_id))
        self.conn.commit()
        
    def get_last_player(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT p.account_id, p.nickname, p.wtr, p.max_damage, p.max_damage_tank_id, p.max_frags, p.max_frags_tank_id
            FROM Players p
            LEFT JOIN Sessions s ON p.account_id = s.account_id
            ORDER BY s.timestamp DESC LIMIT 1
        ''')
        return cursor.fetchone()

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

    def upsert_moe_from_api(self, account_id, moe_dict):
        cursor = self.conn.cursor()
        records = [
            (moe, account_id, tank_id)
            for tank_id, moe in moe_dict.items()
        ]
        # Only updates existing records
        cursor.executemany('''
            UPDATE Player_Tanks 
            SET moe = ?
            WHERE account_id = ? AND tank_id = ?
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

    def save_session_snapshot(self, account_id, total_battles, total_wins, total_wn8, tanks_data_json):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO Sessions (account_id, total_battles, total_wins, total_wn8, tanks_data_json)
            VALUES (?, ?, ?, ?, ?)
        ''', (account_id, total_battles, total_wins, total_wn8, tanks_data_json))
        self.conn.commit()

    def get_session_snapshots(self, account_id, limit=20) -> list:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, account_id, timestamp, total_battles, total_wins, total_wn8, tanks_data_json
            FROM Sessions
            WHERE account_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (account_id, limit))
        return cursor.fetchall()

    def get_latest_snapshot(self, account_id) -> dict or None:
        snapshots = self.get_session_snapshots(account_id, limit=1)
        if snapshots:
            row = snapshots[0]
            return {
                'id': row[0],
                'account_id': row[1],
                'timestamp': row[2],
                'total_battles': row[3],
                'total_wins': row[4],
                'total_wn8': row[5],
                'tanks_data_json': row[6]
            }
        return None

    def get_all_player_tanks(self, account_id) -> list[tuple]:
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT tank_id, battles, wins, damage, frags, spotted, def_pts, fun_rating, comp_rating, is_favourite, moe
            FROM Player_Tanks
            WHERE account_id = ?
        ''', (account_id,))
        return cursor.fetchall()

    def delete_player_by_nickname(self, nickname: str):
        cursor = self.conn.cursor()
        # Find account_id first
        cursor.execute('SELECT account_id FROM Players WHERE nickname = ?', (nickname,))
        row = cursor.fetchone()
        if row:
            account_id = row[0]
            cursor.execute('DELETE FROM Players WHERE account_id = ?', (account_id,))
            cursor.execute('DELETE FROM Player_Tanks WHERE account_id = ?', (account_id,))
            cursor.execute('DELETE FROM Sessions WHERE account_id = ?', (account_id,))
            self.conn.commit()
