import json

# Load the exported cookies
with open("twitter_cookies.json", "r") as f:
    browser_cookies = json.load(f)

# Convert into {name: value} format
twikit_cookies = {cookie["name"]: cookie["value"] for cookie in browser_cookies}

# Save in the format Twikit expects
with open("twitter_cookies_twikit.json", "w") as f:
    json.dump(twikit_cookies, f, indent=2)

print("Converted cookies saved to twitter_cookies_twikit.json")