import time
from database import create_tables, insert_platforms, insert_projects, get_db_connection
from services import fetch_projects, fetch_platforms

MAX_REQUESTS_PER_MINUTE = 60  # Prevents exceeding API limits
REQUEST_WINDOW = 60  # Time window in seconds (1 minute)
request_count = 0  # Track API requests
window_start_time = time.time()  # Start of the request window

def set_projects():
    """Fetch and store projects per platform while handling rate limits."""
    global request_count, window_start_time
    
    platforms = get_platforms()
    if not platforms:
        print("⚠️ [WARNING] No platforms found. Please insert platforms first.")
        return

    if request_count == 0:
        window_start_time = time.time()  # Start of the request window
    
    for platform, project_count in platforms:
        print(f"\n🔍 [INFO] Fetching projects for platform: {platform} (Expecting {project_count})")
        
        per_page = 50 # designed based on the heaviness of the requests
        fetched_count = 0  # Track how many projects we have fetched
        pages = (project_count // per_page) + 1  # Calculate number of pages needed
        
        for page in range(1, pages + 1):
            # Check request limit
            elapsed_time = time.time() - window_start_time
            if request_count >= MAX_REQUESTS_PER_MINUTE:
                sleep_time = REQUEST_WINDOW - elapsed_time  # Wait to reset counter
                if sleep_time > 0:
                    print(f"⏳ [INFO] Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                request_count = 0
                window_start_time = time.time()  # Reset window

            projects = fetch_projects(platform, page, per_page)
            request_count += 1  # Increment request count

            if projects:
                print(f"📥 [INFO] Inserting {len(projects)} projects for page {page} of platform {platform}...")
                insert_projects(platform, projects) 
                fetched_count += len(projects)
            else:
                print(f"⚠️ [WARNING] No projects found for {platform} on page {page}.")
                break  # Stop if no more projects found

            # Stop early if we have reached the total count
            if fetched_count >= project_count:
                print(f"🏁 [INFO] Reached total expected projects for {platform}.")
                break

            # Stop if fewer than `per_page` projects were fetched
            if len(projects) < per_page:
                print(f"🏁 [INFO] Reached last page for {platform}. Stopping.")
                break

            # Enforce sleep to avoid hitting API limits
            elapsed_time = time.time() - window_start_time
            if request_count >= MAX_REQUESTS_PER_MINUTE:
                sleep_time = REQUEST_WINDOW - elapsed_time  # Adjust sleep dynamically
                if sleep_time > 0:
                    print(f"⏳ [INFO] Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                request_count = 0
                window_start_time = time.time()

        print(f"✅ [SUCCESS] Completed {platform}.")

def set_platforms():
    """Fetch and store platforms."""
    platforms = fetch_platforms()
    
    if platforms:
        print("📥 [INFO] Inserting platforms into database...")
        insert_platforms(platforms)
        print("✅ [SUCCESS] Platforms updated.")
    else:
        print("⚠️ [WARNING] No platforms inserted.")

def get_platforms():
    """Retrieve all platforms and their project counts from the database."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name, project_count FROM Platforms;")
            return cur.fetchall()

if __name__ == "__main__":
    print("🚀 [INFO] Initializing database...")
    create_tables()
    
    print("🔍 [INFO] Fetching platforms from API...")
    set_platforms()
    
    print("🔍 [INFO] Fetching projects from API...")
    set_projects()

    print("🎉 [SUCCESS] All platforms processed successfully.")
