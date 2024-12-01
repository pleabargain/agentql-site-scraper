"""
My Target Site Portal Login Script
This script automates the login process for the target site portal using Playwright and AgentQL.
"""

import logging
from datetime import datetime
import agentql
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    filename=f'login_my_target_site_{datetime.now().strftime("%Y%m%d")}.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def read_default_credentials(env_path: str = '.env') -> tuple:
    """
    Reads default credentials from environment variables.

    Args:
        env_path (str): Path to the .env file. Defaults to '.env'

    Returns:
        tuple: Contains URL, username, and password
    """
    # Load environment variables from .env file
    if not os.path.exists(env_path):
        logging.warning(f"{env_path} file not found. Creating template...")
        with open(env_path, 'w') as f:
            f.write("TARGET_URL=\nTARGET_USERNAME=\nTARGET_PASSWORD=")
        logging.info(f"Created {env_path} template. Please fill in your credentials.")
        return "", "", ""

    load_dotenv(env_path)
    
    url = os.getenv('TARGET_URL')
    username = os.getenv('TARGET_USERNAME')
    password = os.getenv('TARGET_PASSWORD')
    
    return url, username, password

def get_user_credentials() -> tuple:
    """
    Gets credentials from .env file or prompts user for input.

    Returns:
        tuple: Contains URL, username, and password
    """
    url, username, password = read_default_credentials()
    
    if not all([url, username, password]):
        print("\nCredentials not found in .env file.")
        print("Please enter your credentials or update the .env file with:")
        print("TARGET_URL=your_url")
        print("TARGET_USERNAME=your_username")
        print("TARGET_PASSWORD=your_password\n")
        
        # Add default URL if none provided
        default_url = "https://auth.reedexpo.com/secure/Account/Login"
        url = input(f"Enter URL (press Enter for default: {default_url}): ").strip() if not url else url
        url = url if url else default_url
        
        username = input("Enter Login ID: ").strip() if not username else username
        password = input("Enter Password: ").strip() if not password else password
    else:
        print("\nCredentials loaded from .env file.")
        print(f"URL: {url}")
        print(f"Username: {username}")
        print("Password: ********")
        
        use_env = input("\nUse these credentials? (Y/n): ").strip().lower()
        if use_env != 'y' and use_env != '':
            default_url = "https://auth.reedexpo.com/secure/Account/Login"
            url = input(f"Enter URL (press Enter for default: {default_url}): ").strip()
            url = url if url else default_url
            username = input("Enter Login ID: ").strip()
            password = input("Enter Password: ").strip()

    return url, username, password

def login_to_portal(url: str, username: str, password: str) -> None:
    """
    Performs login operation on the target site portal.

    Args:
        url (str): Portal URL
        username (str): Login username
        password (str): Login password
    """

    # Updated Exhibitor Hub queries with XPath
    EXHIBITOR_HUB_QUERY = """
    {
        submit_btn "a[href='/exhibitor/challenge'][class='_button_1p0fh_8 _--primary_1p0fh_136 _--theme-default_1p0fh_80']"
        submit_btn_text "Log in to the Exhibitor Hub"
    }
    """


    # Updated login form query with exact selectors based on provided JSON details
    LOGIN_FORM_QUERY = """
    {
        body {
            username_field "input#username[name='Username'][class='form-control'][placeholder='Username']"
            password_field "input#password[name='Password'][class='form-control'][type='password'][placeholder='Password']"
            login_button "button#submit[data-dtm='policebox_login'][class='btn btn-primary login-button']"
        }
    }
    """

    # Query for handling popup
    POPUP_QUERY = """
    {
        popup_form {
            close_btn
        }
    }
    """



    try:
        logging.info("Initializing Playwright")
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = agentql.wrap(context.new_page())
        
        logging.info(f"Navigating directly to login page: {url}")
        page.goto(url)
        
        # Wait for page load
        logging.info("Waiting for page load")
        page.wait_for_load_state('networkidle')
        
        # Wait for form elements
        logging.info("Waiting for login form elements")
        page.wait_for_selector("#username", state="visible", timeout=60000)
        page.wait_for_selector("#password", state="visible", timeout=60000)
        logging.info("Login form elements visible")

        logging.info("Attempting to interact with login form")
        try:
            response = page.query_elements(LOGIN_FORM_QUERY)
            logging.info("Login form elements found")
            
            logging.info(f"Filling username: {username}")
            response.username_field.fill(username)
            
            logging.info("Filling password")
            response.password_field.fill(password)
            
            logging.info("Clicking submit button")
            response.body.login_button.click()
            
        except Exception as form_error:
            logging.warning(f"AgentQL query failed for login form: {str(form_error)}")
            logging.info("Attempting fallback with direct selectors")
            
            logging.info("Filling username field")
            page.locator("#username[name='Username']").fill(username)
            
            logging.info("Filling password field")
            page.locator("#password[name='Password']").fill(password)
            
            logging.info("Clicking submit button")
            page.locator("button#submit[data-dtm='policebox_login']").click()

        # Wait for navigation after login
        logging.info("Waiting for login submission to complete")
        page.wait_for_load_state('networkidle')
        
        logging.info("Login process completed")
        
        # Handle popup if present
        try:
            logging.info("Checking for popup")
            popup_response = page.query_elements(POPUP_QUERY)
            if popup_response and popup_response.popup_form.close_btn:
                logging.info("Popup detected, attempting to close")
                popup_response.popup_form.close_btn.click()
                logging.info("Popup closed successfully")
        except Exception as popup_error:
            logging.warning(f"No popup found or error handling popup: {str(popup_error)}")

        # Try to click Exhibitor Hub button
        try:
            logging.info("Looking for Exhibitor Hub login button")
            hub_response = page.query_elements(EXHIBITOR_HUB_QUERY)
            if hub_response and hub_response.submit_btn:
                logging.info("Exhibitor Hub button found, clicking...")
                hub_response.submit_btn.click()
                logging.info("Exhibitor Hub button clicked successfully")
            else:
                logging.info("Trying to find button by text...")
                page.get_by_text(hub_response.submit_btn_text).click()
                logging.info("Exhibitor Hub button clicked successfully using text selector")
        except Exception as hub_error:
            logging.error(f"Failed to find Exhibitor Hub button: {str(hub_error)}")

        # Navigate to search buyers page
        logging.info("Navigating to search buyers page")
        page.goto("https://portal.my_target_site.com/exhibitor/search-buyers")
        page.wait_for_load_state('networkidle')
        logging.info("Successfully navigated to search buyers page")

        # Keep the browser open indefinitely
        logging.info("Browser will remain open. Press Ctrl+C to exit.")
        while True:
            page.wait_for_timeout(1000)  # Check every second
            
    except Exception as e:
        logging.error(f"Error during login process: {str(e)}")
        logging.error(f"Error details: {str(e.__class__.__name__)}")
        
        # Keep browser open even if there's an error
        logging.info("Browser will remain open despite error. Press Ctrl+C to exit.")
        while True:
            page.wait_for_timeout(1000)
            
    finally:
        logging.info("Script execution completed")

def main():
    """
    Main function to execute the login process.
    """
    try:
        print("\nMy Target Site Portal Login")
        print("===========================")
        logging.info("Starting login process")
        
        url, username, password = get_user_credentials()
        logging.info("Credentials obtained")
        
        if not all([url, username, password]):
            logging.error("Missing required credentials")
            print("Error: All credentials are required")
            return

        print("\nAttempting login...")
        login_to_portal(url, username, password)
        
    except Exception as e:
        logging.error(f"Main execution failed: {str(e)}")
        print(f"\nError: {str(e)}")
    finally:
        logging.info("Main function execution completed")

if __name__ == "__main__":
    main()