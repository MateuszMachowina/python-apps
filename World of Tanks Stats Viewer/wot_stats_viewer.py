import requests
import os
from tabulate import tabulate
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env into the environment
# Hybrid API key approach: environment variable or prompt
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    print("⚠️  No API key found in environment.")
    print("🔑  You can get one here: https://developers.wargaming.net/")
    API_KEY = input("Please enter your WoT API key: ").strip()

API_URL = "https://api.worldoftanks.eu/wot"

def to_roman(n):
    roman_numerals = {
        1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
        6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'
    }
    return roman_numerals.get(n, str(n))

def mastery_to_string(value):
    return {
        0: "None",
        1: "3rd Class",
        2: "2nd Class",
        3: "1st Class",
        4: "Ace Tanker"
    }.get(value, "Unknown")

def get_player_id(username):
    url = f"{API_URL}/account/list/"
    params = {
        "application_id": API_KEY,
        "search": username
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and len(data["data"]) > 0:
        return data["data"][0]["account_id"]
    print("Player not found!")
    return None

def get_player_stats(player_id):
    url = f"{API_URL}/account/info/"
    params = {
        "application_id": API_KEY,
        "account_id": player_id,
        "fields": "statistics.all.wins,statistics.all.battles,global_rating"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and str(player_id) in data["data"]:
        return data["data"][str(player_id)]
    print("Error fetching player stats!")
    return None

def get_most_used_tanks(player_id):
    url = f"{API_URL}/account/tanks/"
    params = {
        "application_id": API_KEY,
        "account_id": player_id,
        "fields": "tank_id,statistics,mark_of_mastery"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and str(player_id) in data["data"]:
        return data["data"][str(player_id)]
    print("Error fetching tank data!")
    return None

def get_tank_stats(player_id, tank_id):
    url = f"{API_URL}/tanks/stats/"
    params = {
        "application_id": API_KEY,
        "account_id": player_id,
        "tank_id": tank_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and str(player_id) in data["data"]:
        return data["data"][str(player_id)][0]["all"]
    print(f"Error fetching stats for Tank ID: {tank_id}")
    return None

def get_tank_details(tank_id):
    url = f"{API_URL}/encyclopedia/vehicles/"
    params = {
        "application_id": API_KEY,
        "fields": "name,type,nation,tier",
        "tank_id": tank_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and str(tank_id) in data["data"]:
        return data["data"][str(tank_id)]
    print(f"Error fetching tank details for Tank ID: {tank_id}")
    return None

def get_max_frags(player_id, tank_id):
    # This function fetches max_frags
    url = f"{API_URL}/tanks/stats/"
    params = {
        "application_id": API_KEY,
        "account_id": player_id,
        "tank_id": tank_id,
        "fields": "max_frags"
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "data" in data and str(player_id) in data["data"]:
        return data["data"][str(player_id)][0].get("max_frags", 0)
    print(f"Error fetching max frags for Tank ID: {tank_id}")
    return 0

def format_type(tank_type):
    tank_type = tank_type.lower()
    if tank_type == "at-spg":
        return "Tank Destroyer"
    elif tank_type == "spg":
        return "Arty"
    if tank_type.endswith("tank"):
        return tank_type[:-4].capitalize() + " Tank"
    return tank_type.capitalize()

def format_nation(nation):
    return nation.upper() if nation.lower() in ["usa", "ussr", "uk"] else nation.capitalize()

def display_top_tanks(username, top_n=5):
    player_id = get_player_id(username)
    if player_id is None:
        return

    print(f"\nFetching stats for player: {username} (ID: {player_id}) ...\n")

    player_stats = get_player_stats(player_id)
    if player_stats is None:
        return

    wins = player_stats['statistics']['all'].get('wins', 0)
    battles = player_stats['statistics']['all'].get('battles', 0)
    win_rate = (wins / battles) * 100 if battles > 0 else 0
    global_rating = player_stats.get('global_rating', 'N/A')

    print(f"Username: {username}")
    print(f"Total Battles: {battles}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Global Rating: {global_rating}\n")

    # Ask user for tier filter
    tier_input = input("Enter tier(s) to filter (e.g. 8 or 6,7,8 or 'all'): ").strip()
    if tier_input.lower() != "all":
        try:
            selected_tiers = set(int(t.strip()) for t in tier_input.split(","))
        except ValueError:
            print("Invalid tier input. Showing all tiers.")
            selected_tiers = None
    else:
        selected_tiers = None

    tanks_data = get_most_used_tanks(player_id)
    if tanks_data is None:
        return

    sorted_tanks = sorted(tanks_data, key=lambda x: x['statistics']['battles'], reverse=True)

    table_headers = ["Tank ID", "Tank Name", "Type", "Nation", "Tier", "Battles", "Win Rate (%)", "Avg Damage", "Avg Frags", "Max Frags", "Mastery Badge"]
    table_data = []

    for tank in sorted_tanks:
        tank_id = tank['tank_id']
        tank_details = get_tank_details(tank_id)

        if not tank_details:
            continue

        tier = tank_details.get("tier")
        if selected_tiers and tier not in selected_tiers:
            continue

        tank_name = tank_details.get("name", "N/A")
        tank_type = format_type(tank_details.get("type", "N/A"))
        tank_nation = format_nation(tank_details.get("nation", "N/A"))
        tank_tier = to_roman(tier)

        battles = tank['statistics']['battles']
        wins_tank = tank['statistics']['wins']
        win_rate_tank = (wins_tank / battles) * 100 if battles > 0 else 0
        mastery_level = tank.get('mark_of_mastery', 0)
        mastery_str = mastery_to_string(mastery_level)

        tank_stats = get_tank_stats(player_id, tank_id)
        if tank_stats:
            damage_dealt = tank_stats.get("damage_dealt", 0)
            avg_damage = damage_dealt / battles if battles > 0 else 0
            frags = tank_stats.get("frags", 0)
            avg_frags = frags / battles if battles > 0 else 0
        else:
            avg_damage = 0
            avg_frags = 0

        max_frags = get_max_frags(player_id, tank_id)

        table_data.append([
            tank_id, tank_name, tank_type, tank_nation,
            tank_tier, battles, f"{win_rate_tank:.2f} %",
            f"{avg_damage:.0f}", f"{avg_frags:.2f}", max_frags, mastery_str
        ])

        if len(table_data) >= top_n:
            break

    if table_data:
        print(tabulate(table_data, headers=table_headers, tablefmt="pretty"))
    else:
        print("No tank data found to display.")


def print_title():
    print("=" * 50)
    print("        World of Tanks Player Stats Viewer        ")
    print("=" * 50)


def main():
    print_title()
    current_username = None  # Variable to keep track of the current player

    while True:
        if current_username is None:
            username = input("\nEnter the player's username: ")
            current_username = username
        else:
            username = current_username  # Use the current username

        top_n = int(input("Enter the number of top tanks to display: "))
        display_top_tanks(username, top_n)

        continue_prompt = input(
            "\nChoose an option:\n1. Check other data for the same player\n2. Check another player\n3. End program\n> ").strip().lower()

        if continue_prompt == '1':
            continue  # This keeps the current player and allows the user to fetch other data
        elif continue_prompt == '2':
            current_username = None  # Reset the current player to allow entering a new username
        elif continue_prompt == '3':
            print("\nMission complete. Returning to garage...")
            break
        else:
            print("Invalid option, please choose again.")


if __name__ == "__main__":
    main()
