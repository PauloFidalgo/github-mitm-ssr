import requests
from bs4 import BeautifulSoup
import uuid
from flask import session as flask_session  # Flask session

# Rename the requests session to avoid conflict with flask_session
req_session = requests.Session()
req_session.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.5"
})


def save_cookies_to_file():
    """Save cookies from req_session to a file."""
    with open("cookies.txt", "w") as f:
        for cookie in req_session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")


def load_cookies_from_file():
    """Load cookies from a file into req_session."""
    try:
        with open("cookies.txt", "r") as f:
            for line in f:
                name, value = line.strip().split("=", 1)
                req_session.cookies.set(name, value)
    except FileNotFoundError:
        print("No cookies file found. Starting with a fresh session.")


def get_login_page():
    response = req_session.get("https://github.com/login")
    html = response.text

    # Use the HTML text from the response instead of the response object
    soup = BeautifulSoup(html, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})

    # Save the token value in Flask's session (assuming we're inside a Flask context)
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]

    # Modify form action if necessary
    form = soup.find("form")
    if form and form.get("action") == "/session":
        form["action"] = "/session"

    return str(soup)


def perform_login(username, password):
    # Retrieve the previously stored authenticity token from Flask's session
    token = flask_session.get("authenticity_token")
    if not token:
        return "Missing authenticity token.", "error"

    flask_session["device_id"] = str(uuid.uuid4())

    payload = {
        "authenticity_token": token,
        "login": username,
        "password": password,
        "webauthn-support": "supported",
        "webauthn-iuvpaa-support": "unsupported",
        "return_to": "",
        "allow_signup": "",
        "device_id": flask_session.get("device_id"),
    }

    post_resp = req_session.post("https://github.com/session", data=payload)
    html = post_resp.text

    save_cookies_to_file()

    cookies = req_session.cookies.get_dict()
    already_logged_in = cookies.get("logged_in", "no") == "yes"

    if already_logged_in:
        return html, "success", cookies
    elif "/sessions/two-factor" in post_resp.url or "two-factor" in html:
        return html, "2fa", cookies
    else:
        return html, "invalid", cookies


def perform_2fa():
    """
    Handles the 2FA submission using the code provided by the user.
    It requests the 2FA app page after login to fetch the form or QR code page.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-PT,pt;q=0.8,en;q=0.5,en-US;q=0.3",
        "Referer": "https://github.com/sessions/two-factor/webauthn",
        "Origin": "https://github.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Turbo-Visit": "true",
        "X-React-App-Name": "rails"
    }

    # Ensure req_session has been authenticated successfully before this call
    print("Session cookies:", req_session.cookies.get_dict())

    response = req_session.get("https://github.com/sessions/two-factor/app", headers=headers)
    save_cookies_to_file()

    # Check if we got a proper HTML response or if it's a redirect or error page
    if response.status_code != 200:
        print("Error: Received status code", response.status_code)
        return f"Error: {response.status_code}"

    # Parse the response to update the authenticity_token if needed
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]

    return response.text


def execute_2fa(app_otp: int):
    token = flask_session.get("authenticity_token")
    if not token:
        return "Missing authenticity token.", "error"

    payload = {
        "authenticity_token": token,
        "app_otp": app_otp,
        "webauthn-support": "supported",
        "webauthn-iuvpaa-support": "unsupported",
        "return_to": "",
        "allow_signup": "",
        "device_id": flask_session.get("device_id"),
    }

    post_resp = req_session.post("https://github.com/sessions/two-factor", data=payload)
    html = post_resp.text

    save_cookies_to_file()
    print("Session cookies:", req_session.cookies.get_dict())

    soup = BeautifulSoup(html, "html.parser")

    if soup.find("input", {"name": "include_email"}):
        return html, "success", req_session.cookies.get_dict()
    else:
        return html, "failure", req_session.cookies.get_dict()
