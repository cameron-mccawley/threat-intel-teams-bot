import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Load required environment variables
teams_webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
if not teams_webhook_url:
    raise ValueError("TEAMS_WEBHOOK_URL environment variable is required.")

# Load optional environment variables with defaults
sqlite_db_path = os.getenv('SQLITE_DB_PATH', 'prev_articles.db')
article_identifiers_path = os.getenv('ARTICLE_IDENTIFIERS_PATH', 'article_identifiers.txt')
poll_interval_seconds = int(os.getenv('POLL_INTERVAL_SECONDS', 180))
max_workers = int(os.getenv('MAX_WORKERS', 5))

# Your existing functionality continues here

# Example of where send_to_teams might be implemented:
def send_to_teams(message):
    if not teams_webhook_url:
        print("Error: TEAMS_WEBHOOK_URL is not set.")
        return
    # Logic to send a message to Teams using teams_webhook_url
