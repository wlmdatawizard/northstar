import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

files = list(DATA_DIR.glob("*"))

# for file in files:
#     print(file.name)

files = list(DATA_DIR.glob("*.csv"))

for file in files:
    df = pd.read_csv(file)

    print(file.name)
    print(df.shape)
