"""
Simple test script to run the AI response locally using the Groq embeddings & chat API.
This avoids installing torch and uses the remote Groq endpoints.

Usage:
  export GROQ_API_KEY="..."
  export SUPABASE_URL="..."
  export SUPABASE_ANON_KEY="..."
  python run_local_test.py -q "¿Qué es Kali Linux?"

"""
import argparse
import asyncio
import os
# Allow running without all env vars by skipping validation for local tests
os.environ['SKIP_ENV_VALIDATION'] = os.environ.get('SKIP_ENV_VALIDATION', '1')
from ai_handler import get_ai_response

async def main(query):
    try:
        print("Consultando AI con RAG usando Groq embeddings...")
        resp = await get_ai_response(query)
        print("\n---- Respuesta de la IA ----\n")
        print(resp)
    except Exception as e:
        print("Error al obtener respuesta:", e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--query', type=str, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.query))
