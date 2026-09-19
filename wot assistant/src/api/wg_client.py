import requests
from PyQt6.QtCore import QThread, pyqtSignal
from ..config import API_KEY, API_URL

class SyncWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, account_id, nickname, api_key, api_url, db_manager):
        super().__init__()
        self.account_id = account_id
        self.nickname = nickname
        self.api_key = api_key
        self.api_url = api_url
        self.db = db_manager

    def run(self):
        try:
            self.progress.emit('Fetching statistics...')
            info_res = requests.get(f"{self.api_url}/account/info/", params={"application_id": self.api_key, "account_id": self.account_id, "fields": "statistics.all"}).json()
            
            self.progress.emit('Fetching WTR...')
            wtr_res = requests.get(f"{self.api_url}/account/wtr/", params={"application_id": self.api_key, "account_id": self.account_id}).json()
            
            self.progress.emit('Fetching tanks...')
            tanks_res = requests.get(f"{self.api_url}/tanks/stats/", params={"application_id": self.api_key, "account_id": self.account_id}).json()
            
            tanks = tanks_res.get("data", {}).get(str(self.account_id), [])
            info_data = info_res.get("data", {}).get(str(self.account_id), {}).get("statistics", {}).get("all", {})
            
            tank_ids_to_check = [t["tank_id"] for t in tanks if 'tank_id' in t]
            if info_data.get("max_damage_tank_id"): tank_ids_to_check.append(info_data["max_damage_tank_id"])
            if info_data.get("max_frags_tank_id"): tank_ids_to_check.append(info_data["max_frags_tank_id"])

            missing = self.db.get_missing_tank_ids(tank_ids_to_check)
            if missing:
                self.progress.emit('Fetching missing tank data...')
                for i in range(0, len(missing), 100):
                    chunk = ",".join(map(str, missing[i:i+100]))
                    details = requests.get(f"{self.api_url}/encyclopedia/vehicles/", params={
                        "application_id": self.api_key, "tank_id": chunk, "fields": "name,tier,type,nation,images"
                    }).json()
                    if details.get("data"): 
                        self.db.insert_tanks_dict(details["data"])

            self.db.upsert_player_tanks(self.account_id, tanks)
            
            self.progress.emit('Fetching MoE (achievements)...')
            ach_res = requests.get(f"{self.api_url}/tanks/achievements/", params={"application_id": self.api_key, "account_id": self.account_id}).json()
            ach_data = ach_res.get("data", {}).get(str(self.account_id), [])
            moe_dict = {}
            for item in ach_data:
                tank_id = item.get("tank_id")
                moe = item.get("achievements", {}).get("marksOnGun")
                if tank_id and moe is not None:
                    moe_dict[tank_id] = moe
                    
            if moe_dict:
                self.db.upsert_moe_from_api(self.account_id, moe_dict)
                
            player_tanks_from_db = self.db.get_all_player_tanks(self.account_id)
            
            wtr_data = wtr_res.get("data", {}).get(str(self.account_id), {})
            wtr = wtr_data.get("rating", 0) if wtr_data else 0

            result_dict = {
                'account_id': self.account_id,
                'nickname': self.nickname,
                'info_data': info_data,
                'wtr': wtr,
                'tanks': tanks,
                'player_tanks_from_db': player_tanks_from_db
            }
            self.finished.emit(result_dict)

        except Exception as e:
            self.error.emit(str(e))

class WGApiClient:
    def __init__(self, db_manager):
        self.db = db_manager

    def search_player(self, nick: str) -> SyncWorker:
        search_res = requests.get(f"{API_URL}/account/list/", params={"application_id": API_KEY, "search": nick}).json()
        if not search_res.get("data"): 
            raise ValueError("Nie znaleziono gracza.")
            
        acc_id = search_res["data"][0]["account_id"]
        fetched_nick = search_res["data"][0]["nickname"]
        self.db.upsert_player(acc_id, fetched_nick)
        
        return SyncWorker(acc_id, fetched_nick, API_KEY, API_URL, self.db)
