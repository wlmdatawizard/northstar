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


def audit_claims():
    name, df = "claims", claims
    row_count, column_count = df.shape
    dup_row_count = df.duplicated().sum()
    dup_claim_id_count = df["CLAIM_ID"].duplicated().sum()
    missing_claim_id_count = df["CLAIM_ID"].isna().sum()
    missing_patient_id_count = df["PATIENT_ID"].isna().sum()
    missing_encounter_id_count = df["ENCOUNTER_ID"].isna().sum()
    claim_amount = pd.to_numeric(df["CLAIM_AMOUNT"], errors="coerce")
    negative_claim_amount_count = (claim_amount < 0).sum()

    print(f"=" * 40)
    print(f"NORTHSTAR SOURCE DATA BASELINE AUDIT")
    print(f"=" * 40)

    print(f"\n[Claims]\n")
    print(f"{'Rows:':<26}{row_count}")
    print(f"{'Columns:':<26}{column_count}")
    print(f"{'Duplicate Rows:':<26}{dup_row_count}")
    print(f"{'Duplicate Claim IDs:':<26}{dup_claim_id_count}")
    print(f"{'Missing Claim IDs:':<26}{missing_claim_id_count}")
    print(f"{'Missing Patient IDs:':<26}{missing_patient_id_count}")
    print(f"{'Missing Encounter IDs:':<26}{missing_encounter_id_count}")
    print(f"{'Negative Claim Amounts:':<26}{negative_claim_amount_count}")
    print(f"\n{'-' * 40}")


def audit_encounters():
    name, df = "encounters", encounters
    row_count, column_count = df.shape
    dup_row_count = df.duplicated().sum()
    dup_encounter_id_count = df["ENCOUNTER_ID"].duplicated().sum()
    missing_patient_id_count = df["PATIENT_ID"].isna().sum()
    missing_provider_id_count = df["PROVIDER_ID"].isna().sum()
    missing_encounter_id_count = df["ENCOUNTER_ID"].isna().sum()
    print(f"\n[Encounters]\n")
    print(f"{'Rows:':<26}{row_count}")
    print(f"{'Columns:':<26}{column_count}")
    print(f"{'Duplicate Rows:':<26}{dup_row_count}")
    print(f"{'Duplicate Encounter IDs:':<26}{dup_encounter_id_count}")
    print(f"{'Missing Patient IDs:':<26}{missing_patient_id_count}")
    print(f"{'Missing Provider IDs:':<26}{missing_provider_id_count}")
    print(f"{'Missing Encounter IDs:':<26}{missing_encounter_id_count}")
    print(f"\n{'-' * 40}")


def audit_patients():
    name, df = "patients", patients
    row_count, column_count = df.shape
    dup_row_count = df.duplicated().sum()
    dup_patient_id_count = df["PATIENT_ID"].duplicated().sum()
    missing_patient_id_count = df["PATIENT_ID"].isna().sum()

    print(f"\n[Patients]\n")
    print(f"{'Rows:':<26}{row_count}")
    print(f"{'Columns:':<26}{column_count}")
    print(f"{'Duplicate Rows:':<26}{dup_row_count}")
    print(f"{'Duplicate Patient IDs:':<26}{dup_patient_id_count}")
    print(f"{'Missing Patient IDs:':<26}{missing_patient_id_count}")
    print(f"\n{'-' * 40}")


def audit_providers():
    name, df = "providers", providers
    row_count, column_count = df.shape
    dup_row_count = df.duplicated().sum()
    dup_provider_id_count = df["PROVIDER_ID"].duplicated().sum()
    missing_provider_id_count = df["PROVIDER_ID"].isna().sum()

    print(f"\n[Providers]\n")
    print(f"{'Rows:':<26}{row_count}")
    print(f"{'Columns:':<26}{column_count}")
    print(f"{'Duplicate Rows:':<26}{dup_row_count}")
    print(f"{'Duplicate Provider IDs:':<26}{dup_provider_id_count}")
    print(f"{'Missing Provider IDs:':<26}{missing_provider_id_count}")
    print(f"\n{'-' * 40}")


def main():
    audit_claims()
    audit_encounters()
    audit_patients()
    audit_providers()


if __name__ == "__main__":
    main()
