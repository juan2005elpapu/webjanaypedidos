import os
import requests
from datetime import datetime
from pytz import timezone

HEROKU_API_KEY = os.environ['HEROKU_API_KEY']
HEROKU_APP_NAME = os.environ['HEROKU_APP_NAME']
TZ = timezone("America/Bogota")
HEADERS = {
    "Accept": "application/vnd.heroku+json; version=3",
    "Authorization": f"Bearer {HEROKU_API_KEY}",
    "Content-Type": "application/json",
}

def should_run():
    now = datetime.now(TZ)
    return 8 <= now.hour < 20

def scale_dyno(replicas):
    url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/formation/web"
    payload = {"quantity": replicas}
    resp = requests.patch(url, json=payload, headers=HEADERS)
    resp.raise_for_status()

def main():
    target = 1 if should_run() else 0
    scale_dyno(target)

if __name__ == "__main__":
    main()