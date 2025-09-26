import psycopg2
from typing import Dict, List, Any
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_URL

DUMMY_DATA: Dict[str, Dict[str, List[str]]] = {
    "Home & Garden": {
        "Smart Home Devices": [
            "smart thermostat",
            "voice assistant speaker",
            "smart lighting",
            "home security camera"
        ],
        "Outdoor Living": [
            "patio furniture set",
            "outdoor grill",
            "garden shed",
            "fire pit"
        ]
    },
    "Athletic Footwear": {
        "Men's Running Shoes": [
            "lightweight running shoes men",
            "trail running sneakers for men",
            "marathon running shoes male"
        ],
        "Women's Sneakers": [
            "casual sneakers for women",
            "retro women's sneakers",
            "platform sneakers"
        ]
    },
    "Digital Marketing Software": {
        "SEO Tools": [
            "keyword research tool",
            "backlink checker software",
            "SEO rank tracker",
            "on-page SEO analyzer"
        ],
        "Social Media Management": [
            "social media scheduler",
            "analytics for social media",
            "social media listening tools"
        ]
    }
}


def populate_dummy_data():
    """
    Clears existing data and populates the database with dummy data following
    the category -> ad_group -> keyword structure.
    """
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # Disable autocommit for transactional safety
        conn.autocommit = False

        # Clear existing data
        print("Clearing existing data...")
        cur.execute("DELETE FROM keywords;")
        cur.execute("DELETE FROM ad_groups;")
        cur.execute("DELETE FROM categories;")

        # Reset the ID sequences for all three tables
        cur.execute("ALTER SEQUENCE keywords_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE ad_groups_id_seq RESTART WITH 1;")
        cur.execute("ALTER SEQUENCE categories_id_seq RESTART WITH 1;")
        print("Existing data cleared and sequences reset.")

        # Insert dummy data
        for category_name, ad_groups in DUMMY_DATA.items():
            # Insert category and get its ID
            cur.execute(
                "INSERT INTO categories (name) VALUES (%s) RETURNING id;",
                (category_name,)
            )
            category_id = cur.fetchone()[0]
            print(f"Inserted category: {category_name} (ID: {category_id})")

            for group_name, keywords in ad_groups.items():
                # Insert ad group and get its ID
                cur.execute(
                    "INSERT INTO ad_groups (name, category_id) VALUES (%s, %s) RETURNING id;",
                    (group_name, category_id)
                )
                group_id = cur.fetchone()[0]
                print(f"  -> Inserted ad group: {group_name} (ID: {group_id})")

                # Insert associated keywords
                for keyword in keywords:
                    cur.execute(
                        "INSERT INTO keywords (keyword, ad_group_id) VALUES (%s, %s);",
                        (keyword, group_id)
                    )
                    print(f"    -> Inserted keyword: {keyword}")

        # Commit all transactions
        conn.commit()
        print("\nDatabase populated with dummy data successfully.")


    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error while populating database: {error}")
        if conn:
            conn.rollback()  # Rollback changes if an error occurs
    finally:
        if conn is not None:
            conn.close()
            print("Database connection closed.")


if __name__ == "__main__":
    populate_dummy_data()