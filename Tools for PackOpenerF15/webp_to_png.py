from PIL import Image
import os

# Folder źródłowy z webp
input_folder = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\webp"
# Folder docelowy (nadrzędny, gdzie będą PNG)
output_folder = r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\png"

os.makedirs(output_folder, exist_ok=True)

for file in os.listdir(input_folder):
    if file.endswith(".webp"):
        img_path = os.path.join(input_folder, file)
        img = Image.open(img_path)
        png_file = os.path.join(output_folder, file.replace(".webp", ".png"))
        img.save(png_file, "PNG")
        print(f"Skonwertowano: {file} -> {png_file}")

print("Konwersja zakończona ✔️")
