from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import os
import time
import requests
import zipfile
import shutil

def inject_and_verify_github_cookies(cookies):
    options = Options()
    options.accept_insecure_certs = True  

    driver = webdriver.Firefox(options=options)

    try:
        # Navigate to GitHub and inject cookies
        driver.get("https://github.com")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        for name, value in cookies.items():
            driver.add_cookie(
                {
                    "name": name,
                    "value": value,
                    "domain": ".github.com",
                    "path": "/",
                    "secure": True,
                }
            )

        driver.refresh()
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//meta[@name='user-login']"))
        )

        user_element = driver.find_element(By.XPATH, "//meta[@name='user-login']")
        username = user_element.get_attribute("content")
        print(f"Logged in as: {username}")

        download_dir = os.path.join(os.getcwd(), "cloned_repos", f"github_repos_{username}")
        os.makedirs(download_dir, exist_ok=True)

        # Navigate to the repositories page
        driver.get(f"https://github.com/{username}?tab=repositories")

        # Wait for the repositories page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "user-repositories-list"))
        )

        # Get all repository elements
        repo_elements = driver.find_elements(By.CSS_SELECTOR, "#user-repositories-list li")
        repos = []

        # Extract repository names and URLs
        for repo in repo_elements:
            try:
                repo_name_elem = repo.find_element(By.CSS_SELECTOR, "h3 a")
                repo_name = repo_name_elem.text.strip()
                repo_url = f"https://github.com/{username}/{repo_name}"
                repos.append({"name": repo_name, "url": repo_url})
                print(f"Found repository: {repo_name}")
            except Exception as e:
                print(f"Error extracting repository info: {e}")

        # Download each repository
        for repo in repos:
            try:
                print(f"Downloading {repo['name']}...")

                # Get the cookies from Selenium for the requests session
                selenium_cookies = driver.get_cookies()
                session = requests.Session()

                # Add cookies to the session
                for cookie in selenium_cookies:
                    session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])

                # Download as ZIP (using the archive download URL)
                zip_url = f"{repo['url']}/archive/refs/heads/main.zip"
                zip_fallback_url = f"{repo['url']}/archive/refs/heads/master.zip"

                response = session.get(zip_url, stream=True)
                # If main branch doesn't exist, try master
                if response.status_code != 200:
                    response = session.get(zip_fallback_url, stream=True)

                if response.status_code == 200:
                    zip_path = os.path.join(download_dir, f"{repo['name']}.zip")
                    with open(zip_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # Extract the ZIP file
                    extract_dir = os.path.join(download_dir, repo['name'])
                    os.makedirs(extract_dir, exist_ok=True)

                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)

                    # Remove the ZIP file after extraction
                    os.remove(zip_path)
                    print(f"Successfully downloaded and extracted {repo['name']}")
                else:
                    print(f"Failed to download {repo['name']}. Status code: {response.status_code}")

                # Add a small delay to avoid rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"Error downloading {repo['name']}: {e}")

        print(f"All repositories downloaded to {download_dir}")

        # Keep the browser open for a few seconds to show success
        time.sleep(5)

    except Exception as e:
        print(f"Error during repository download: {e}")
    finally:
        driver.quit()
