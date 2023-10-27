import hashlib
import requests
import os
import json
import time
from bs4 import BeautifulSoup
YOUR_DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/your_url"

MAX_RETRY_ATTEMPTS = 3  # Maximum number of retry attempts
from bs4 import BeautifulSoup


# Enable or disable ad filtration
FILTER_ADS = True

def filter_ads(webpage_content):
    soup = BeautifulSoup(webpage_content, "html.parser")
    # Identify and remove ad elements using their HTML structure or classes
    for ad in soup.find_all("div", class_="ad-container"):
        ad.decompose()
    return str(soup)

def get_webpage_hash(url):
    attempts = 0
    while attempts < MAX_RETRY_ATTEMPTS:
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            webpage_content = response.text
            webpage_hash = hashlib.sha256(webpage_content.encode()).hexdigest()
            return webpage_hash
        except requests.exceptions.RequestException as e:
            print(f"Error fetching webpage: {e}")
            attempts += 1
            if attempts < MAX_RETRY_ATTEMPTS:
                print(f"Retrying... (Attempt {attempts}/{MAX_RETRY_ATTEMPTS})")
                time.sleep(5)  # Wait for 5 seconds before retrying
    print("Max retry attempts reached. Giving up.")
    return None

def send_discord_notification(message, webhook_url):
    data = {"content": message}
    requests.post(webhook_url, json=data)

def main():
    # Define a list of websites
    websites = [
        "http://www.example1.org/",
	"http://www.example2.org/",
        # Add more websites here
    ]

    # Load existing hashes from a JSON file or initialize an empty dictionary
    hash_file_path = "./website_hashes.json"
    if os.path.exists(hash_file_path):
        with open(hash_file_path, "r") as f:
            website_hashes = json.load(f)
    else:
        website_hashes = {}

    for website in websites:
        time.sleep(5)
        YOUR_WEBPAGE_URL = website

        # Read the previous hash from the dictionary
        old_hash = website_hashes.get(YOUR_WEBPAGE_URL)

        # Get the current hash
        new_hash = get_webpage_hash(YOUR_WEBPAGE_URL)

        # Compare and notify
        if old_hash is not None and old_hash != new_hash:
            send_discord_notification(f"Webpage has changed: {YOUR_WEBPAGE_URL}", YOUR_DISCORD_WEBHOOK_URL)

        # Update the hash in the dictionary
        website_hashes[website] = new_hash

    # Save the updated dictionary to the JSON file
    with open(hash_file_path, "w") as f:
        json.dump(website_hashes, f, indent=4)

if __name__ == "__main__":
    main()
