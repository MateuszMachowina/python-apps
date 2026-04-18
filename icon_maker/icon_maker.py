from PIL import Image

# 1. Wczytaj swój oryginalny plik PNG
img = Image.open('ikonka.png')

# 2. Pobierz jego wymiary i znajdź dłuższy bok
szerokosc, wysokosc = img.size
max_bok = max(szerokosc, wysokosc)

# 3. Stwórz nowy, całkowicie przezroczysty obraz, który jest idealnym kwadratem
tlo = Image.new('RGBA', (max_bok, max_bok), (255, 255, 255, 0))

# 4. Oblicz środek i wklej na niego swój czołg
offset = ((max_bok - szerokosc) // 2, (max_bok - wysokosc) // 2)
tlo.paste(img, offset)

# 5. Zapisz gotowy kwadrat do formatu ICO ze wszystkimi rozmiarami
tlo.save(
    'icon.ico', 
    format='ICO', 
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
)

print("Sukces! Stworzono idealnie kwadratową i ostrą ikonę.")
