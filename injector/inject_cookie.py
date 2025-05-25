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
import json
from bs4 import BeautifulSoup

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


def clone_repositories_headless(cookies):
    """Clone GitHub repositories using cookies without opening a browser."""
    session = requests.Session()

    # Add cookies from browser session
    for name, value in cookies.items():
        session.cookies.set(name, value, domain=".github.com", path="/")

    try:
        # Set browser-like headers
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://github.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "max-age=0",
        }

        # Get username from the profile page HTML
        profile_response = session.get("https://github.com", headers=headers)

        if profile_response.status_code != 200:
            print(
                f"Failed to load GitHub homepage. Status code: {profile_response.status_code}"
            )
            return

        # Parse the HTML to extract the username
        soup = BeautifulSoup(profile_response.text, "html.parser")
        meta_tag = soup.find("meta", {"name": "user-login"})

        if not meta_tag or not meta_tag.get("content"):
            # Try alternative method - look for the username in the page content
            username_element = soup.select_one("span.header-nav-current-user")
            if username_element:
                username = username_element.text.strip()
            else:
                print("Could not extract username from GitHub page")
                return
        else:
            username = meta_tag.get("content")

        print(f"Logged in as: {username}")

        # Create directory for repositories
        download_dir = os.path.join(
            os.getcwd(), "cloned_repos", f"github_repos_{username}"
        )
        os.makedirs(download_dir, exist_ok=True)

        # Skip API and go directly to HTML scraping
        repos = scrape_repos_from_html(session, username, headers)

        if not repos:
            print("No repositories found")
            return

        print(f"Found {len(repos)} repositories")

        # Download each repository
        for repo in repos:
            try:
                print(f"Downloading {repo['name']}...")

                # Download as ZIP (using the archive download URL)
                zip_url = f"{repo['url']}/archive/refs/heads/main.zip"
                zip_fallback_url = f"{repo['url']}/archive/refs/heads/master.zip"

                response = session.get(zip_url, stream=True, headers=headers)
                # If main branch doesn't exist, try master
                if response.status_code != 200:
                    response = session.get(zip_fallback_url, stream=True, headers=headers)

                if response.status_code == 200:
                    zip_path = os.path.join(download_dir, f"{repo['name']}.zip")
                    with open(zip_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)

                    # Extract the ZIP file
                    extract_dir = os.path.join(download_dir, repo["name"])
                    os.makedirs(extract_dir, exist_ok=True)

                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(extract_dir)

                    # Remove the ZIP file after extraction
                    os.remove(zip_path)
                    print(f"Successfully downloaded and extracted {repo['name']}")
                else:
                    print(
                        f"Failed to download {repo['name']}. Status code: {response.status_code}"
                    )

                # Add a small delay to avoid rate limiting
                time.sleep(1)

            except Exception as e:
                print(f"Error downloading {repo['name']}: {e}")

        print(f"All repositories downloaded to {download_dir}")

    except Exception as e:
        print(f"Error during repository download: {e}")


def scrape_repos_from_html(session, username, headers=None):
    """Scrape repositories from the GitHub user page."""
    repos = []
    try:
        if headers is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }

        # Navigate directly to the repositories tab
        repos_page_url = f"https://github.com/{username}?tab=repositories"
        print(f"Fetching repositories from: {repos_page_url}")

        response = session.get(repos_page_url, headers=headers)

        if response.status_code != 200:
            print(
                f"Failed to get repositories page. Status code: {response.status_code}"
            )
            # For debugging
            print(f"Response content: {response.text[:500]}...")
            return []

        # Save the HTML for debugging if needed
        repos_pages_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(repos_pages_dir, exist_ok=True)
        repos_page_path = os.path.join(repos_pages_dir, f"repos_page_{username}.html")

        with open(repos_page_path, "w", encoding="utf-8") as f:
            f.write(response.text)

        soup = BeautifulSoup(response.text, "html.parser")

        # Try different selectors to find repository elements
        repo_elements = soup.select("#user-repositories-list li")

        if not repo_elements:
            # Try alternative selector
            repo_elements = soup.select("li.public, li.private")

        if not repo_elements:
            # Another alternative
            repo_elements = soup.select("li[itemprop='owns']")

        print(f"Found {len(repo_elements)} repository elements on the page")

        for repo_element in repo_elements:
            # Try different selectors for repository name
            repo_name_elem = (
                repo_element.select_one("h3 a") or 
                repo_element.select_one("a[itemprop='name codeRepository']") or
                repo_element.select_one("a[data-hovercard-type='repository']")
            )

            if repo_name_elem:
                repo_name = repo_name_elem.text.strip()
                # Clean up the repository name (remove any extra text)
                if "/" in repo_name:
                    repo_name = repo_name.split("/")[-1].strip()

                repo_url = f"https://github.com/{username}/{repo_name}"
                repos.append({"name": repo_name, "url": repo_url})
                print(f"Found repository: {repo_name}")

        # Check for pagination
        next_page = soup.select_one("a.next_page")
        if next_page and next_page.get("href"):
            next_url = next_page.get("href")
            if not next_url.startswith("http"):
                next_url = f"https://github.com{next_url}"

            print(f"Found next page: {next_url}")
            # Get repositories from next page (recursive call)
            next_page_repos = scrape_repos_from_html(session, username, headers, next_url)
            repos.extend(next_page_repos)

    except Exception as e:
        print(f"Error scraping repositories: {e}")
        import traceback
        traceback.print_exc()

    return repos
