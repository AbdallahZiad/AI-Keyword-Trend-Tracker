import sys
from pathlib import Path
import psycopg2
import psycopg2.extras
from psycopg2 import sql
from typing import Dict, List, Any, Optional

# Add the project root to sys.path for module imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_client import DBClient
from config.settings import DATABASE_URL


def run_tests():
    """
    Runs a series of tests on the DBClient.
    This version cleans up after each test to leave the database in its original state.
    """
    tests_passed = True

    print("\n--- Running Tests on Main Database ---")

    # Store IDs/names of new data for later cleanup
    new_category_ids = []
    new_ad_group_ids = []
    new_keyword_keywords = []

    try:
        with DBClient() as db:
            # Test 1: Upserting a new category
            print("\nTest 1: Upserting a new category...")
            cat_id = db.upsert_category("Test Category 1")
            new_category_ids.append(cat_id)
            if isinstance(cat_id, int):
                print(f"✅ Test 1 Passed. Category ID: {cat_id}")
            else:
                print("❌ Test 1 Failed.")
                tests_passed = False

            # Test 2: Upserting an existing category
            print("\nTest 2: Upserting an existing category...")
            cat_id_existing = db.upsert_category("Test Category 1")
            if cat_id == cat_id_existing:
                print("✅ Test 2 Passed. IDs match.")
            else:
                print("❌ Test 2 Failed.")
                tests_passed = False

            # Test 3: Upserting a new ad group
            print("\nTest 3: Upserting a new ad group...")
            group_id = db.upsert_ad_group("Test Ad Group 1", cat_id)
            new_ad_group_ids.append(group_id)
            if isinstance(group_id, int):
                print(f"✅ Test 3 Passed. Group ID: {group_id}")
            else:
                print("❌ Test 3 Failed.")
                tests_passed = False

            # Test 4: Upserting an existing ad group with a new category
            print("\nTest 4: Upserting an existing ad group with a new category...")
            cat_id_new = db.upsert_category("Test Category 2")
            new_category_ids.append(cat_id_new)
            group_id_new = db.upsert_ad_group("Test Ad Group 1", cat_id_new)
            if group_id == group_id_new:
                db.cur.execute("SELECT category_id FROM ad_groups WHERE id = %s;", (group_id_new,))
                updated_cat_id = db.cur.fetchone()['category_id']
                if updated_cat_id == cat_id_new:
                    print("✅ Test 4 Passed. Group updated and ID matched.")
                else:
                    print("❌ Test 4 Failed. Category ID was not updated.")
                    tests_passed = False
            else:
                print("❌ Test 4 Failed. Group IDs did not match.")
                tests_passed = False

            # Test 5: Upserting a new keyword
            print("\nTest 5: Upserting a new keyword...")
            db.upsert_keyword("test keyword 1", group_id_new)
            new_keyword_keywords.append("test keyword 1")
            db.cur.execute("SELECT keyword FROM keywords WHERE keyword = %s;", ("test keyword 1",))
            keyword_exists = db.cur.fetchone() is not None
            if keyword_exists:
                print("✅ Test 5 Passed. Keyword inserted.")
            else:
                print("❌ Test 5 Failed.")
                tests_passed = False

            # Test 6: Upserting a keyword with an updated ad group
            print("\nTest 6: Upserting a keyword with a new group...")
            group_id_new_group = db.upsert_ad_group("Test Ad Group 2", cat_id)
            new_ad_group_ids.append(group_id_new_group)
            db.upsert_keyword("test keyword 1", group_id_new_group)
            db.cur.execute("SELECT ad_group_id FROM keywords WHERE keyword = %s;", ("test keyword 1",))
            updated_group_id = db.cur.fetchone()['ad_group_id']
            if updated_group_id == group_id_new_group:
                print("✅ Test 6 Passed. Keyword's group updated.")
            else:
                print("❌ Test 6 Failed.")
                tests_passed = False

            # Test 7: Get all categories
            print("\nTest 7: Getting all categories...")
            all_categories_before = db.get_all_categories()
            # Insert a temporary category to check if get_all_categories works as expected
            temp_cat_id = db.upsert_category("Temporary Category")
            new_category_ids.append(temp_cat_id)
            all_categories_after = db.get_all_categories()
            if len(all_categories_after) == len(all_categories_before) + 1:
                print("✅ Test 7 Passed. Correct categories retrieved.")
            else:
                print("❌ Test 7 Failed.")
                tests_passed = False

            # Test 8: Get keywords by category
            print("\nTest 8: Getting keywords by category...")
            db.upsert_keyword("test keyword 2", group_id_new_group)
            new_keyword_keywords.append("test keyword 2")
            keywords = db.get_keywords_by_category(cat_id)
            if len(keywords) == 2 and sorted([k['keyword'] for k in keywords]) == ["test keyword 1", "test keyword 2"]:
                print("✅ Test 8 Passed. Correct keywords retrieved.")
            else:
                print("❌ Test 8 Failed.")
                tests_passed = False

            # Test 9: Count keywords
            print("\nTest 9: Counting keywords...")
            count_before = db.count_keywords()
            db.upsert_keyword("test keyword 3", group_id_new_group)
            new_keyword_keywords.append("test keyword 3")
            count_after = db.count_keywords()
            if count_after == count_before + 1:
                print("✅ Test 9 Passed. Correct keyword count.")
            else:
                print("❌ Test 9 Failed.")
                tests_passed = False

    except Exception as e:
        print(f"\n❌ An unexpected error occurred during tests: {e}")
        tests_passed = False

    finally:
        # Cleanup section to revert the database to its original state
        print("\n--- Cleaning up temporary test data ---")
        try:
            with DBClient() as db:
                # Delete keywords first due to foreign key constraints
                if new_keyword_keywords:
                    sql_keywords_to_delete = sql.SQL("DELETE FROM keywords WHERE keyword IN ({});").format(
                        sql.SQL(', ').join(sql.Literal(kw) for kw in new_keyword_keywords)
                    )
                    db.cur.execute(sql_keywords_to_delete)

                # Delete ad groups next
                if new_ad_group_ids:
                    sql_groups_to_delete = sql.SQL("DELETE FROM ad_groups WHERE id IN ({});").format(
                        sql.SQL(', ').join(sql.Literal(id) for id in new_ad_group_ids)
                    )
                    db.cur.execute(sql_groups_to_delete)

                # Delete categories last
                if new_category_ids:
                    sql_categories_to_delete = sql.SQL("DELETE FROM categories WHERE id IN ({});").format(
                        sql.SQL(', ').join(sql.Literal(id) for id in new_category_ids)
                    )
                    db.cur.execute(sql_categories_to_delete)

                db.conn.commit()
                print("Temporary test data removed successfully.")
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")

    print("\n--- Test Summary ---")
    if tests_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED. Please review the output above.")


if __name__ == "__main__":
    run_tests()