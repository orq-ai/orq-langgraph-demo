#!/usr/bin/env python3
"""
Database initialization script for LangGraph deployment on LangSmith.

This script runs before the graph is loaded and ensures the SQLite database
is properly initialized using the existing structured data ingestion pipeline.
"""

import logging
from pathlib import Path
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from core.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize database using the existing structured data ingestion pipeline."""
    logger.info("Initializing SQLite database for LangGraph deployment...")

    try:
        # Import and run the existing structured data ingestion pipeline
        from scripts.structured_data_ingestion_pipeline import ingest_csv_to_sqlite

        # Check if database already exists and has data
        db_path = Path(settings.DEFAULT_SQLITE_PATH)
        if db_path.exists():
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            if table_count > 0:
                cursor.execute("SELECT COUNT(*) FROM dim_country")
                country_count = cursor.fetchone()[0]

                if country_count > 0:
                    logger.info("Database already contains data, skipping initialization")
                    conn.close()
                    return True

            conn.close()

        # Run the structured data ingestion pipeline
        logger.info("Running structured data ingestion pipeline...")
        ingest_csv_to_sqlite()

        logger.info("SQLite database initialization completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def main():
    """Main initialization function."""
    logger.info("Starting SQLite database initialization for LangGraph deployment...")

    if init_database():
        logger.info("Database initialization completed successfully!")
        return 0
    else:
        logger.error("Database initialization failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
