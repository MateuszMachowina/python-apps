import pandas as pd

df = pd.read_csv(r"C:\Users\macho\Desktop\FIFA 15 Pack Simulator\players.csv", sep=";")
df.to_json("players.json", orient="records", indent=4)
