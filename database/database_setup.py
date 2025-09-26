import psycopg2
from psycopg2 import sql
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_URL

def setup_database():
    """
    Connects to the PostgreSQL database and creates the necessary tables
    if they do not already exist, with a category > ad_group > keyword structure.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Create the 'categories' table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create the 'ad_groups' table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ad_groups (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create the 'keywords' table with a foreign key to 'ad_groups'
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id SERIAL PRIMARY KEY,
                keyword TEXT UNIQUE NOT NULL,
                ad_group_id INTEGER REFERENCES ad_groups(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        print("Database schema created or updated successfully with the new structure.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error while setting up the database: {error}")
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    setup_database()