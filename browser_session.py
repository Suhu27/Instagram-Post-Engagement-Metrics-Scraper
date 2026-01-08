from instagrapi import Client

# Paste the sessionid you copied here (between the quotes)
SESSIONID = "Paste your sessionid here"

try:
    cl = Client()
    
    # Login using browser session
    cl.login_by_sessionid(SESSIONID)
    
    # Test if it works
    user = cl.account_info()
    print(f"✅ Logged in as: {user.username}")
    print(f"✅ Account ID: {user.pk}")
    
    # Save to the file your scraper expects
    cl.dump_settings("session_unified.json")
    print(f"✅ Session saved to: session_unified.json")
    print("\n🎉 SUCCESS! You can now run your scraper!")
    
except Exception as e:
    print(f"❌ Failed: {e}")
    print("\nPossible issues:")
    print("- Sessionid copied incorrectly (check for extra spaces)")
    print("- Session expired (get a fresh one from browser)")
    print("- Account has restrictions")
