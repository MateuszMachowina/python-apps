"""Local Instagram followers dashboard for several accounts on one computer.

Sessions are pasted manually for a single sync and are never stored. Account
profiles and their follower snapshots live separately in unfollowers_data/.
"""
import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

DATA_DIR = Path("unfollowers_data")
PROFILES_FILE = DATA_DIR / "profiles.json"
IG_APP_ID = "936619743392459"

BG, SURFACE, CARD = "#0a0a0a", "#161616", "#1e1e1e"
ACCENT, ACCENT2, TEXT, MUTED = "#c13584", "#833ab4", "#f0f0f0", "#888888"
GREEN, RED, GOLD = "#2ecc71", "#e74c3c", "#f5a623"


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def load_profiles() -> list[dict]:
    return load_json(PROFILES_FILE, [])


def profile_state_path(user_id: str) -> Path:
    return DATA_DIR / user_id / "current_state.json"


def load_state(user_id: str) -> dict:
    return load_json(profile_state_path(user_id), {
        "followers": [], "following": [], "updated_at": None,
        "new_followers": [], "unfollowers": [],
    })


def make_session(session_id: str):
    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.instagram.com",
        "Referer": "https://www.instagram.com/",
    })
    session.cookies.set("sessionid", session_id, domain=".instagram.com", path="/")
    return session


def api_headers():
    return {"Accept": "*/*", "X-IG-App-ID": IG_APP_ID, "X-Requested-With": "XMLHttpRequest"}


def get_users(session, user_id: str, action: str, status) -> set[str]:
    users, max_id = set(), None
    while True:
        status(f"Pobieranie: {action} ({len(users)} znalezionych) …")
        params = {"count": 100}
        if max_id:
            params["max_id"] = max_id
        response = session.get(
            f"https://www.instagram.com/api/v1/friendships/{user_id}/{action}/",
            params=params, headers=api_headers(), timeout=25,
        )
        if response.status_code == 429:
            raise RuntimeError("Instagram ograniczył liczbę zapytań (429). Spróbuj później.")
        if response.status_code != 200:
            raise RuntimeError(f"Instagram zwrócił {response.status_code}: {response.text[:160]}")
        data = response.json()
        users.update(user.get("username", "") for user in data.get("users", []) if user.get("username"))
        max_id = data.get("next_max_id")
        if not max_id:
            return users
        time.sleep(4)


def sync_profile(profile: dict, session_id: str, status) -> dict:
    try:
        import requests  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Brakuje requests. Uruchom: py -m pip install requests") from exc
    user_id = profile["user_id"]
    session = make_session(session_id)
    followers = get_users(session, user_id, "followers", status)
    following = get_users(session, user_id, "following", status)
    old = load_state(user_id)
    previous = set(old.get("followers", []))
    state = {
        "followers": sorted(followers, key=str.lower),
        "following": sorted(following, key=str.lower),
        "updated_at": now(),
        "new_followers": sorted(followers - previous, key=str.lower) if previous else [],
        "unfollowers": sorted(previous - followers, key=str.lower) if previous else [],
    }
    save_json(profile_state_path(user_id), state)
    return state


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Follow Tracker")
        self.geometry("1120x720")
        self.minsize(900, 580)
        self.configure(bg=BG)
        self.profiles = load_profiles()
        self.active_id = None
        self.search = tk.StringVar()
        self._build()
        self.refresh_profiles()

    def _build(self):
        header = tk.Frame(self, bg=SURFACE, height=62)
        header.pack(fill="x"); header.pack_propagate(False)
        tk.Frame(header, bg=ACCENT, width=4).pack(side="left", fill="y")
        tk.Label(header, text="✦ Follow Tracker", bg=SURFACE, fg=TEXT, font=("Segoe UI", 20, "bold")).pack(side="left", padx=18)
        tk.Label(header, text="lokalne profile · sesje nie są zapisywane", bg=SURFACE, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")

        body = tk.PanedWindow(self, orient="horizontal", bg=BG, sashwidth=4)
        body.pack(fill="both", expand=True, padx=16, pady=16)
        left, right = tk.Frame(body, bg=SURFACE, width=290), tk.Frame(body, bg=BG)
        body.add(left, minsize=240); body.add(right, minsize=580)

        tk.Label(left, text="KONTA", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=14, pady=(14, 6))
        self.profile_list = tk.Listbox(left, bg=CARD, fg=TEXT, selectbackground=ACCENT, selectforeground="white",
                                       relief="flat", activestyle="none", font=("Segoe UI", 10), height=12)
        self.profile_list.pack(fill="both", expand=True, padx=10)
        self.profile_list.bind("<<ListboxSelect>>", lambda _event: self.select_profile())

        form = tk.Frame(left, bg=SURFACE)
        form.pack(fill="x", padx=10, pady=10)
        self.name_var, self.user_id_var = tk.StringVar(), tk.StringVar()
        for label, variable in (("Nazwa profilu", self.name_var), ("Instagram User ID", self.user_id_var)):
            tk.Label(form, text=label, bg=SURFACE, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            tk.Entry(form, textvariable=variable, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat", font=("Segoe UI", 10)).pack(fill="x", pady=(2, 8), ipady=5)
        buttons = tk.Frame(form, bg=SURFACE); buttons.pack(fill="x")
        tk.Button(buttons, text="Zapisz profil", command=self.save_profile, bg=ACCENT, fg="white", relief="flat").pack(side="left")
        tk.Button(buttons, text="Usuń z listy", command=self.remove_profile, bg=SURFACE, fg=MUTED, relief="flat").pack(side="right")

        top = tk.Frame(right, bg=BG); top.pack(fill="x")
        self.profile_title = tk.Label(top, text="Wybierz lub dodaj konto", bg=BG, fg=TEXT, font=("Segoe UI", 18, "bold"))
        self.profile_title.pack(side="left")
        tk.Button(top, text="Synchronizuj", command=self.ask_sync, bg=ACCENT, fg="white", relief="flat", font=("Segoe UI", 10, "bold"), padx=15, pady=7).pack(side="right")

        self.summary = tk.Frame(right, bg=BG); self.summary.pack(fill="x", pady=14)
        self.cards = []
        for caption, colour in (("Followers", TEXT), ("Following", TEXT), ("Nie odwzajemniają", GOLD), ("Odeszli ostatnio", RED)):
            card = tk.Frame(self.summary, bg=CARD, padx=14, pady=10); card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            value = tk.Label(card, text="—", bg=CARD, fg=colour, font=("Segoe UI", 20, "bold")); value.pack(anchor="w")
            tk.Label(card, text=caption, bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            self.cards.append(value)
        self.updated = tk.Label(right, text="Brak synchronizacji", bg=BG, fg=MUTED, font=("Segoe UI", 9)); self.updated.pack(anchor="w", pady=(0, 8))

        filter_bar = tk.Frame(right, bg=BG); filter_bar.pack(fill="x")
        tk.Label(filter_bar, text="Szukaj", bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="left")
        search = tk.Entry(filter_bar, textvariable=self.search, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat")
        search.pack(side="left", fill="x", expand=True, padx=(8, 0), ipady=4)
        self.search.trace_add("write", lambda *_: self.render_lists())

        self.tabs = ttk.Notebook(right); self.tabs.pack(fill="both", expand=True, pady=(8, 0))
        self.tables = {}
        for key, title in (("non_followers", "Nie odwzajemniają"), ("new_followers", "Nowi obserwujący"), ("unfollowers", "Przestali obserwować"), ("followers", "Wszyscy obserwujący")):
            frame = tk.Frame(self.tabs, bg=SURFACE)
            table = tk.Listbox(frame, bg=SURFACE, fg=TEXT, relief="flat", activestyle="none", font=("Segoe UI", 10))
            table.pack(fill="both", expand=True, padx=8, pady=8)
            self.tabs.add(frame, text=title); self.tables[key] = table

        self.status = tk.Label(self, text="Gotowe", bg=SURFACE, fg=MUTED, anchor="w", padx=16, pady=8, font=("Segoe UI", 9))
        self.status.pack(fill="x", side="bottom")

    def refresh_profiles(self):
        self.profile_list.delete(0, "end")
        for profile in self.profiles:
            self.profile_list.insert("end", f"{profile['name']}  ·  {profile['user_id']}")
        if self.active_id:
            for index, profile in enumerate(self.profiles):
                if profile["user_id"] == self.active_id:
                    self.profile_list.select_set(index); break
        self.refresh_dashboard()

    def active_profile(self):
        return next((p for p in self.profiles if p["user_id"] == self.active_id), None)

    def select_profile(self):
        selected = self.profile_list.curselection()
        if not selected: return
        profile = self.profiles[selected[0]]; self.active_id = profile["user_id"]
        self.name_var.set(profile["name"]); self.user_id_var.set(profile["user_id"])
        self.refresh_dashboard()

    def save_profile(self):
        name, user_id = self.name_var.get().strip(), self.user_id_var.get().strip()
        if not name or not user_id.isdigit():
            messagebox.showwarning("Brak danych", "Podaj nazwę profilu i numeryczny Instagram User ID."); return
        self.profiles = [p for p in self.profiles if p["user_id"] != user_id]
        self.profiles.append({"name": name, "user_id": user_id})
        self.profiles.sort(key=lambda p: p["name"].lower()); self.active_id = user_id
        save_json(PROFILES_FILE, self.profiles); self.refresh_profiles()

    def remove_profile(self):
        profile = self.active_profile()
        if not profile or not messagebox.askyesno("Usuń profil", f"Usunąć {profile['name']} z listy? Dane synchronizacji pozostaną lokalnie."): return
        self.profiles = [p for p in self.profiles if p["user_id"] != self.active_id]
        self.active_id = None; save_json(PROFILES_FILE, self.profiles); self.refresh_profiles()

    def refresh_dashboard(self):
        profile = self.active_profile()
        if not profile:
            self.profile_title.config(text="Wybierz lub dodaj konto"); self.updated.config(text="Brak synchronizacji")
            for card in self.cards: card.config(text="—")
            self.render_lists({}); return
        state = load_state(profile["user_id"]); followers, following = set(state["followers"]), set(state["following"])
        self.profile_title.config(text=profile["name"])
        self.updated.config(text=f"Ostatnia synchronizacja: {state['updated_at'] or 'jeszcze nie wykonano'}")
        for card, value in zip(self.cards, (len(followers), len(following), len(following - followers), len(state["unfollowers"]))): card.config(text=str(value))
        self.render_lists(state)

    def render_lists(self, state=None):
        if state is None:
            profile = self.active_profile(); state = load_state(profile["user_id"]) if profile else {}
        followers, following = set(state.get("followers", [])), set(state.get("following", []))
        data = {"non_followers": sorted(following - followers, key=str.lower), "new_followers": state.get("new_followers", []),
                "unfollowers": state.get("unfollowers", []), "followers": state.get("followers", [])}
        phrase = self.search.get().strip().lower()
        for key, table in self.tables.items():
            table.delete(0, "end")
            values = [item for item in data[key] if phrase in item.lower()]
            if values:
                for username in values: table.insert("end", "@" + username)
            else: table.insert("end", "Brak danych" if not phrase else "Brak wyników")

    def ask_sync(self):
        profile = self.active_profile()
        if not profile:
            messagebox.showwarning("Wybierz konto", "Najpierw dodaj albo wybierz profil."); return
        dialog = tk.Toplevel(self); dialog.title("Sesja Instagram"); dialog.configure(bg=SURFACE); dialog.resizable(False, False); dialog.transient(self); dialog.grab_set()
        tk.Label(dialog, text="Wklej własny sessionid", bg=SURFACE, fg=TEXT, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(dialog, text="Token jest używany tylko do tej synchronizacji i nie zostanie zapisany.", bg=SURFACE, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=20)
        value = tk.StringVar(); entry = tk.Entry(dialog, textvariable=value, show="•", width=54, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat")
        entry.pack(padx=20, pady=14, ipady=6); entry.focus_set()
        tk.Button(dialog, text="Synchronizuj", bg=ACCENT, fg="white", relief="flat", command=lambda: self.start_sync(dialog, value.get().strip())).pack(anchor="e", padx=20, pady=(0, 18))

    def start_sync(self, dialog, session_id):
        if not session_id:
            messagebox.showwarning("Brak sessionid", "Wklej sessionid.", parent=dialog); return
        dialog.destroy(); profile = self.active_profile(); self.status.config(text="Synchronizacja trwa …", fg=GOLD)
        def work():
            try:
                state = sync_profile(profile, session_id, lambda text: self.after(0, self.status.config, {"text": text, "fg": GOLD}))
                self.after(0, self.refresh_dashboard); self.after(0, self.status.config, {"text": "Synchronizacja zakończona", "fg": GREEN})
            except Exception as exc:
                self.after(0, self.status.config, {"text": f"Błąd: {exc}", "fg": RED})
        threading.Thread(target=work, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
