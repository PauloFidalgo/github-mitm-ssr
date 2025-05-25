# Bypass 2FA in GitHub using MITM

## Overview
This is a project designed for educational purposes to demonstrate and understand network security concepts, vulnerabilities, and mitigation techniques. This project should only be used in controlled environments with proper authorization.

## Features
- GitHub MITM
- Credentials Storage
- Session Token Storage
- 2FA (SMS and TOPT) included

## Prerequisites
- Python
- Sqlite3
- Firefox (for cookie injection)
- Required Python libraries (see [Installation](#installation))

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/PauloFidalgo/github-mitm-ssr.git
    cd github-mitm-ssr
    ```
2. Install dependencies:
    ```bash
    pip3 install -r requirements.txt
    ```
3. Create Local Database:
    ```bash
    python3 db/database_setup.py
    ```
4. Generate a secret: 
    ```bash
    python3 -c "import secrets; print(secrets.token_hex(16))"
    ```
    Copy the secret printed in the terminal
5. Create the .env file and add the following lines:
    ```bash
    touch .env
    ```
    - APP_SECRET_KEY: GENERATED_KEY
    - INJECT_COOKIE: "TRUE" to automatically open Firefox with the session captured, "FALSE" otherwise

## Usage
1. Run the script:
    ```bash
    python3 app.py
    ```
3. Go to the Link in which the app started

## Disclaimer
This project is for educational purposes only. Unauthorized use of this tool is strictly prohibited and may violate local, state, or federal laws. Use responsibly.

