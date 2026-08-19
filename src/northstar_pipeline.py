import os
from pathlib import Path
import snowflake.connector
from dotenv import load_dotenv
import csv


load_dotenv()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE")
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA")
SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")


def get_snowflake_connection():
    return snowflake.connector.connect(
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        account=SNOWFLAKE_ACCOUNT,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        role=SNOWFLAKE_ROLE
    )


def test_connection(cursor):
    cursor.execute(
        "SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
        "CURRENT_DATABASE(), CURRENT_SCHEMA();"
    )

    print(cursor.fetchone())


def create_file_format(cursor):
    sql = """
    CREATE FILE FORMAT IF NOT EXISTS NORTHSTAR.RAW.NORTHSTAR_CSV_FORMAT
        TYPE = 'CSV'
        FIELD_DELIMITER = ','
        SKIP_HEADER = 1
        FIELD_OPTIONALLY_ENCLOSED_BY = '"'
        EMPTY_FIELD_AS_NULL = TRUE;
    """

    cursor.execute(sql)
    row = cursor.fetchone()

    if row:
        return row[0]

    return "Format command completed with no message returned."


def create_stage(cursor):
    sql = """
    CREATE STAGE IF NOT EXISTS NORTHSTAR.RAW.NORTHSTAR_STAGE
        FILE_FORMAT = NORTHSTAR.RAW.NORTHSTAR_CSV_FORMAT;
    """

    cursor.execute(sql)

    row = cursor.fetchone()

    if row:
        return row[0]

    return "Stage command completed with no message returned."


def upload_files(cursor):
    files = list(DATA_DIR.glob("*.csv"))

    if not files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

    results = []

    for file in files:
        sql = f"""
        PUT 'file://{file.as_posix()}'
        @NORTHSTAR.RAW.NORTHSTAR_STAGE
        AUTO_COMPRESS = TRUE
        OVERWRITE = TRUE;
        """

        cursor.execute(sql)
        rows = cursor.fetchall()

        results.append((file.name, rows))

    cursor.execute("LIST @NORTHSTAR.RAW.NORTHSTAR_STAGE;")
    staged_files = cursor.fetchall()

    return results, staged_files


def validate_staged_files(cursor):
    validations = [
        (
            "billing_claims_dirty.csv.gz",
            "NORTHSTAR.RAW.BILLING_CLAIMS_RAW"
        ),
        (
            "encounter_info_dirty.csv.gz",
            "NORTHSTAR.RAW.ENCOUNTER_INFO_RAW"
        ),
        (
            "patient_info_dirty.csv.gz",
            "NORTHSTAR.RAW.PATIENT_INFO_RAW"
        ),
        (
            "provider_info_dirty.csv.gz",
            "NORTHSTAR.RAW.PROVIDER_INFO_RAW"
        )
    ]

    results = []

    for file_name, table_name in validations:
        sql = f"""
        COPY INTO {table_name}
        FROM @NORTHSTAR.RAW.NORTHSTAR_STAGE/{file_name}
        FILE_FORMAT = (FORMAT_NAME = 'NORTHSTAR.RAW.NORTHSTAR_CSV_FORMAT')
        VALIDATION_MODE = 'RETURN_ALL_ERRORS';
        """

        cursor.execute(sql)
        rows = cursor.fetchall()

        results.append((file_name, rows))

    return results


def count_csv_rows(file_path):
    with open(file_path, newline="", encoding="utf-8") as file:
        reader = csv.reader(file)

        next(reader, None)

        return sum(1 for _ in reader)


def get_source_row_counts():
    return {
        "BILLING_CLAIMS_RAW": count_csv_rows(
            DATA_DIR / "billing_claims_dirty.csv"
        ),
        "ENCOUNTER_INFO_RAW": count_csv_rows(
            DATA_DIR / "encounter_info_dirty.csv"
        ),
        "PATIENT_INFO_RAW": count_csv_rows(
            DATA_DIR / "patient_info_dirty.csv"
        ),
        "PROVIDER_INFO_RAW": count_csv_rows(
            DATA_DIR / "provider_info_dirty.csv"
        )
    }


def get_raw_counts(cursor):
    sql = """
    SELECT 'BILLING_CLAIMS_RAW', COUNT(*)
    FROM NORTHSTAR.RAW.BILLING_CLAIMS_RAW
    UNION ALL
    SELECT 'ENCOUNTER_INFO_RAW', COUNT(*)
    FROM NORTHSTAR.RAW.ENCOUNTER_INFO_RAW
    UNION ALL
    SELECT 'PATIENT_INFO_RAW', COUNT(*)
    FROM NORTHSTAR.RAW.PATIENT_INFO_RAW
    UNION ALL
    SELECT 'PROVIDER_INFO_RAW', COUNT(*)
    FROM NORTHSTAR.RAW.PROVIDER_INFO_RAW
    """

    cursor.execute(sql)
    return dict(cursor.fetchall())


def load_raw_tables(cursor):
    loads = [
        (
            "billing_claims_dirty.csv.gz",
            "NORTHSTAR.RAW.BILLING_CLAIMS_RAW"
        ),
        (
            "encounter_info_dirty.csv.gz",
            "NORTHSTAR.RAW.ENCOUNTER_INFO_RAW"
        ),
        (
            "patient_info_dirty.csv.gz",
            "NORTHSTAR.RAW.PATIENT_INFO_RAW"
        ),
        (
            "provider_info_dirty.csv.gz",
            "NORTHSTAR.RAW.PROVIDER_INFO_RAW"
        )
    ]

    results = []

    for file_name, table_name in loads:
        sql = f"""
        COPY INTO {table_name}
        FROM @NORTHSTAR.RAW.NORTHSTAR_STAGE/{file_name}
        FILE_FORMAT = (FORMAT_NAME = 'NORTHSTAR.RAW.NORTHSTAR_CSV_FORMAT');
        """

        cursor.execute(sql)
        rows = cursor.fetchall()

        results.append((table_name, rows))

    return results


def reconcile_load_counts(source_counts, before_counts, after_counts):
    results = []

    for table_name, source_count in source_counts.items():
        before_count = before_counts[table_name]
        after_count = after_counts[table_name]

        loaded_count = after_count - before_count

        if loaded_count == source_count:
            status = "MATCH"
        else:
            status = "MISMATCH"

        results.append(
            (
                table_name,
                source_count,
                before_count,
                after_count,
                loaded_count,
                status
            )
        )

    return results


def process_validated_load(cursor, validation_results):
    all_valid = True

    for _, rows in validation_results:
        if rows:
            all_valid = False

    if all_valid:
        source_counts = get_source_row_counts()
        before_counts = get_raw_counts(cursor)

        load_results = load_raw_tables(cursor)

        after_counts = get_raw_counts(cursor)

        reconciliation_results = reconcile_load_counts(
            source_counts,
            before_counts,
            after_counts
        )
    else:
        load_results = None
        reconciliation_results = None

    return all_valid, load_results, reconciliation_results


def print_upload_results(upload_results):
    for file_name, rows in upload_results:
        print(f"\nUploaded: {file_name}")

        for row in rows:
            print(row)


def print_staged_files(staged_files):
    print("\nFiles currently in stage:")

    for row in staged_files:
        print(row)


def print_validation_results(validation_results, all_valid):
    for file_name, rows in validation_results:
        print(f"\nValidation: {file_name}")

        if rows:
            for row in rows:
                print(row)
        else:
            print("No validation errors returned.")

    if all_valid:
        print(
            "\nPre-load validation complete: "
            "all staged files passed validation."
        )
    else:
        print(
            "\nPre-load validation completed with "
            "one or more validation errors."
        )


def print_load_results(load_results):
    if load_results is None:
        print("\nRAW table load was skipped.")
        return

    for table_name, rows in load_results:
        print(f"\nLoad results: {table_name}")

        for row in rows:
            print(row)


def print_reconciliation_results(reconciliation_results):
    if reconciliation_results is None:
        return

    print("\nRAW row-count reconciliation:")

    for (
        table_name,
        source_count,
        before_count,
        after_count,
        loaded_count,
        status
    ) in reconciliation_results:

        print(
            f"{table_name:<25} "
            f"Source: {source_count:<8} "
            f"Before Load: {before_count:<8} "
            f"After Load: {after_count:<8} "
            f"Loaded: {loaded_count:<8} "
            f"{status}"
        )


def print_pipeline_results(upload_results, staged_files, validation_results, all_valid, load_results, reconciliation_results):
    print("\nSnowflake connection successfully closed.")

    print_upload_results(upload_results)
    print_staged_files(staged_files)
    print_validation_results(validation_results, all_valid)
    print_load_results(load_results)
    print_reconciliation_results(reconciliation_results)


def main():
    try:
        with get_snowflake_connection() as conn:
            with conn.cursor() as cursor:
                create_file_format(cursor)
                create_stage(cursor)

                upload_results, staged_files = upload_files(cursor)
                validation_results = validate_staged_files(cursor)

                (all_valid, load_results, reconciliation_results) = process_validated_load(cursor, validation_results)

        print_pipeline_results(upload_results, staged_files, validation_results, all_valid, load_results, reconciliation_results)

    except FileNotFoundError as e:
        print(
            "Source file error: One or more required files could not be found. "
            f"Details: {e}"
        )
        raise

    except PermissionError as e:
        print(
            "Permission error: Python does not have permission to access "
            f"a required file or directory. Details: {e}"
        )
        raise

    except snowflake.connector.errors.ProgrammingError as e:
        print(
            "Snowflake SQL error: A SQL statement failed or referenced "
            f"an invalid Snowflake object. Details: {e}"
        )
        raise

    except snowflake.connector.errors.OperationalError as e:
        print(
            "Snowflake operational error: The connection or database operation "
            f"could not be completed. Details: {e}"
        )
        raise

    except snowflake.connector.errors.InterfaceError as e:
        print(
            "Snowflake connector error: The Python connector encountered "
            f"an interface or connection problem. Details: {e}"
        )
        raise

    except snowflake.connector.errors.DatabaseError as e:
        print(
            "Snowflake database error: An unexpected database-related "
            f"failure occurred. Details: {e}"
        )
        raise

    except Exception as e:
        print(f"Unexpected pipeline error: {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
