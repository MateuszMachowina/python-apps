# WoT Stats Assistant 📊 🚀

WoT Stats Assistant to potężna i intuicyjna aplikacja desktopowa stworzona w Pythonie dla społeczności World of Tanks. Program pozwala na błyskawiczne monitorowanie statystyk gracza, śledzenie osiągnięć na poszczególnych czołgach oraz automatyczne obliczanie WN8 w oparciu o najświeższe dane oczekiwane.

## 🌟 Główne Funkcje

* **Wizytówka Gracza:** Podgląd kluczowych parametrów konta w jednym miejscu:
    * Oficjalny rating **WTR**.
    * Całkowity **WN8** konta (kolorowany według skali XVM).
    * Procent zwycięstw oraz łączna liczba bitew.
    * Rekordy życiowe (Max DMG i Max Fragi) wraz z ikoną i nazwą czołgu.
* **Szczegółowa Tabela Czołgów:** Pełna lista pojazdów w garażu z danymi:
    * **WN8 dla każdego czołgu** obliczany dynamicznie.
    * Średnie uszkodzenia i średnia liczba zniszczonych pojazdów.
    * Status odznak biegłości (**MoE**) – kliknij, aby zmienić!
* **System Oceny:** Własny system 5-gwiazdkowy pozwalający ocenić każdy pojazd pod kątem "Dobrej zabawy" i "Konkurencyjności".
* **Zaawansowane Filtrowanie:**
    * Filtrowanie po nacji, typie i tierze.
    * Filtr "Ulubione".
    * **Filtr minimalnej liczby bitew (20/50)** – odfiltruj pojazdy, którymi zagrałeś za mało razy, by statystyki były miarodajne.
* **Inteligentny Cache:** Ikony czołgów i dane encyklopedyczne są zapisywane lokalnie w bazie SQLite i folderze cache, co minimalizuje zużycie transferu i przyspiesza działanie aplikacji.

## 🛠️ Technologia

* **Język:** Python 3.x
* **GUI:** PyQt6
* **Baza danych:** SQLite3
* **API:** Wargaming.net API & XVM Expected Values (WN8)

## 🚀 Instalacja i Uruchomienie

### 1. Wymagania
Upewnij się, że masz zainstalowanego Pythona. Następnie zainstaluj wymagane biblioteki:

```bash
pip install PyQt6 requests python-dotenv
