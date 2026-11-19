"""CI helper: block until SQL Server accepts connections, then create the
database for the service under test. Usage: python wait_for_sqlserver.py <dbname>

Reads the SA password from MSSQL_SA_PASSWORD. Connects as sa only to bootstrap
the database; the application itself connects via DATABASE_URL.
"""
import os
import sys
import time

import pymssql

db = sys.argv[1]
password = os.environ["MSSQL_SA_PASSWORD"]

last_error = None
for attempt in range(30):
    try:
        conn = pymssql.connect(
            server="127.0.0.1", port=1433, user="sa",
            password=password, autocommit=True,
        )
        conn.cursor().execute(f"IF DB_ID('{db}') IS NULL CREATE DATABASE [{db}]")
        conn.close()
        print(f"SQL Server ready; database '{db}' ensured.")
        break
    except Exception as exc:  # noqa: BLE001 - CI readiness probe
        last_error = exc
        print(f"waiting for SQL Server (attempt {attempt + 1})... {exc}")
        time.sleep(3)
else:
    raise SystemExit(f"SQL Server never became ready: {last_error}")
