from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def inject_and_verify_github_cookies(cookies):
    options = Options()
    options.accept_insecure_certs = True  

    driver = webdriver.Firefox(options=options)

    try:
        driver.get("https://github.com")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(("tag name", "body"))
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
            EC.presence_of_element_located(("xpath", "//meta[@name='user-login']"))
        )

        user_element = driver.find_element("xpath", "//meta[@name='user-login']")
    finally:
        driver.quit()