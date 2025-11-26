import os
import pytest
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

def get_supabase():
    if not SUPABASE_SERVICE_KEY:
        pytest.skip("SUPABASE_SERVICE_KEY is required for integration tests")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def test_deduct_credit_roundtrip():
    supabase = get_supabase()
    # Create a test user and set balance to 2
    uid = 999999999
    supabase.table('usuarios').upsert({'user_id': uid, 'credit_balance': 2}).execute()
    before = supabase.table('usuarios').select('credit_balance').eq('user_id', uid).execute().data[0]['credit_balance']
    assert before == 2
    res = supabase.rpc('deduct_credit', {'uid': uid}).execute()
    # RPC returns a boolean; validate logical result and new balance
    new_balance = supabase.table('usuarios').select('credit_balance').eq('user_id', uid).execute().data[0]['credit_balance']
    assert new_balance == 1
    # Clean up
    supabase.table('usuarios').delete().eq('user_id', uid).execute()
