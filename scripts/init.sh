#!/bin/bash
COOKIE_FILE="github_cookies.txt"
LOGIN_PAGE_HTML="github_login.html"

# Fetch the GitHub login page
curl -s -L -c "$COOKIE_FILE" \
  -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.5" \
  -H "DNT: 1" \
  -H "Connection: keep-alive" \
  -H "Upgrade-Insecure-Requests: 1" \
  "https://github.com/login" -o "$LOGIN_PAGE_HTML"

echo "Login page saved to $LOGIN_PAGE_HTML and cookies saved to $COOKIE_FILE."