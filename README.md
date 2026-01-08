Instagram Account Scraper (Resumable, Time-Limited)
A Python tool for collecting Instagram posts, engagement metrics, and comments from public accounts. Designed for research use with resumable sessions and built-in rate limiting.

📂 Repository Contents
Ascrap_with_limit.py: Main scraper script

browser_session.py: Authentication helper

🚀 Quick Start
1. Installation
bash
pip install instagrapi
2. Authentication
The scraper uses your browser session instead of a password login for better security.

Log into Instagram in your web browser.

Open Developer Tools (F12) → Application/Storage → Cookies.

Copy the value of the sessionid cookie.

Paste it into browser_session.py:

python
SESSIONID = "paste_your_sessionid_here"
Run the script to generate your session file:

bash
python browser_session.py
Output: session_unified.json (Keep this file private!)

3. Configuration
Open Ascrap_with_limit.py and set your target:

python
TARGET_ACCOUNT = "username"       # Target account (no @ symbol)
MAX_RUNTIME_HOURS = 10            # Stop after X hours to avoid bans

# Define date ranges to scrape
TIMELINES = [
    {
        "name": "2024 Data",
        "start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "end": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "output": f"{TARGET_ACCOUNT}_2024.csv",
        "reset_cursor": False  # See below for explanation
    },
]
4. Run Scraper
bash
python Ascrap_with_limit.py
🧠 How Resuming Works (Cursor Logic)
This scraper is designed to handle interruptions (network issues, rate limits, or time limits) without losing progress.

The "Cursor": Instagram's API uses a cursor (a unique ID) to mark your position in a feed. It points to the "next page" of posts.

Saving State: As the scraper moves backward in time through the feed, it saves this cursor to a text file (username_cursor.txt).

What reset_cursor Does:
False (Default / Resume Mode):
The script checks for a saved cursor file.

If found: It skips all previously scraped posts and resumes exactly where it left off.

If not found: It starts scraping from the most recent post.

Use this for large scraping jobs that might take multiple sessions.

True (Restart Mode):
The script deletes any existing cursor file before starting.

It effectively forces the scraper to start fresh from the most recent post, re-scanning everything.

Use this if you want to re-scrape an account from scratch or if the cursor file got corrupted.

📊 CSV Output
Data is saved to the filename specified in your timeline config.

Column	Description
post_id	Unique ID of the post
date	Date posted (UTC)
type	Photo, Video, Reel, or Carousel
likes	Total like count
comments_count	Total comment count
shares	Share count
views	View count (for videos)
engagement_rate	(likes + comments + shares) / views (videos only)
caption_raw	Full caption text
comments_json	JSON list of first 40 comments
url	Direct link to post

Important Notes
Rate Limits: The script automatically pauses for 3-6 minutes after every 30 requests to protect your account.

Public Accounts Only: The target account must be public or followed by your authenticated account.

Ethics: This tool is for educational and research purposes. Respect Instagram's terms of service.
