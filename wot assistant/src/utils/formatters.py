from ..config import TIER_MAP, TYPE_MAP

def format_tier(tier: int) -> str:
    return TIER_MAP.get(tier, str(tier))

def format_type(t: str) -> str:
    return TYPE_MAP.get(t, str(t).capitalize())

def format_nation(n: str) -> str:
    if not n: return "Unknown"
    return n.upper() if n.lower() in ["usa", "ussr", "uk"] else n.capitalize()

def format_number(n: int) -> str:
    return f"{n:,}".replace(",", " ")
