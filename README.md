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
- Required Python libraries (see [Installation](#installation))

## Installation
1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/myMitm.git
    cd myMitm
    ```
2. Install dependencies:
    ```bash
    pip3 install -r requirements.txt
    ```

## Usage
1. Run the script:
    ```bash
    gunicorn -w 4 -b <LINK> app:app
    ```
2. Go to the <LINK> in which the app started

## Disclaimer
This project is for educational purposes only. Unauthorized use of this tool is strictly prohibited and may violate local, state, or federal laws. Use responsibly.

