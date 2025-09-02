import pandas as pd
import os

# Pełna ścieżka do Excela
excel_path = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\players_table.xlsx"

# Wczytaj arkusze
players_df = pd.read_excel(excel_path, sheet_name="players")
clubs_df = pd.read_excel(excel_path, sheet_name="clubs")
nations_df = pd.read_excel(excel_path, sheet_name="nations")

# Pełne ścieżki do folderów z obrazkami
players_folder = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\players"
clubs_folder = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\clubs"
nations_folder = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\nations"

# Zestawy nazw plików (bez rozszerzenia)
players_imgs = {int(f.split(".")[0]) for f in os.listdir(players_folder) if f.endswith(".png")}
clubs_imgs = {int(f.split(".")[0]) for f in os.listdir(clubs_folder) if f.endswith(".png")}
nations_imgs = {int(f.split(".")[0]) for f in os.listdir(nations_folder) if f.endswith(".png")}

# Brakujące pliki
missing_players = sorted(list(set(players_df["player_id"]) - players_imgs))
missing_clubs = sorted(list(set(clubs_df["club_id"]) - clubs_imgs))
missing_nations = sorted(list(set(nations_df["nation_id"]) - nations_imgs))

# Stwórz raport
max_len = max(len(missing_players), len(missing_clubs), len(missing_nations))
report_df = pd.DataFrame({
    "Missing Players": missing_players + [""]*(max_len - len(missing_players)),
    "Missing Clubs": missing_clubs + [""]*(max_len - len(missing_clubs)),
    "Missing Nations": missing_nations + [""]*(max_len - len(missing_nations))
})

# Zapisz raport do Excela
report_df.to_excel(r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\missing_images.xlsx", index=False)

print("Raport zapisany do missing_images.xlsx ✔️")
