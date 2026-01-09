import time
import random
import os
import json
import csv
import sys
from datetime import datetime, timedelta, timezone
from instagrapi import Client



# ================= CONFIGURATION ================= 
SESSION_FILE = "session_unified.json"
TARGET_ACCOUNT = "username" 
CURSOR_FILE = f"{TARGET_ACCOUNT}_cursor.txt"



# ===== TIME LIMIT =====
MAX_RUNTIME_HOURS = 10

 

# ===== TIMELINE CONFIG =====
TIMELINES = [
    # ============ CHANGE 1: Reordered timelines, Timeline 3 commented out ============
     {
         "name": "Timeline 3 (Jan-May 2024)",
         "start": datetime(2024, 1, 1, tzinfo=timezone.utc),
         "end": datetime(2024, 5, 11, 23, 59, 59, tzinfo=timezone.utc),
         "output": f"{TARGET_ACCOUNT}_JanMay2024.csv",
         "reset_cursor": False
     },
    {
        "name": "Timeline 2 (Oct-Dec 2023)",
        "start": datetime(2023, 10, 1, tzinfo=timezone.utc),
        "end": datetime(2023, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        "output": f"{TARGET_ACCOUNT}_OctDec2023.csv",
        "reset_cursor": False 
    },
    {
        "name": "Timeline 1 (Jun-Sep 2023)",
        "start": datetime(2023, 6, 1, tzinfo=timezone.utc),
        "end": datetime(2023, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
        "output": f"{TARGET_ACCOUNT}_JunSep2023.csv",
        "reset_cursor": False 
    }
    # ============ END CHANGE 1 ============
]



DEBUG_MODE = False



# ===== CONSERVATIVE SETTINGS =====
BATCH_SIZE = 33            
MAX_COMMENTS_PER_POST = 40
REQUESTS_BEFORE_PAUSE = 30
PAUSE_DURATION_RANGE = (180, 360)
SCROLL_DELAY = (3, 6)
SCRAPE_DELAY = (4, 7)



GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"



# ================= HELPERS =================



def print_status(message, color=None):
    timestamp = datetime.now().strftime("%H:%M:%S")
    color_code = ""
    if color == "green": color_code = GREEN
    elif color == "yellow": color_code = YELLOW
    elif color == "red": color_code = RED
    elif color == "cyan": color_code = CYAN
    print(f"{color_code}[{timestamp}] {message}{RESET}")



def save_cursor(cursor):
    with open(CURSOR_FILE, "w") as f:
        f.write(cursor)



def load_cursor():
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, "r") as f:
            return f.read().strip()
    return None



def load_existing_ids(filename):
    if not os.path.exists(filename): return set()
    existing = set()
    try:
        with open(filename, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'post_id' in row: existing.add(row['post_id'])
    except: pass
    return existing



def append_to_csv(data_dict, filename):
    file_exists = os.path.isfile(filename)
    fieldnames = [
        'post_id', 'date', 'type', 'likes', 'comments_count', 'shares', 'views', 
        'engagement_rate', 'caption_raw', 'comments_json', 'url'
    ]
    with open(filename, 'a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists: writer.writeheader()
        writer.writerow(data_dict)



api_request_count = 0



def check_rate_limits(cl=None):
    global api_request_count
    api_request_count += 1
    
    if api_request_count > 0 and api_request_count % REQUESTS_BEFORE_PAUSE == 0:
        sleep_time = random.randint(*PAUSE_DURATION_RANGE)
        print_status(f"☕ SAFETY PAUSE: Cooling down for {sleep_time}s...", "yellow")
        
        if cl:
            try:
                cl.account_info()
                print_status("    Health Check: OK", "green")
            except Exception as e:
                print_status(f"    ACCOUNT FLAGGED: {e}", "red")
                raise e 
        
        time.sleep(sleep_time)
        print_status("▶ Resuming operations...", "green")



def get_raw_comments_safe(cl, media_id, amount=40):
    comments = []
    max_id = None
    
    try:
        while len(comments) < amount:
            check_rate_limits(cl)
            params = {'max_id': max_id} if max_id else {}
            result = cl.private_request(f"media/{media_id}/comments/", params=params)
            
            raw_items = result.get('comments', [])
            for item in raw_items:
                if len(comments) >= amount: break
                user = item.get('user', {}).get('username', 'Unknown')
                text = item.get('text', '').replace('\n', ' ')
                comments.append({"user": user, "text": text})
            
            max_id = result.get('next_max_id')
            if not max_id: break
            time.sleep(random.uniform(2, 4))
            
    except Exception as e:
        if "429" in str(e): raise e 
        print(f"       Comment fetch warning: {str(e)[:50]}...")
        
    return comments



# ================= CORE SCRAPER =================



def process_resumable(cl, timeline_config, global_start_time):
    START_DATE = timeline_config['start']
    END_DATE = timeline_config['end']
    OUTPUT_FILE = timeline_config['output']
    
    if timeline_config['reset_cursor'] and os.path.exists(CURSOR_FILE):
        os.remove(CURSOR_FILE)
        print_status(f"🗑️ Cleared cursor for {timeline_config['name']}", "yellow")
    
    try:
        user_id = cl.user_id_from_username(TARGET_ACCOUNT)
    except Exception as e:
        print_status(f" Failed to get User ID: {e}", "red")
        return "error"



    next_max_id = load_cursor()
    processed_ids = load_existing_ids(OUTPUT_FILE)
    
    print("\n" + "╔" + "═"*60 + "╗")
    print(f"║  ULTIMATE SCRAPER: {TARGET_ACCOUNT}")
    print(f"║  TASK: {timeline_config['name']}")
    print(f"║  FILE: {OUTPUT_FILE}")
    if next_max_id:
        print(f"║  RESUMING from cursor: {next_max_id[:30]}...")
    else:
        print(f"║ 🚀 No cursor found - starting fresh")
    print("╚" + "═"*60 + "╝\n")



    posts_collected = 0
    consecutive_skips = 0
    start_time = time.time()
    batch_count = 0
    
    try:
        while True:
            elapsed_total = time.time() - global_start_time
            if elapsed_total > (MAX_RUNTIME_HOURS * 3600):
                print("\n" + "⏰"*30)
                print_status(f" TIME LIMIT REACHED ({MAX_RUNTIME_HOURS} hours)", "yellow")
                print(f"   Cursor saved. Posts this session: {posts_collected}")
                print(f"   API Requests: {api_request_count}")
                print(f"   Run same script tomorrow to resume!")
                print("⏰"*30)
                return "time_limit"
            
            try:
                check_rate_limits(cl)
                
                params = {"count": BATCH_SIZE, "exclude_comment": True}
                if next_max_id: params["max_id"] = next_max_id
                
                response = cl.private_request(f"feed/user/{user_id}/", params=params)
                items = response.get('items', [])
                
                # ============ CHANGE 2: Store next_max_id but DON'T save yet ============
                next_max_id = response.get('next_max_id')
                # REMOVED: if next_max_id: save_cursor(next_max_id)
                # ============ END CHANGE 2 ============
                
                if not items:
                    print_status("End of feed reached.")
                    break



                batch_dates = []
                for item in items:
                    ts = item.get('taken_at')
                    if ts: batch_dates.append(datetime.fromtimestamp(ts, timezone.utc))
                
                if not batch_dates: continue
                
                batch_newest = max(batch_dates) 
                batch_oldest = min(batch_dates)
                
                if batch_oldest > END_DATE:
                    consecutive_skips += 1
                    
                    if consecutive_skips % 50 == 0:
                        elapsed_hrs = elapsed_total / 3600
                        remaining_hrs = MAX_RUNTIME_HOURS - elapsed_hrs
                        print(f"\r Skip #{consecutive_skips} | Time left: {remaining_hrs:.1f}h | At: {batch_oldest.date()}| API: {api_request_count}", end="", flush=True)
                    else:
                        print(f"\r Fast Fwd #{consecutive_skips} (Oldest: {batch_oldest.date()})...| API: {api_request_count}...", end="", flush=True)
                    
                    if consecutive_skips > 0 and consecutive_skips % 60 == 0:
                        print()
                        print_status(f" Extra cooldown at skip #{consecutive_skips}. Pausing 30s...", "yellow")
                        time.sleep(30)
                    
                    if not next_max_id: break
                    
                    # ============ CHANGE 3: Save cursor when skipping forward ============
                    if next_max_id:
                        save_cursor(next_max_id)
                    # ============ END CHANGE 3 ============
                    
                    delay = random.uniform(*SCROLL_DELAY)
                    time.sleep(delay)
                    continue



                if consecutive_skips > 0: print("")
                consecutive_skips = 0



                # ============ CHANGE 4: Check exit BEFORE saving cursor ============
                if batch_newest < (START_DATE - timedelta(days=7)):
                    print_status(f" FINISHED TIMELINE: Reached {batch_newest.date()}.", "green")
                    break  # Exit WITHOUT saving this cursor
                # ============ END CHANGE 4 ============



                batch_count += 1
                print("\n" + "─"*60)
                print_status(f" BATCH {batch_count}: {batch_newest.date()} → {batch_oldest.date()}", "cyan")
                print("─"*60)
                
                for item in items:
                    try:
                        ts = item.get('taken_at')
                        if not ts: continue 
                        
                        post_date = datetime.fromtimestamp(ts, timezone.utc)
                        pk = str(item.get('pk'))
                        
                        if pk in processed_ids: continue 
                        if post_date > END_DATE: continue 
                        if post_date < START_DATE: continue 



                        posts_collected += 1
                        
                        code = item.get('code')
                        media_type_code = item.get('media_type')
                        media_type = "Photo"
                        if media_type_code == 2:
                            media_type = "Video"
                            if item.get('clips_metadata'): media_type = "Reel"
                        elif media_type_code == 8: media_type = "Carousel"



                        print(f"   ✓ [Post {posts_collected}] {post_date.date()} ({media_type})", end=" | ")



                        likes = item.get('like_count', 0)
                        comments_count = item.get('comment_count', 0)
                        views = 0
                        if media_type in ["Video", "Reel"]:
                            views = item.get('play_count', 0)
                            if views == 0: views = item.get('view_count', 0)
                        
                        shares = item.get('reshare_count', 0)
                        if shares == 0:
                            clips_meta = item.get('clips_metadata') or {}
                            shares = clips_meta.get('reshare_count', 0)



                        raw_cap = item.get('caption', {}).get('text', "") if item.get('caption') else ""
                        caption_raw = raw_cap.replace('\n', ' ').replace('\r', ' ')



                        comments_data = [] 
                        if comments_count > 0:
                            fetch_amount = min(comments_count, MAX_COMMENTS_PER_POST)
                            print(f"Get {fetch_amount} Comms...", end=" ", flush=True)
                            comments_data = get_raw_comments_safe(cl, pk, amount=MAX_COMMENTS_PER_POST)



                        er = None
                        if media_type in ["Video", "Reel"] and views > 0:
                            er = round(((likes + shares + comments_count) / views) * 100, 2)



                        row = {
                            'post_id': str(pk), 'date': post_date, 'type': media_type,
                            'likes': likes, 'comments_count': comments_count, 'shares': shares,
                            'views': views, 'engagement_rate': er,
                            'caption_raw': caption_raw,
                            'comments_json': json.dumps(comments_data, ensure_ascii=False),
                            'url': f"https://www.instagram.com/p/{code}/"
                        }
                        
                        append_to_csv(row, OUTPUT_FILE)
                        processed_ids.add(pk)
                        print("Saved.")
                        
                        if posts_collected % 10 == 0:
                            elapsed = time.time() - start_time
                            rate = posts_collected / (elapsed / 60) if elapsed > 0 else 0
                            print_status(f"⏱️  Speed: {rate:.1f} posts/min | Elapsed: {elapsed/60:.1f} min | API: {api_request_count}", "yellow")
                        
                        time.sleep(random.uniform(*SCRAPE_DELAY))



                    except Exception as e:
                        print(f"\n   ⚠ Bad Post Data (Skipped): {e}")
                        continue 



                # ============ CHANGE 5: Save cursor AFTER processing batch ============
                if next_max_id:
                    save_cursor(next_max_id)
                # ============ END CHANGE 5 ============
                
                if not next_max_id: break
                time.sleep(2)



            except Exception as e:
                print_status(f"API Error: {e}", "red")
                if "429" in str(e):
                    print_status("Sleeping 5m (Rate Limit)...", "red")
                    time.sleep(300)
                elif "feedback_required" in str(e):
                    print_status(" ACTION BLOCK! Stopping.", "red")
                    return "blocked"
                else:
                    time.sleep(60)
    
    except KeyboardInterrupt:
        print("\n" + "!"*60)
        print_status(" INTERRUPTED BY USER", "yellow")
        return "interrupted"



    print("\n" + "="*60)
    print(f"   COMPLETED: {timeline_config['name']}")
    print(f"   Posts: {posts_collected}")
    print(f"   API Requests: {api_request_count}")
    print(f"   File:  {OUTPUT_FILE}")
    print("="*60)
    return "completed"



# ================= MAIN =================



if __name__ == "__main__":
    if not os.path.exists(SESSION_FILE):
        print("Please run generate_session.py first.")
        exit()
    try:
        cl = Client()
        cl.load_settings(SESSION_FILE)
        cl.login_by_sessionid(cl.sessionid)
        
        print_status(" STARTING MULTI-TIMELINE SCRAPE...", "cyan")
        print(f" Time limit: {MAX_RUNTIME_HOURS} hours\n")
        
        global_start_time = time.time()
        
        for i, task in enumerate(TIMELINES):
            result = process_resumable(cl, task, global_start_time)
            
            if result == "time_limit":
                print("\n Stopped - time limit. Resume tomorrow!")
                break
            elif result == "blocked":
                print("\n Stopped - action block. Wait 24h!")
                break
            elif result == "interrupted":
                print("\n Stopped by user.")
                break
            elif result == "completed":
                if i < len(TIMELINES) - 1:
                    elapsed = time.time() - global_start_time
                    if elapsed < (MAX_RUNTIME_HOURS * 3600 - 300):
                        print_status(f" Finished {task['name']}. Cooling 2 mins...", "green")
                        time.sleep(120)
        
        print("\n Session complete.")
        
    except Exception as e: print(f"Fatal: {e}")
