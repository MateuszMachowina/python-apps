import os

class Theme:
    # Color Palette
    BG_PRIMARY = '#0d1117'
    BG_SECONDARY = '#161b22'
    BG_TERTIARY = '#1c2333'
    BG_SIDEBAR = '#0d1117'
    BORDER = '#30363d'
    BORDER_LIGHT = '#3d444d'
    TEXT_PRIMARY = '#e6edf3'
    TEXT_SECONDARY = '#8b949e'
    TEXT_MUTED = '#656d76'
    ACCENT = '#7c3aed'
    ACCENT_HOVER = '#8b5cf6'
    ACCENT_GLOW = 'rgba(124, 58, 237, 0.3)'
    SUCCESS = '#3fb950'
    WARNING = '#d29922'
    DANGER = '#f85149'
    STAR_ACTIVE = '#fbbf24'
    STAR_INACTIVE = '#3d444d'
    ROW_ALT = '#111820'
    ROW_HOVER = '#1a2233'
    SCROLLBAR_BG = '#0d1117'
    SCROLLBAR_HANDLE = '#30363d'
    SCROLLBAR_HOVER = '#484f58'

    # Typography
    FONT_FAMILY = 'Segoe UI'
    FONT_MONO = 'Consolas'
    FONT_SIZE_SM = 11
    FONT_SIZE_BASE = 13
    FONT_SIZE_LG = 15
    FONT_SIZE_XL = 18
    FONT_SIZE_2XL = 24
    FONT_SIZE_3XL = 32

    # Spacing
    RADIUS_SM = 6
    RADIUS_MD = 10
    RADIUS_LG = 14
    PADDING_SM = 8
    PADDING_MD = 14
    PADDING_LG = 20

    @staticmethod
    def load_stylesheet() -> str:
        """Reads dark_theme.qss from the bundled resources."""
        from ..utils.paths import get_resource_path
        qss_path = get_resource_path(os.path.join('src', 'styles', 'dark_theme.qss'))
        try:
            with open(qss_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def get_wn8_color(wn8: int) -> str:
        """Returns hex color based on WN8 thresholds."""
        if wn8 >= 2450:
            return '#a855f7' # Unicum
        elif wn8 >= 2000:
            return '#3b82f6' # Great
        elif wn8 >= 1600:
            return '#22c55e' # Good
        elif wn8 >= 1140:
            return '#eab308' # Average
        elif wn8 >= 650:
            return '#f97316' # Below Average
        else:
            return '#ef4444' # Bad

    @staticmethod
    def get_wn8_label(wn8: int) -> str:
        """Returns label string based on WN8 thresholds."""
        if wn8 >= 2450:
            return 'Unicum'
        elif wn8 >= 2000:
            return 'Great'
        elif wn8 >= 1600:
            return 'Good'
        elif wn8 >= 1140:
            return 'Average'
        elif wn8 >= 650:
            return 'Below Average'
        else:
            return 'Bad'
