#!/bin/bash
USERNAME=$1
PASSWORD=$2
COOKIE_FILE="github_cookies.txt"
LOGIN_PAGE_HTML="github_login.html"
RESPONSE_HTML="response.html"

# Extract authenticity token from the saved login page
AUTH_TOKEN=$(grep 'name="authenticity_token"' "$LOGIN_PAGE_HTML" | sed -n 's/.*value="\([^"]*\)".*/\1/p' | head -1)
TIMESTAMP=$(date +%s%N | cut -b1-13)
DEVICE_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')

# Submit the login form
curl -s -L -b "$COOKIE_FILE" -c "$COOKIE_FILE" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Origin: https://github.com" \
  -H "Referer: https://github.com/login" \
  --data-urlencode "authenticity_token=$AUTH_TOKEN" \
  --data-urlencode "login=$USERNAME" \
  --data-urlencode "password=$PASSWORD" \
  --data-urlencode "timestamp=$TIMESTAMP" \
  --data-urlencode "webauthn-support=supported" \
  --data-urlencode "webauthn-iuvpaa-support=unsupported" \
  --data-urlencode "return_to=" \
  --data-urlencode "allow_signup=" \
  --data-urlencode "device_id=$DEVICE_ID" \
  --data-urlencode "required_field_xxxx=" \
  "https://github.com/session" -o "$RESPONSE_HTML"

# Check for successful login
if grep -q "Incorrect username or password." "$RESPONSE_HTML"; then
  echo "Login failed. Check $RESPONSE_HTML for details."
  exit 1
else
  echo "Login successful! Response saved to $RESPONSE_HTML."
  exit 0
fi