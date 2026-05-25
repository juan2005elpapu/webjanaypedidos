import argparse
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

def parse_args():
    parser = argparse.ArgumentParser(description="Scale Heroku web dyno on a schedule or by force.")
    parser.add_argument("--force-on", action="store_true", help="Ignore schedule and scale to 1.")
    parser.add_argument("--force-off", action="store_true", help="Ignore schedule and scale to 0.")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.force_on and args.force_off:
        raise SystemExit("Choose only one: --force-on or --force-off")

    if args.force_on:
        target = 1
    elif args.force_off:
        target = 0
    else:
        target = 1 if should_run() else 0
    scale_dyno(target)

if __name__ == "__main__":
    main()