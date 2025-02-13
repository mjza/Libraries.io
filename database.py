import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
import json

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

# Create tables
def create_tables():
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

                CREATE TABLE IF NOT EXISTS Projects (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    description TEXT,
                    homepage TEXT,
                    language TEXT,
                    repository_url TEXT,
                    package_manager_url TEXT,
                    rank INTEGER,
                    stars INTEGER,
                    forks INTEGER,
                    keywords TEXT[],
                    funding_urls TEXT[],
                    normalized_licenses TEXT[],
                    latest_release_number TEXT,
                    latest_release_published_at TIMESTAMP,
                    latest_stable_release_number TEXT,
                    latest_stable_release_published_at TIMESTAMP,
                    versions JSONB,
                    raw JSONB,
                    UNIQUE(name, platform)
                );

                CREATE INDEX IF NOT EXISTS idx_project_name ON Projects(name);
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

def insert_projects(platform, projects):
    """Insert projects into the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for project in projects:
                cur.execute("""
                    INSERT INTO Projects (
                        name, platform, description, homepage, language, repository_url, 
                        package_manager_url, rank, stars, forks, keywords, funding_urls, 
                        normalized_licenses, latest_release_number, latest_release_published_at, 
                        latest_stable_release_number, latest_stable_release_published_at, versions, raw
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (name, platform) DO UPDATE 
                    SET description = EXCLUDED.description,
                        homepage = EXCLUDED.homepage,
                        language = EXCLUDED.language,
                        repository_url = EXCLUDED.repository_url,
                        package_manager_url = EXCLUDED.package_manager_url,
                        rank = EXCLUDED.rank,
                        stars = EXCLUDED.stars,
                        forks = EXCLUDED.forks,
                        keywords = EXCLUDED.keywords,
                        funding_urls = EXCLUDED.funding_urls,
                        normalized_licenses = EXCLUDED.normalized_licenses,
                        latest_release_number = EXCLUDED.latest_release_number,
                        latest_release_published_at = EXCLUDED.latest_release_published_at,
                        latest_stable_release_number = EXCLUDED.latest_stable_release_number,
                        latest_stable_release_published_at = EXCLUDED.latest_stable_release_published_at,
                        versions = EXCLUDED.versions,
                        raw = EXCLUDED.raw;
                """, (
                    project["name"], platform, project.get("description"), project.get("homepage"),
                    project.get("language"), project.get("repository_url"), project.get("package_manager_url"),
                    project.get("rank"), project.get("stars"), project.get("forks"),
                    project.get("keywords", []), project.get("funding_urls", []),
                    project.get("normalized_licenses", []), project.get("latest_release_number"),
                    project.get("latest_release_published_at"), project.get("latest_stable_release_number"),
                    project.get("latest_stable_release_published_at"), json.dumps(project.get("versions", [])),
                    json.dumps(project)
                ))
            conn.commit()

