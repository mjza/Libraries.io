from database import create_table, insert_platforms
from services import fetch_platforms

if __name__ == "__main__":
    print("Initializing database...")
    create_table()
    
    print("Fetching platforms from API...")
    platforms = fetch_platforms()
    
    if platforms:
        print("Inserting platforms into database...")
        insert_platforms(platforms)
        print("Platforms data updated successfully.")
    else:
        print("No data inserted.")
