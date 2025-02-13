import os
import sys
import time
import requests
import psycopg2
from dotenv import load_dotenv
from database import get_db_connection, insert_projects

print("[INFO] Starting npm.py script...", flush=True)
sys.stdout.flush()
time.sleep(1)  # Ensure the message gets logged

# Load environment variables
load_dotenv()

# API and Rate Limit Settings
API_KEY = os.getenv("API_KEY")
SEARCH_URL = "https://libraries.io/api/search"
MAX_REQUESTS_PER_MINUTE = 59  # API Limit
REQUEST_WINDOW = 60  # Time window in seconds
request_count = 0
window_start_time = time.time()

# Fetch NPM package names from the database
def get_npm_packages(batch_size=1000, offset=0):
    """Fetches NPM package names in paginated batches from the database, 
    where raw has only one property or its only property is 'name'."""
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT name FROM Projects 
                WHERE platform = 'NPM' 
                AND (
                    jsonb_typeof(raw) = 'object' 
                    AND (
                        raw ? 'name' 
                        AND 
                        (SELECT COUNT(*) FROM jsonb_object_keys(raw)) = 1
                    )
                )
                ORDER BY name 
                LIMIT %s OFFSET %s;
                """,
                (batch_size, offset)
            )
            return [row[0] for row in cur.fetchall()]



# Query Libraries.io API for each NPM package
def fetch_npm_project(package_name):
    """Fetch package details from Libraries.io API with error handling."""
    global request_count, window_start_time

    # Enforce request limit
    elapsed_time = time.time() - window_start_time
    if request_count >= MAX_REQUESTS_PER_MINUTE:
        sleep_time = REQUEST_WINDOW - elapsed_time
        if sleep_time > 0:
            print(f"[INFO] Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        request_count = 0
        window_start_time = time.time()

    url = f"{SEARCH_URL}?platforms=NPM&q={package_name}&api_key={API_KEY}"

    try:
        response = requests.get(url)

        if response.status_code == 200:
            request_count += 1  # Increment request count
            return response.json()

        elif response.status_code == 400:
            print(f"[WARNING] Invalid package name: {package_name}. Skipping.")
            return None  # Ignore invalid names

        elif response.status_code == 429:  # Rate limit exceeded
            print(f"[RATE LIMIT] API limit reached for {package_name}. Retrying after 10s...")
            time.sleep(10)
            return fetch_npm_project(package_name)  # Retry

        elif response.status_code in [500, 502, 503, 504]:  # Temporary server errors
            print(f"[SERVER ERROR] API error {response.status_code} for {package_name}. Skipping.")
            return None

        else:
            print(f"[ERROR] Unexpected API response for {package_name}: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request timed out for {package_name}. Skipping.")
        return None

    except requests.exceptions.RequestException as e:
        print(f"[NETWORK ERROR] Could not fetch {package_name}: {str(e)}. Skipping.")
        return None


# Main function to update projects
def update_npm_projects(batch_size=60):
    """Fetch project details in batches to handle large data efficiently."""
    offset = 0
    total_fetched = 0

    while True:
        npm_packages = get_npm_packages(batch_size, offset)

        if not npm_packages:
            print("[INFO] No more NPM packages to process.")
            break  # Exit loop if no more packages are found

        print(f"[INFO] Processing batch {offset // batch_size + 1} ({len(npm_packages)} packages).")

        projects = []
        for package in npm_packages:
            print(f"[INFO] Fetching details for '{package}'.")
            project = fetch_npm_project(package)
            if project:
                projects.extend(project)

        if projects:
            print(f"[INFO] Inserting {len(projects)} projects into the database.")
            insert_projects("NPM", projects)
        else:
            print(f"[WARNING] No valid data found for this batch. Skipping.")

        total_fetched += len(npm_packages)
        offset += batch_size  # Move to the next batch

    print(f"[SUCCESS] All {total_fetched} NPM packages processed.")

# Run the script
if __name__ == "__main__":
    update_npm_projects()
