import requests

class WN8Provider:
    def __init__(self):
        self._cache = {}

    def get_expected_values(self) -> dict[int, dict]:
        if self._cache:
            return self._cache

        try:
            res = requests.get("https://static.modxvm.com/wn8-data-exp/json/wn8exp.json", timeout=5).json()
            self._cache = {item["IDNum"]: item for item in res["data"]}
            return self._cache
        except Exception as e:
            print(f"Błąd pobierania wartości oczekiwanych WN8: {e}")
            return {}
