"""
Database schema manager.

Responsibility:
    Applies all SQL schema files to the database.

Does NOT:
    - execute business logic;
    - know about repositories;
    - know about models.
"""

from pathlib import Path

SQL_DIRECTORY = Path(__file__).parent / "sql"


def get_schema_files() -> list[Path]:
    """
    Return all SQL schema files sorted by filename.
    """

    return sorted(SQL_DIRECTORY.glob("*.sql"))
