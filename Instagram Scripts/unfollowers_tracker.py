import os, json, time, tempfile, shutil
from pathlib import Path
from datetime import datetime

# ─── Twoje funkcje z poprzedniego skryptu ─────────────────────────────────────
def find_firefox_profile() -> Path | None:
    appdata = os.environ.get("APPDATA", "")
    root = Path(appdata) / "Mozilla" / "Firefox" / "Profiles"
    if not root.exists(): return None
    for p in root.iterdir():
        if p.is_dir() and ("default-release" in p.name or "default" in p.name): return p
    dirs = [p for p in root.iterdir() if p.is_dir()]
    return dirs[0] if dirs else None

def extract_instagram_cookies(profile_dir: Path) -> dict:
    db = profile_dir / "cookies.sqlite"
    if not db.exists(): return {}
    tmp = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(db, tmp)
    for ext in ["-wal", "-shm"]:
        src = db.with_name(db.name + ext)
        if src.exists(): shutil.copy2(src, tmp.with_name(tmp.name + ext))
    try:
        import sqlite3 as _sq
        conn = _sq.connect(tmp)
        rows = conn.cursor().execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        ).fetchall()
        conn.close()
        return {n: v for n, v in rows}
    finally:
        tmp.unlink(missing_ok=True)
        for ext in ["-wal", "-shm"]: tmp.with_name(tmp.name + ext).unlink(missing_ok=True)

def _make_session(cookies: dict):
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Accept-Language": "en-US,en;q=0.5",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
    })
    for n, v in cookies.items(): s.cookies.set(n, v, domain=".instagram.com", path="/")
    if "csrftoken" in cookies: s.headers["X-CSRFToken"] = cookies["csrftoken"]
    return s

def _ah() -> dict:
    return {"Accept": "*/*", "X-IG-App-ID": "936619743392459", "X-Requested-With": "XMLHttpRequest"}

# ─── Nowa logika: Pobieranie i porównywanie ───────────────────────────────────

STATE_FILE = Path("followers_state.json")

def get_users(sess, user_id: str, action: str) -> set:
    """
    Pobiera listę followersów lub followingów.
    action: 'followers' lub 'following'
    """
    users = set()
    max_id = ""
    print(f"[*] Pobieranie listy {action}...")
    
    while True:
        url = f"https://www.instagram.com/api/v1/friendships/{user_id}/{action}/?count=100"
        if max_id:
            url += f"&max_id={max_id}"
            
        r = sess.get(url, timeout=20, headers=_ah())
        
        if r.status_code == 429:
            print("[!] Błąd 429: Rate Limit! Instagram zablokował zapytania. Zwiększ opóźnienie.")
            break
        if r.status_code != 200:
            print(f"[!] Błąd {r.status_code}: {r.text[:100]}")
            break
            
        data = r.json()
        for user in data.get('users', []):
            users.add(user['username'])
            
        max_id = data.get('next_max_id')
        if not max_id:
            break
            
        # UWAGA: Ten sleep to Twoja tarcza obronna przed banem. Nie schodź poniżej 3-5 sekund.
        print(f"  ↳ Pobrano {len(users)} osób, czekam 4 sekundy przed kolejną stroną...")
        time.sleep(4)
        
    return users

def main():
    profile = find_firefox_profile()
    if not profile:
        print("[!] Nie znaleziono profilu Firefox.")
        return
        
    cookies = extract_instagram_cookies(profile)
    user_id = cookies.get("ds_user_id")
    
    if not user_id:
        print("[!] Nie znaleziono aktywnej sesji (ds_user_id). Zaloguj się w Firefox.")
        return
        
    sess = _make_session(cookies)
    state_file = Path(f"followers_state_{user_id}.json")
    report_file = Path(f"raport_{user_id}.txt")
    
    # 1. Pobieranie aktualnych list (to info nadal wypisujemy w konsoli, żebyś wiedział, że coś się dzieje)
    current_followers = get_users(sess, user_id, "followers")
    current_following = get_users(sess, user_id, "following")
    
    if not current_followers:
        print("[!] Nie udało się pobrać followersów. Przerwano.")
        return

    # Wczytanie poprzedniego stanu (jeśli istnieje)
    past_followers = set()
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            past_followers = set(json.load(f))

    # =========================================================
    # BUDOWANIE RAPORTU (DO PLIKU TXT)
    # =========================================================
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raport_lines = []
    
    raport_lines.append("="*50)
    raport_lines.append(f" RAPORT SYNCHRONIZACJI INSTAGRAM | Data: {now}")
    raport_lines.append("="*50)

    # 2. Zmiany od ostatniego uruchomienia
    if past_followers:
        unfollowers = past_followers - current_followers
        new_followers = current_followers - past_followers
        
        # Kto uciekł?
        if unfollowers:
            raport_lines.append(f"\n[💔] COFNĘLI FOLLOW OD OSTATNIEGO RAZU ({len(unfollowers)}):")
            for uf in unfollowers:
                raport_lines.append(f"  - @{uf}")
        else:
            raport_lines.append("\n[✅] Nikt nie cofnął followa od ostatniej synchronizacji!")

        # Kto nowy przyszedł?
        if new_followers:
            raport_lines.append(f"\n[🎉] NOWI OBSERWUJĄCY ({len(new_followers)}):")
            for nf in new_followers:
                raport_lines.append(f"  - @{nf}")
    else:
        raport_lines.append("\n[ℹ] Brak poprzedniego stanu. Zapisano pierwszą bazę do porównań.")

    # 3. Kto nie oddaje followa (Non-followers)
    non_followers = current_following - current_followers
    raport_lines.append(f"\n[🔍] OSOBY, KTÓRE NIE ODDAJĄ CI FOLLOWA ({len(non_followers)}):")
    if non_followers:
        for nf in non_followers:
            raport_lines.append(f"  - @{nf}")
    else:
        raport_lines.append("  Wszyscy, których obserwujesz, obserwują też Ciebie. Wow!")

    raport_lines.append("\n" + "="*50)
    raport_lines.append(f"[ID Konta: {user_id}]")

    # =========================================================
    # ZAPIS DO PLIKÓW
    # =========================================================
    
    # Zapis stanu dla bazy (JSON)
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(list(current_followers), f, ensure_ascii=False)
        
    # Zapis pięknego raportu (TXT)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("\n".join(raport_lines))
        
    print(f"\n[✅] Gotowe! Otwórz plik: {report_file.name}, aby sprawdzić szczegóły.")

if __name__ == "__main__":
    main()