import os
import time
import requests
from dotenv import load_dotenv
from database import get_npm_packages, insert_projects, count_npm_packages

# Load environment variables
load_dotenv()

# API and Rate Limit Settings
API_KEY = os.getenv("API_KEY")
SEARCH_URL = "https://libraries.io/api/search"
MAX_REQUESTS_PER_MINUTE = 30  # API Limit
REQUEST_WINDOW = 60  # Time window in seconds
request_count = 0
window_start_time = time.time()


def print_progress(current, total, batch_number):
    """Prints the progress of fetching and inserting projects."""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 50  # Progress bar length
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    print(f"\rBatch {batch_number}: |{bar}| {percent:.2f}% ({current}/{total}) Completed", end="", flush=True)


# Query Libraries.io API for each NPM package
def fetch_npm_project(package_name):
    """Fetch package details from Libraries.io API with error handling."""
    global request_count, window_start_time
    
    # Enforce request limit
    elapsed_time = time.time() - window_start_time
    if request_count >= MAX_REQUESTS_PER_MINUTE:
        sleep_time = REQUEST_WINDOW - elapsed_time
        if sleep_time > 0:
            print(f"⏳ [INFO] Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
        request_count = 0
        window_start_time = time.time()
    
    print(f"📦 [INFO] {request_count + 1}- Fetching details for '{package_name}'.", flush=True)    

    url = f"{SEARCH_URL}?platforms=NPM&q={package_name}&api_key={API_KEY}"

    try:
        response = requests.get(url)

        if response.status_code == 200:
            request_count += 1  # Increment request count
            return response.json()

        elif response.status_code == 400:
            print(f"⚠️ [WARNING] Invalid package name: {package_name}. Skipping.", flush=True)
            return None  # Ignore invalid names

        elif response.status_code == 429:  # Rate limit exceeded
            print(f"⚠️ [RATE LIMIT] API limit reached for {package_name}. Retrying after 10s...", flush=True)
            time.sleep(10)
            return fetch_npm_project(package_name)  # Retry

        elif response.status_code in [500, 502, 503, 504]:  # Temporary server errors
            print(f"⚠️ [SERVER ERROR] API error {response.status_code} for {package_name}. Skipping.", flush=True)
            return None

        else:
            print(f"❌ [ERROR] Unexpected API response for {package_name}: {response.status_code}", flush=True)
            return None

    except requests.exceptions.Timeout:
        print(f"⚠️ [TIMEOUT] Request timed out for {package_name}. Skipping.", flush=True)
        return None

    except requests.exceptions.RequestException as e:
        print(f"❌ [NETWORK ERROR] Could not fetch {package_name}: {str(e)}. Skipping.", flush=True)
        return None


# Main function to update projects
def update_npm_projects(batch_size=MAX_REQUESTS_PER_MINUTE):
    """Fetch project details in batches to handle large data efficiently."""
    total_packages = count_npm_packages()  # Get total number of packages
    print(f"📦 [INFO] Found {total_packages} NPM packages to process.", flush=True)
    
    offset = 0
    total_fetched = 0
    batch_number = 1

    while True:
        print_progress(total_fetched, total_packages, batch_number)
        npm_packages = get_npm_packages(batch_size, offset)

        if not npm_packages:
            print("🏁 [INFO] No more NPM packages to process.", flush=True)
            break  # Exit loop if no more packages are found

        print(f"🔍 [INFO] Processing batch {offset // batch_size + 1} ({len(npm_packages)} packages).", flush=True)

        projects = []
        for package in npm_packages:
            project = fetch_npm_project(package)
            if project:
                projects.extend(project)

        if projects:
            print(f"📥 [INFO] Inserting {len(projects)} projects into the database.", flush=True)
            insert_projects("NPM", projects)
        else:
            print(f"⚠️ [WARNING] No valid data found for this batch. Skipping.", flush=True)

        total_fetched += len(npm_packages)
        offset += batch_size  # Move to the next batch
        batch_number += 1  # Increment batch count

    print(f"✅ [SUCCESS] All {total_fetched} NPM packages processed.", flush=True)

# Run the script
if __name__ == "__main__":
    update_npm_projects()
