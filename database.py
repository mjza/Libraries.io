import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

# Connect to the database
def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

# Create schema and table
def create_table():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Platforms (
                    name TEXT PRIMARY KEY,
                    project_count INTEGER,
                    homepage TEXT,
                    color TEXT,
                    default_language TEXT
                );
            """)
            conn.commit()

# Insert or update platforms data
def insert_platforms(platforms):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for platform in platforms:
                cur.execute("""
                    INSERT INTO Platforms (name, project_count, homepage, color, default_language)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE 
                    SET project_count = EXCLUDED.project_count,
                        homepage = EXCLUDED.homepage,
                        color = EXCLUDED.color,
                        default_language = EXCLUDED.default_language;
                """, (
                    platform["name"],
                    platform["project_count"],
                    platform["homepage"],
                    platform["color"],
                    platform["default_language"]
                ))
            conn.commit()
