import os
import time
import requests
from dotenv import load_dotenv
from database import get_npm_packages, insert_projects, count_npm_packages
import itertools

# Load environment variables
load_dotenv()

# API and Rate Limit Settings
API_KEYS = os.getenv("API_KEYS").split(",")
SEARCH_URL = "https://libraries.io/api/search"
DEFAULT_MAX_REQUESTS_PER_MINUTE = 60  # Default limit unless otherwise known
REQUEST_WINDOW = 60  # Time window in seconds

# Track request counts, rate limits, and start times for each API key
api_keys_status = {
    key.strip(): {
        "request_count": 0,
        "window_start_time": time.time(),
        "max_requests_per_minute": DEFAULT_MAX_REQUESTS_PER_MINUTE
    } for key in API_KEYS
}
api_key_cycle = itertools.cycle(api_keys_status.keys())
current_api_key = next(api_key_cycle)


def switch_api_key():
    global current_api_key
    for _ in range(len(api_keys_status)):
        candidate_key = next(api_key_cycle)
        status = api_keys_status[candidate_key]
        elapsed_time = time.time() - status["window_start_time"]

        if status["request_count"] < status["max_requests_per_minute"]:
            current_api_key = candidate_key
            return True  # Successfully switched to a valid API key
        elif elapsed_time >= REQUEST_WINDOW:
            # Reset the window for this key if the time window has passed
            api_keys_status[candidate_key]["request_count"] = 0
            api_keys_status[candidate_key]["window_start_time"] = time.time()
            current_api_key = candidate_key
            return True  # Successfully reset and switched

    return False  # No available API key found


def wait_for_rate_limit_reset():
    """Sleep until the soonest API key resets its rate limit window."""
    reset_times = {}
    current_time = time.time()

    # Calculate remaining time for each API key
    for key, status in api_keys_status.items():
        elapsed_time = current_time - status["window_start_time"]
        remaining_time = REQUEST_WINDOW - elapsed_time
        if remaining_time > 0:
            reset_times[key] = remaining_time

    if not reset_times:
        return  # No API key needs resetting; all are ready to use

    # Find the API key with the soonest reset time
    key_to_reset = min(reset_times, key=reset_times.get)
    sleep_time = reset_times[key_to_reset]

    print(f"⏳ [INFO] All API keys exhausted. Sleeping for {sleep_time:.2f} seconds for key: {key_to_reset}...")
    time.sleep(sleep_time)

    # Reset only the API key with the shortest time
    api_keys_status[key_to_reset]["request_count"] = 0
    api_keys_status[key_to_reset]["window_start_time"] = time.time()

    # Adjust the window_start_time for other API keys
    for key, status in api_keys_status.items():
        if key != key_to_reset:
            # Adjust the window start time relative to the sleep time
            status["window_start_time"] += sleep_time


def update_rate_limit(api_key):
    """Reduce the max request count for the API key dynamically if rate limit is hit early."""
    status = api_keys_status[api_key]
    elapsed_time = time.time() - status["window_start_time"]
    if elapsed_time < REQUEST_WINDOW:
        # Update max_requests_per_minute dynamically
        new_limit = status["request_count"]
        print(f"⚠️ [UPDATE] Adjusting max requests for API key {api_key} to {new_limit} per minute.")
        api_keys_status[api_key]["max_requests_per_minute"] = new_limit


def print_progress(current, total, batch_number):
    """Prints the progress of fetching and inserting projects."""
    percent = (current / total) * 100 if total > 0 else 0
    bar_length = 50
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    print(f"\rBatch {batch_number}: |{bar}| {percent:.2f}% ({current}/{total}) Completed", end="", flush=True)


def fetch_npm_project(package_name):
    """Fetch package details from Libraries.io API with proper rate-limit handling."""
    global current_api_key

    while True:
        status = api_keys_status[current_api_key]
        elapsed_time = time.time() - status["window_start_time"]

        if status["request_count"] >= status["max_requests_per_minute"]:
            if elapsed_time >= REQUEST_WINDOW:
                # Reset count if time window has passed
                status["request_count"] = 0
                status["window_start_time"] = time.time()
            else:
                if not switch_api_key():
                    wait_for_rate_limit_reset()

        print(f"📦 [INFO] Fetching details for '{package_name}' using API key: {current_api_key}", flush=True)

        url = f"{SEARCH_URL}?platforms=NPM&q={package_name}&api_key={current_api_key}"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                status["request_count"] += 1
                return response.json()

            elif response.status_code == 400:
                print(f"⚠️ [WARNING] Invalid package name: {package_name}. Skipping.", flush=True)
                return None

            elif response.status_code == 429:
                print(f"⚠️ [RATE LIMIT] API limit reached early for key {current_api_key}.", flush=True)
                update_rate_limit(current_api_key)
                if not switch_api_key():
                    wait_for_rate_limit_reset()

            elif response.status_code in [500, 502, 503, 504]:
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
def update_npm_projects(batch_size=DEFAULT_MAX_REQUESTS_PER_MINUTE):
    """Fetch project details in batches while handling rate limits."""
    total_packages = count_npm_packages()
    print(f"📦 [INFO] Found {total_packages} NPM packages to process.", flush=True)

    offset = 0
    total_fetched = 0
    batch_number = 1

    while True:
        print_progress(total_fetched, total_packages, batch_number)
        npm_packages = get_npm_packages(batch_size, offset)

        if not npm_packages:
            print("🏁 [INFO] No more NPM packages to process.", flush=True)
            break

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
        offset += batch_size
        batch_number += 1

    print(f"✅ [SUCCESS] All {total_fetched} NPM packages processed.", flush=True)


# Run the script
if __name__ == "__main__":
    update_npm_projects()
