import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import psycopg2
import psycopg2.extras
from psycopg2 import sql

# Add the project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import DATABASE_URL


class DBClient:
    """
    A comprehensive client for managing database operations related to
    keywords, categories, and ad groups.
    """

    def __init__(self):
        self.conn = None
        self.cur = None

    def __enter__(self):
        """
        Context manager method to establish a database connection.
        """
        try:
            # We explicitly set autocommit to False to manage transactions manually
            self.conn = psycopg2.connect(DATABASE_URL)
            self.conn.autocommit = False
            self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            return self
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error connecting to the database: {error}")
            raise error

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager method to close the database connection.
        """
        # Rollback in case of an exception to ensure a clean state
        if exc_type:
            print("Transaction failed, rolling back...")
            self.conn.rollback()

        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()

    def _execute_query(self, query: sql.Composable, params: Optional[tuple] = None) -> Optional[List[Dict]]:
        """
        A private helper to execute a query and handle common operations.
        Returns a list of dictionaries for results or None for operations
        like INSERT or UPDATE. This method no longer commits.
        """
        try:
            self.cur.execute(query, params)
            if self.cur.description:  # Check if the query returned results (e.g., SELECT)
                return self.cur.fetchall()
            return None
        except psycopg2.DatabaseError as e:
            # This rollback is just for a single failed query, but the main
            # transaction rollback in __exit__ will handle the overall failure.
            self.conn.rollback()
            print(f"Database error during query execution: {e}")
            return None

    # ------------------ CATEGORY METHODS ------------------

    def upsert_category(self, category_name: str) -> Optional[int]:
        """
        Inserts a new category or returns the ID of an existing one.
        Returns the category ID on success, None on failure.
        """
        query = sql.SQL("""
                        INSERT INTO categories (name)
                        VALUES (%s) ON CONFLICT (name) DO NOTHING
                        RETURNING id;
                        """)

        result = self._execute_query(query, (category_name,))

        # If the category was newly inserted, result will contain the ID
        if result and result[0]['id']:
            return result[0]['id']

        # If the category already existed, get its ID
        query = sql.SQL("SELECT id FROM categories WHERE name = %s;")
        result = self._execute_query(query, (category_name,))
        if result and result[0]['id']:
            return result[0]['id']

        return None

    def get_all_categories(self) -> List[Dict]:
        """
        Retrieves all categories from the database.
        Returns a list of dictionaries.
        """
        query = sql.SQL("SELECT id, name FROM categories ORDER BY name;")
        result = self._execute_query(query)
        return result if result else []

    # ------------------ AD GROUP METHODS ------------------

    def upsert_ad_group(self, group_name: str, category_id: int) -> Optional[int]:
        """
        Inserts a new ad group or updates an existing one's category.
        Returns the ad group ID on success, None on failure.
        """
        query = sql.SQL("""
                        INSERT INTO ad_groups (name, category_id)
                        VALUES (%s, %s) ON CONFLICT (name) DO
                        UPDATE
                            SET category_id = EXCLUDED.category_id
                            RETURNING id;
                        """)

        result = self._execute_query(query, (group_name, category_id))

        if result and result[0]['id']:
            return result[0]['id']

        # If the group already existed, get its ID
        query = sql.SQL("SELECT id FROM ad_groups WHERE name = %s;")
        result = self._execute_query(query, (group_name,))
        if result and result[0]['id']:
            return result[0]['id']

        return None

    def get_ad_groups_by_category(self, category_id: int) -> List[Dict]:
        """
        Retrieves all ad groups associated with a specific category ID.
        Returns a list of dictionaries with ad group name and ID.
        """
        query = sql.SQL("""
                        SELECT id, name
                        FROM ad_groups
                        WHERE category_id = %s
                        ORDER BY name;
                        """)
        result = self._execute_query(query, (category_id,))
        return result if result else []

    # ------------------ KEYWORD METHODS ------------------

    def upsert_keyword(self, keyword: str, ad_group_id: int):
        """
        Inserts a new keyword or updates the ad_group_id of an existing one.
        """
        query = sql.SQL("""
                        INSERT INTO keywords (keyword, ad_group_id)
                        VALUES (%s, %s) ON CONFLICT (keyword) DO
                        UPDATE
                            SET ad_group_id = EXCLUDED.ad_group_id;
                        """)
        self._execute_query(query, (keyword, ad_group_id))

    def get_keywords_by_category(self, category_id: int) -> List[Dict]:
        """
        Retrieves all keywords associated with a specific category ID.
        This uses a JOIN across categories, ad_groups, and keywords.
        Returns a list of dictionaries with keyword and ad group information.
        """
        query = sql.SQL("""
                        SELECT k.id    AS keyword_id,
                               k.keyword,
                               ag.id   AS ad_group_id,
                               ag.name AS ad_group_name
                        FROM keywords k
                                 JOIN ad_groups ag ON k.ad_group_id = ag.id
                        WHERE ag.category_id = %s
                        ORDER BY ag.name, k.keyword;
                        """)
        result = self._execute_query(query, (category_id,))
        return result if result else []

    def get_keywords_in_batches(self, batch_size: int, offset: int) -> List[Dict]:
        """
        Retrieves a batch of keywords for processing.
        Returns keyword, ad_group_id, and category_id.
        """
        query = sql.SQL("""
                        SELECT k.id  AS keyword_id,
                               k.keyword,
                               ag.id AS ad_group_id,
                               ag.category_id
                        FROM keywords k
                                 JOIN ad_groups ag ON k.ad_group_id = ag.id
                        ORDER BY k.id
                            LIMIT %s
                        OFFSET %s;
                        """)
        result = self._execute_query(query, (batch_size, offset))
        return result if result else []

    def count_keywords(self) -> int:
        """
        Counts the total number of keywords in the database.
        """
        query = sql.SQL("SELECT COUNT(*) FROM keywords;")
        result = self._execute_query(query)
        if result and result[0]:
            return result[0]['count']
        return 0

    def clear_all_data(self):
        """
        Truncates all relevant data tables to prepare for a fresh sync.
        This method no longer commits.
        """
        query = sql.SQL("TRUNCATE TABLE categories, ad_groups, keywords RESTART IDENTITY CASCADE;")
        self._execute_query(query)


if __name__ == '__main__':
    # This example demonstrates how to use the new three-tiered structure
    # NOTE: The __main__ block needs to be updated to manually commit as well.
    try:
        with DBClient() as db:
            print("Successfully connected to the database.")
            db.clear_all_data()

            # --- 1. Upsert a category ---
            cat_id = db.upsert_category("Fitness Gear")
            print(f"Upserted 'Fitness Gear' with ID: {cat_id}")

            # --- 2. Upsert an ad group linked to the category ---
            group_id = db.upsert_ad_group("Running Shoes", cat_id)
            print(f"Upserted 'Running Shoes' ad group with ID: {group_id} linked to category ID: {cat_id}")

            # --- 3. Upsert keywords linked to the ad group ---
            db.upsert_keyword("men's trail running shoes", group_id)
            db.upsert_keyword("women's lightweight running shoes", group_id)
            print("Upserted keywords for the 'Running Shoes' ad group.")

            # --- Commit the transaction to save all changes ---
            db.conn.commit()
            print("Transaction committed successfully.")

            # --- 4. Retrieve all data for the category via JOIN ---
            if cat_id:
                keywords_in_category = db.get_keywords_by_category(cat_id)
                print(f"\nKeywords for 'Fitness Gear' (ID: {cat_id}):")
                for kw in keywords_in_category:
                    print(f"- Keyword: {kw['keyword']}")
                    print(f"  - Belongs to Ad Group: {kw['ad_group_name']} (ID: {kw['ad_group_id']})")

            print(f"\nTotal keywords in database: {db.count_keywords()}")

    except Exception as e:
        print(f"An error occurred: {e}")