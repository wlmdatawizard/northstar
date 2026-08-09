import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

files = list(DATA_DIR.glob("*"))

for file in files:
    print(file.name)
