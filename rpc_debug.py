#!/usr/bin/env python3
"""
Small helper to debug RPC calls locally: shows balance before/after calling deduct_credit
"""
import argparse
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_supabase():
    if not SUPABASE_SERVICE_KEY:
        raise EnvironmentError("SUPABASE_SERVICE_KEY is required to run this debug script")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def main():
    parser = argparse.ArgumentParser(description="Debug deduct_credit RPC")
    parser.add_argument('--user', type=int, required=True, help='Telegram user ID')
    args = parser.parse_args()
    supabase = get_supabase()
    before = supabase.table('usuarios').select('credit_balance').eq('user_id', args.user).execute().data
    before_val = before[0]['credit_balance'] if before and len(before) > 0 else None
    logger.info(f"Before balance: {before_val}")
    res = supabase.rpc('deduct_credit', {'uid': args.user}).execute()
    logger.info(f"RPC raw response: data={getattr(res, 'data', None)} error={getattr(res, 'error', None)} status={getattr(res, 'status_code', None)}")
    after = supabase.table('usuarios').select('credit_balance').eq('user_id', args.user).execute().data
    after_val = after[0]['credit_balance'] if after and len(after) > 0 else None
    logger.info(f"After balance: {after_val}")

if __name__ == '__main__':
    main()
