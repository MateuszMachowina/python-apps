import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('API_KEY')
API_URL = 'https://api.worldoftanks.eu/wot'

TIER_MAP = {1:'I', 2:'II', 3:'III', 4:'IV', 5:'V', 6:'VI', 7:'VII', 8:'VIII', 9:'IX', 10:'X', 11:'XI'}
TIER_MAP_REVERSE = {v: k for k, v in TIER_MAP.items()}

TYPE_MAP = {'lightTank': 'Light Tank', 'mediumTank': 'Medium Tank', 'heavyTank': 'Heavy Tank', 'AT-SPG': 'Tank Destroyer', 'SPG': 'Artillery'}
TYPE_MAP_REVERSE = {v: k for k, v in TYPE_MAP.items()}

NATION_LIST = ['USA', 'USSR', 'UK', 'Germany', 'France', 'Japan', 'China', 'Poland', 'Sweden', 'Italy', 'Czech', 'Norway']

# WN8 color thresholds: (min_value, color_hex, label)
WN8_THRESHOLDS = [
    (2450, '#a855f7', 'Unicum'),
    (2000, '#3b82f6', 'Great'),
    (1600, '#22c55e', 'Good'),
    (1140, '#eab308', 'Average'),
    (650, '#f97316', 'Below Average'),
    (0, '#ef4444', 'Bad'),
]

def get_wn8_color(wn8_val: int) -> str:
    for threshold, color, _ in WN8_THRESHOLDS:
        if wn8_val >= threshold:
            return color
    return '#ef4444'

def get_wn8_label(wn8_val: int) -> str:
    for threshold, _, label in WN8_THRESHOLDS:
        if wn8_val >= threshold:
            return label
    return 'Bad'
