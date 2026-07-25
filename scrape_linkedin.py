import json
import getpass
import sys

try:
    from linkedin_api import Linkedin
except ImportError:
    print("Error: The 'linkedin-api' package is not installed.")
    print("Please install it by running: pip install linkedin-api")
    sys.exit(1)

def scrape_profile():
    print("=== LinkedIn Profile Scraper ===")
    print("Note: This script requires a valid LinkedIn account to bypass the login wall.")
    print("Warning: Use a secondary/dummy account if possible, as scraping can occasionally flag accounts.\n")
    
    email = input("Enter LinkedIn email: ")
    password = getpass.getpass("Enter LinkedIn password: ")

    try:
        print("\nAuthenticating...")
        # Authenticate with LinkedIn
        api = Linkedin(email, password)

        print("Fetching profile for 'vineeth-kaimal-373707a8'...")
        # GET the profile data
        profile = api.get_profile('vineeth-kaimal-373707a8')

        # Save to file
        output_file = 'vineeth_linkedin_profile.json'
        with open(output_file, 'w') as f:
            json.dump(profile, f, indent=4)
            
        print(f"\n✅ Successfully fetched and saved profile data to {output_file}")

    except Exception as e:
        print(f"\n❌ Failed to fetch profile. Error: {e}")
        print("This is often due to 2FA being enabled on the account, or LinkedIn temporarily blocking the login attempt.")

if __name__ == "__main__":
    scrape_profile()
