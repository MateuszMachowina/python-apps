def calculate_global_wn8(info_data: dict, player_tanks: list, expected_values: dict) -> int:
    if not expected_values or not player_tanks: return 0

    exp_dmg = exp_spot = exp_frag = exp_def = exp_win = 0.0
    act_dmg = act_spot = act_frag = act_def = act_win = 0.0

    for tank in player_tanks:
        tid = tank.get('tank_id')
        stats = tank.get('all', {})
        battles = stats.get('battles', 0)
        
        if tid in expected_values and battles > 0:
            exp = expected_values[tid]
            exp_dmg += exp['expDamage'] * battles
            exp_spot += exp['expSpot'] * battles
            exp_frag += exp['expFrag'] * battles
            exp_def += exp['expDef'] * battles
            exp_win += (exp['expWinRate'] / 100.0) * battles
            
            act_dmg += stats.get('damage_dealt', 0)
            act_spot += stats.get('spotted', 0)
            act_frag += stats.get('frags', 0)
            act_def += stats.get('dropped_capture_points', 0)
            act_win += stats.get('wins', 0)

    if exp_dmg == 0: return 0

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

def calculate_tank_wn8(tank_id: int, battles: int, wins: int, damage: int, frags: int, spotted: int, def_pts: int, expected_values: dict) -> int:
    if tank_id not in expected_values or battles <= 0: return 0
    
    exp = expected_values[tank_id]
    eDmg = exp['expDamage'] * battles
    eSpot = exp['expSpot'] * battles
    eFrag = exp['expFrag'] * battles
    eDef = exp['expDef'] * battles
    eWin = (exp['expWinRate'] / 100.0) * battles
    
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
