#!/usr/bin/env python3
"""Ingest the synthetic food-delivery dataset into SQLite.

Reads four CSVs under `data/` (produced by
`scripts/generate_demo_orders.py`) and loads them into the SQLite database
the agent's SQL tools query. Re-runnable: tables are dropped and recreated
each time.

Usage:
    make ingest-sql
    # or
    uv run python scripts/structured_data_ingestion_pipeline.py
"""

import logging
from pathlib import Path
import sqlite3
import sys

import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from core.settings import settings  # noqa: E402

# Maps source CSV filenames to SQLite table names. The order matters only
# insofar as dimensions load before the fact table so error messages are
# easier to read if something is missing.
CSV_TO_TABLE = {
    "DIM_CITY.csv": "dim_city",
    "DIM_DISH.csv": "dim_dish",
    "DIM_RESTAURANT.csv": "dim_restaurant",
    "FACT_ORDERS.csv": "fact_orders",
}


def ingest_csv_to_sqlite() -> None:
    """Load every CSV into the target SQLite database."""
    db_path = str(settings.DEFAULT_SQLITE_PATH)
    data_dir = Path("data")

    # Auto-generate the CSVs if they're missing — first-run convenience so
    # `make ingest-sql` works right after clone without a separate step.
    if not (data_dir / "FACT_ORDERS.csv").exists():
        logger.info("CSVs not found — running generate_demo_orders.py first")
        from scripts.generate_demo_orders import main as gen_main  # type: ignore

        gen_main()

    logger.info(f"Connecting to SQLite database: {db_path}")
    conn = sqlite3.connect(db_path)

    try:
        total_rows = 0

        for csv_file, table_name in CSV_TO_TABLE.items():
            file_path = data_dir / csv_file
            if not file_path.exists():
                logger.error(f"Missing CSV: {file_path}")
                raise FileNotFoundError(f"Expected CSV at {file_path}")

            logger.info(f"Processing {csv_file}...")
            df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(df):,} rows from {csv_file}")

            df.to_sql(table_name, conn, if_exists="replace", index=False)
            logger.info(f"Created table '{table_name}' with {len(df):,} rows")

            total_rows += len(df)

        logger.info(
            f"Successfully ingested {total_rows:,} total rows into {len(CSV_TO_TABLE)} tables"
        )

        # Summary table so the operator sees everything at a glance.
        logger.info("\nDatabase summary:")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        for (table_name,) in cursor.fetchall():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.info(f"  {table_name}: {count:,} rows")

        # Example sanity queries — these confirm the star schema JOINs work.
        logger.info("\nExample query 1: total orders by country")
        cursor.execute(
            """
            SELECT
                dc.country,
                SUM(fo.orders_count) AS total_orders,
                ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur
            FROM fact_orders fo
            JOIN dim_city dc ON fo.city_id = dc.city_id
            GROUP BY dc.country
            ORDER BY total_orders DESC
            """
        )
        for row in cursor.fetchall():
            print(f"  {row[0]:<15} {row[1]:>8}  €{row[2]:>12,.2f}")

        logger.info("\nExample query 2: top 5 dishes by orders")
        cursor.execute(
            """
            SELECT
                dd.dish_name,
                dd.cuisine,
                SUM(fo.orders_count) AS total_orders
            FROM fact_orders fo
            JOIN dim_dish dd ON fo.dish_id = dd.dish_id
            GROUP BY dd.dish_name, dd.cuisine
            ORDER BY total_orders DESC
            LIMIT 5
            """
        )
        for row in cursor.fetchall():
            print(f"  {row[0]:<28} {row[1]:<15} {row[2]:>8}")

        logger.info("\nData ingestion completed successfully!")
        logger.info(f"Database file: {db_path}")

    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        raise
    finally:
        conn.close()
        logger.info("Database connection closed")


def main() -> None:
    logger.info("Starting food-delivery data ingestion to SQLite...")
    ingest_csv_to_sqlite()


if __name__ == "__main__":
    main()
