from dataclasses import dataclass

@dataclass
class PlayerInfo:
    account_id: int
    nickname: str

@dataclass
class TankInfo:
    tank_id: int
    name: str
    tier: int
    type: str
    nation: str
    image_url: str

@dataclass
class PlayerTankStats:
    account_id: int
    tank_id: int
    battles: int
    wins: int
    damage: int
    frags: int
    spotted: int
    def_pts: int
    fun_rating: int
    comp_rating: int
    is_favourite: bool
    moe: int

@dataclass
class SessionSnapshot:
    id: int
    account_id: int
    timestamp: str
    total_battles: int
    total_wins: int
    total_wn8: int
    tanks_data_json: str
