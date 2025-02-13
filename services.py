import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("API_KEY")
BASE_URL = "https://libraries.io/api/"
DEFAULT_SLEEP_TIME = 15  # Sleep 15 seconds between each request to prevent hitting the rate limit
MAX_RETRIES = 4 # Retry up to 4 times

# Fetch platform data from API
def fetch_platforms():
    api_url = f"{BASE_URL}platforms?api_key={API_KEY}"
    
    retries = 0
    while retries < MAX_RETRIES:  
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            wait_time =  (2 ** retries) * DEFAULT_SLEEP_TIME  # Exponential backoff
            print(f"⚠️ [RATE LIMIT] Reached API limit. Retrying in {wait_time}s...")
            time.sleep(DEFAULT_SLEEP_TIME)
            retries += 1
        else:
            print(f"❌ [ERROR] Failed to fetch platforms: {response.status_code}, {response.text}")
            return []

    print("🚨 [FATAL] Maximum retries reached. Could not fetch platforms.")
    return []

# Fetch project data from API
def fetch_projects(platform, page, per_page):
    """Fetch projects for a specific platform, handling API rate limits."""
    url = f"{BASE_URL}search?platforms={platform}&sort=created_at&page={page}&per_page={per_page}&q=&api_key={API_KEY}"

    retries = 0
    while retries < MAX_RETRIES:
        wait_time = (2 ** retries) * DEFAULT_SLEEP_TIME  # Exponential backoff
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:                
                print(f"⚠️ [RATE LIMIT] Reached API limit for {platform} on page {page}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                retries += 1
            else:
                print(f"❌ [ERROR] API request failed for {platform}, page {page}: {response.status_code}, {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ [NETWORK ERROR] Fetching {platform} (Page {page}) failed: {str(e)}")
            time.sleep(wait_time)  # Wait before retrying
            retries += 1

    print(f"🚨 [FATAL] Maximum retries reached for {platform} (Page {page}). Skipping.")
    return None
