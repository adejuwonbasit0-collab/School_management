"""
Repairs an existing (pre-existing / already-deployed) database that:
  1. Is missing tables that were added to the models but never migrated
     (faq_items, ui_components, hosting_servers, product_reviews,
     project_requests, short_urls, shortened_urls, client_projects,
     project_milestones, project_updates), and/or
  2. Has its alembic_version stamped at a revision that no longer exists
     in migrations/versions/ (this happens if a migration file was ever
     deleted/replaced without updating databases that already ran it).

This does NOT drop or modify any existing data. It only adds what's
missing, then aligns the alembic version stamp so `flask db upgrade`
works normally from now on.

Run with: python -m scripts.repair_db
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import inspect, text
from app import create_app
from app.extensions import db

KNOWN_GOOD_REVISIONS = {"8a20331e7818", "69bda5ddb9f2", "318bfff7aca2", "b6c355e2dd75", "5d76627460b2", "6b19ca3cfb52", "88e4d617f8d0", "da69a7eb0ebc", "1fb0d1cfca39", "578c399ae2c4"}

app = create_app("development")

with app.app_context():
    insp = inspect(db.engine)
    existing_tables = set(insp.get_table_names())

    # 1. Create any tables that are in the models but missing from the DB.
    #    create_all() only creates tables that don't already exist, so this
    #    is safe to run against a database that already has data.
    db.create_all()

    insp = inspect(db.engine)
    new_tables = set(insp.get_table_names()) - existing_tables
    if new_tables:
        print(f"Created missing tables: {', '.join(sorted(new_tables))}")
    else:
        print("No missing tables found.")

    # 2. Fix the analytics_events column rename if the old column name
    #    is still present (older DBs created before the rename).
    cols = {c["name"] for c in insp.get_columns("analytics_events")} if "analytics_events" in insp.get_table_names() else set()
    if "event_metadata" in cols and "metadata" not in cols:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE analytics_events RENAME COLUMN event_metadata TO metadata"))
        print("Renamed analytics_events.event_metadata -> metadata")

    # 3. Align the alembic_version stamp so `flask db upgrade` works going forward.
    if "alembic_version" in insp.get_table_names():
        with db.engine.begin() as conn:
            current = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            if current not in KNOWN_GOOD_REVISIONS:
                conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": "578c399ae2c4"})
                print(f"Fixed broken alembic stamp: '{current}' -> '578c399ae2c4'")
            elif current != "578c399ae2c4":
                conn.execute(text("UPDATE alembic_version SET version_num = :v"), {"v": "578c399ae2c4"})
                print(f"Updated alembic stamp: '{current}' -> '578c399ae2c4'")
            else:
                print("Alembic stamp already up to date.")
    else:
        with db.engine.begin() as conn:
            conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
            conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('578c399ae2c4')"))
        print("Created alembic_version table and stamped at '578c399ae2c4'")

    print("\nDatabase repair complete. Run `python -m scripts.seed` next to fill in any missing sample data.")
