# Instagram Account Scraper

A robust, resumable tool for collecting Instagram posts, engagement metrics, and comments. Designed for academic research, this script features built-in rate limiting, session persistence, and multi-timeline support.

## Project Contents

- `Ascrap_with_limit.py`: The primary scraping script.
- `browser_session.py`: A utility script for authentication.

## Installation

```bash
pip install instagrapi
```

## Authentication

This tool uses browser session cookies for authentication, which is more secure than standard password login.

1. Log into Instagram.com in your web browser.
2. Open Developer Tools (F12), navigate to **Application** > **Cookies**.
3. Copy the value of the `sessionid` cookie.
4. Paste the value into `browser_session.py`:

```python
SESSIONID = "your_session_id_here"
```

5. Run the authentication script:

```bash
python browser_session.py
```

*This generates a `session_unified.json` file. Keep this file private.*

## Configuration

Open `Ascrap_with_limit.py` to configure your target account and scraping schedule.

### 1. Set Target Account

```python
TARGET_ACCOUNT = "target_username"  # Do not include the '@' symbol
MAX_RUNTIME_HOURS = 10            # Script stops after this duration
```

### 2. Define Date Ranges

Configure the `TIMELINES` list to specify which dates to scrape.

```python
TIMELINES = [
    {
        "name": "Dataset 1",
        "start": datetime(2024, 1, 1, tzinfo=timezone.utc),
        "end": datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "output": f"{TARGET_ACCOUNT}_2024.csv",
        "reset_cursor": False
    },
]
```

## Usage

Run the main script to begin collection:

```bash
python Ascrap_with_limit.py
```

## Resume Logic

The scraper is designed to be interrupted and resumed without data loss.

- **Cursor File:** The script saves a text file (`username_cursor.txt`) containing the ID of the last processed post.
- **Resuming:** On the next run, the script reads this file and automatically skips previously scraped content.
- **Resetting:** To restart a timeline from the beginning, set `reset_cursor: True` in your configuration or manually delete the cursor text file.

## Output Format

Data is exported to a CSV file with the following columns:

| Column | Description |
| :--- | :--- |
| `post_id` | Unique identifier for the post. |
| `date` | UTC timestamp of publication. |
| `type` | Media type (Photo, Video, Reel, Carousel). |
| `likes` | Count of likes. |
| `comments_count` | Count of comments. |
| `shares` | Count of shares. |
| `views` | Count of views (video content only). |
| `engagement_rate` | Interaction rate relative to views (video only). |
| `caption_raw` | Full caption text. |
| `comments_json` | JSON string containing top comments (can change number required). |
| `url` | Permanent link to the post. |


