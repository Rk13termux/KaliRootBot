"""
Script to seed user credits in Supabase for testing the bot and AI.

Usage examples:
  # Add 5 credits to user 12345 (use RPC add_credits if exists)
  python seed_users.py --add --user 12345 --amount 5

  # Set user 12345 balance to 10 (upsert)
  python seed_users.py --set --user 12345 --amount 10

  # Load from a JSON file: list of objects {"user_id": 12345, "amount": 10}
  python seed_users.py --file users.json

Important: run with active virtualenv or use `dev_setup.sh` first.
"""
import argparse
import json
import logging
import os
from typing import List, Dict

try:
    from supabase import create_client  # type: ignore[import]
except Exception as e:
    # Friendly error for devs when the venv isn't active or deps not installed
    import sys
    print("\n[ERROR] No se ha podido resolver la importación 'supabase'. Asegúrate de tener el virtualenv activado y las dependencias instaladas:")
    print("  python -m venv venv")
    print("  source venv/bin/activate")
    print("  pip install -r requirements.txt")
    print("Luego selecciona el intérprete correcto en VSCode y recarga la ventana si usas Pylance.\n")
    raise
from config import SUPABASE_URL, SUPABASE_ANON_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def upsert_user_balance(supabase, user_id: int, amount: int, first_name: str = None, last_name: str = None, username: str = None):
    # Upsert (set) balance to an absolute value
    data = {"user_id": user_id, "credit_balance": amount}
    if first_name:
        data["first_name"] = first_name
    if last_name:
        data["last_name"] = last_name
    if username:
        data["username"] = username
    res = supabase.table("usuarios").upsert(data).execute()
    if getattr(res, "status_code", None) and 200 <= res.status_code < 300:
        logger.info(f"Upserted user {user_id} -> {amount} credits")
    else:
        logger.error("Upsert failed: %s", res)
    return res


def add_credits_rpc(supabase, user_id: int, amount: int):
    # Uses the RPC add_credits(uid, amount) we defined in SQL migration
    try:
        res = supabase.rpc("add_credits", {"uid": user_id, "amount": amount}).execute()
        logger.info(f"add_credits RPC invoked for {user_id} +{amount}")
        return res
    except Exception as e:
        logger.exception("RPC add_credits failed: %s", e)
        return None


def seed_from_file(supabase, path: str, mode: str = "add"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("File JSON must be a list of objects: [{ 'user_id': int, 'amount': int }, ...]")
    for item in data:
        uid = int(item.get("user_id") or item.get("userId") or item.get("id"))
        amount = int(item.get("amount"))
        if mode == "set":
            upsert_user_balance(supabase, uid, amount)
        else:
            add_credits_rpc(supabase, uid, amount)


def parse_cli_args():
    parser = argparse.ArgumentParser(description="Seed user credits into the Supabase DB")
    parser.add_argument("--user", type=int, help="User ID (telegram user id)")
    parser.add_argument("--amount", type=int, help="Amount to add or set")
    parser.add_argument("--first-name", type=str, help="First name to set for user")
    parser.add_argument("--last-name", type=str, help="Last name to set for user")
    parser.add_argument("--username", type=str, help="Telegram username to set for user")
    parser.add_argument("--add", action="store_true", help="Add credits using add_credits RPC (default behavior)")
    parser.add_argument("--set", action="store_true", help="Set (upsert) absolute balance for user")
    parser.add_argument("--file", type=str, help="JSON file with list of { user_id, amount }")
    return parser.parse_args()


def main():
    args = parse_cli_args()
    supabase = get_supabase_client()

    mode = "add"
    if args.set:
        mode = "set"

    if args.file:
        seed_from_file(supabase, args.file, mode=mode)
        return

    if not args.user or args.amount is None:
        logger.error("You must specify --user and --amount, or use --file with a list of users.")
        return

    uid = args.user
    amount = args.amount

    if mode == "set":
        upsert_user_balance(supabase, uid, amount, first_name=args.first_name, last_name=args.last_name, username=args.username)
    else:
        # Optionally update names when adding credits
        if args.first_name or args.last_name or args.username:
            upsert_user_balance(supabase, uid, 0, first_name=args.first_name, last_name=args.last_name, username=args.username)
        add_credits_rpc(supabase, uid, amount)


if __name__ == "__main__":
    main()
