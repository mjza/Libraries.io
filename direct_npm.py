import requests
import psycopg2
from psycopg2.extras import execute_values
import time
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()

# Database connection settings
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}

BATCH_SIZE = 10  # Number of projects to process per batch
NPM_API_URL = "https://registry.npmjs.org/{package}"

# Connect to PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

def fetch_npm_data(package_name):
    """Fetch package metadata from NPM Registry."""
    url = NPM_API_URL.format(package=package_name)
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            try:
                return response.json()  # Ensure response is valid JSON
            except json.JSONDecodeError:
                print(f"Invalid JSON response for {package_name}")
                return None
        else:
            print(f"Failed to fetch {package_name}: HTTP {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"Error fetching {package_name}: {e}")
        return None

def extract_data(npm_data):
    """Extract relevant fields from NPM response."""
    if not isinstance(npm_data, dict):
        print("Unexpected response format, skipping entry.")
        return None

    repository_data = npm_data.get("repository", {})
    repository_url = None
    if isinstance(repository_data, str):  # Handle case where 'repository' is a string
        repository_url = repository_data
    elif isinstance(repository_data, dict):
        repository_url = repository_data.get("url")

    if repository_url and repository_url.startswith("git+"):
        repository_url = repository_url[4:]  # Remove "git+"

    return {
        "description": npm_data.get("description"),
        "homepage": npm_data.get("homepage"),
        "repository_url": repository_url,
        "latest_release_number": npm_data.get("dist-tags", {}).get("latest"),
        "latest_release_published_at": npm_data.get("time", {}).get(npm_data.get("dist-tags", {}).get("latest")),
        "raw": npm_data  # Store full JSON response for future reference
    }

def update_database(updates):
    """Bulk update projects table."""
    query = """
        UPDATE public.projects AS p
        SET
            description = COALESCE(data.description, p.description),
            homepage = COALESCE(data.homepage, p.homepage),
            repository_url = COALESCE(data.repository_url, p.repository_url),
            latest_release_number = COALESCE(data.latest_release_number, p.latest_release_number),
            latest_release_published_at = COALESCE(data.latest_release_published_at, p.latest_release_published_at),
            raw = COALESCE(data.raw, p.raw)
        FROM (VALUES %s) AS data(id, description, homepage, repository_url, latest_release_number, latest_release_published_at, raw)
        WHERE p.id = data.id;
    """
    execute_values(cursor, query, updates)
    conn.commit()

def process_batches():
    """Fetch missing data and update in batches."""
    offset = 0
    while True:
        cursor.execute("""
            SELECT id, name FROM public.projects 
            WHERE repository_url IS NULL OR description IS NULL OR homepage IS NULL
            ORDER BY id LIMIT %s OFFSET %s;
        """, (BATCH_SIZE, offset))
        projects = cursor.fetchall()

        if not projects:
            print("No more projects to update.")
            break

        updates = []
        for project_id, package_name in projects:
            npm_data = fetch_npm_data(package_name)
            if npm_data:
                extracted_data = extract_data(npm_data)
                if extracted_data:
                    updates.append((
                        project_id, extracted_data["description"], extracted_data["homepage"],
                        extracted_data["repository_url"], extracted_data["latest_release_number"],
                        extracted_data["latest_release_published_at"], extracted_data["raw"]
                    ))

        if updates:
            update_database(updates)
            print(f"Updated {len(updates)} projects.")

        offset += BATCH_SIZE
        time.sleep(2)  # Avoid API rate limits

# Run the batch update process
process_batches()

# Close database connection
cursor.close()
conn.close()
