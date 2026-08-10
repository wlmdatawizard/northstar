import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

files = list(DATA_DIR.glob("*.csv"))

dataframes = {}

for file in files:
    dataframes[file.stem] = pd.read_csv(file)
    # print(file.name)
    # print(dataframes[file.stem].shape)

claims = dataframes["billing_claims_dirty"]
encounters = dataframes["encounter_info_dirty"]
patients = dataframes["patient_info_dirty"]
providers = dataframes["provider_info_dirty"]
print("\n")
print(f"| {'name':<25}| {'rows':<10}| {'columns':<10}| {"Dup_Row":<10} |")
print("-" * 65)

for name, df in dataframes.items():
    row_count, column_count = df.shape
    data_type = df.dtypes.to_string()
    null_count = df.isna().sum().sum()
    dup_count = df.duplicated().sum()

    print(f"| {name:<25}| {row_count:<10}| {column_count:<10}| {dup_count:<10} |")
print("\n")
