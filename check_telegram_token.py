"""
Quick script to validate a Telegram bot token by calling getMe.
Usage: python check_telegram_token.py <TELEGRAM_BOT_TOKEN>
If no argument is provided, it will use the environment's TELEGRAM_BOT_TOKEN.
"""
import sys
import os
import requests

if __name__ == '__main__':
    token = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print('No token provided. Export TELEGRAM_BOT_TOKEN or pass as argument.')
        sys.exit(1)
    url = f'https://api.telegram.org/bot{token}/getMe'
    try:
        r = requests.get(url, timeout=5)
    except Exception as e:
        print('Request failed:', e)
        sys.exit(2)
    if r.status_code == 200 and r.json().get('ok'):
        print('Token is valid. getMe response:')
        print(r.json())
        sys.exit(0)
    else:
        print('Token invalid or Telegram returned an error:', r.status_code, r.text)
        sys.exit(3)
