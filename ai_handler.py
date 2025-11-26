import os
from typing import List
from groq import Groq
import logging
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_ANON_KEY, GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

logger.info('Using Groq MODEL for chat & embed: %s', GROQ_MODEL)

async def get_ai_response(query: str) -> str:
    # 1. Generar embedding usando la API de Groq (este proyecto usa Groq para embeddings)
    query_vec: List[float] = []
    # Use Groq embeddings endpoint to get vector without local torch
    # The groq client API for embeddings may differ depending on the package version; adjust if needed.
    emb_resp = None
    used_model = GROQ_MODEL or "embed-english-3.0"
    try:
        emb_resp = groq_client.embeddings.create(model=used_model, input=query)
    except Exception as e:
        logger.exception("Embedding failed with model %s: %s", used_model, e)
        emb_resp = None

    # Normalize embedding response (support various client shapes)
    try:
        if emb_resp and hasattr(emb_resp, 'data') and isinstance(emb_resp.data, list) and len(emb_resp.data) > 0:
            query_vec = emb_resp.data[0].get('embedding', [])
        elif isinstance(emb_resp, dict) and emb_resp.get('data'):
            query_vec = emb_resp['data'][0].get('embedding', [])
        elif isinstance(emb_resp, list) and len(emb_resp) > 0 and isinstance(emb_resp[0], list):
            query_vec = emb_resp[0]
        else:
            query_vec = []
    except Exception:
        logger.exception('Failed to extract embedding vector from result: %s', getattr(emb_resp, 'data', emb_resp))
        query_vec = []
    # 2. Buscar contexto relevante en Supabase
    # 2. Buscar contexto relevante en Supabase (si está disponible). Si falla, continuamos sin contexto.
    context_fragments = []
    try:
        if query_vec:
            res = supabase.rpc("search_knowledge_base", {"query_embedding": query_vec, "top_k": 5}).execute()
        else:
            # If we failed to get embeddings, fallback to returning the most recent entries
            res = supabase.table('knowledge_base').select('content,title').order('created_at', desc=True).limit(5).execute()
        if hasattr(res, 'data') and res.data:
            context_fragments = [item.get("content", "") for item in res.data]
        elif isinstance(res, dict) and res.get('data'):
            context_fragments = [item.get("content", "") for item in res['data']]
    except Exception as e:
        # Si no hay Supabase configurado o RPC falla, dejamos context_fragments vacío
        logger.exception('Error searching knowledge_base: %s', e)
        context_fragments = []
    context = "\n".join(context_fragments)
    # 3. Construir prompt
    prompt = f"Eres un experto en Kali Linux. Responde únicamente usando el siguiente contexto:\n{context}\n\nPregunta: {query}"
    # 4. Llamar a Groq para completado
    # Chat completion: use only Groq chat models
    # This bot uses only the Groq model specified in `GROQ_MODEL` for both embeddings and chat.
    chat_model = GROQ_MODEL
    # Attempt a single Groq chat model specified by config
    try:
        response = groq_client.chat.completions.create(
            model=chat_model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content if response.choices else "No se pudo obtener respuesta de la IA."
    except Exception as e:
        logger.exception('Chat completion error with Groq model %s: %s', chat_model, e)
        # Log model availability if possible for easier debugging
        try:
            model_list = groq_client.models.list()  # type: ignore[attr-defined]
            if hasattr(model_list, 'data') and model_list.data:
                available_models = [m.id for m in model_list.data]
            elif isinstance(model_list, dict) and model_list.get('data'):
                available_models = [m.get('id') for m in model_list.get('data', [])]
            else:
                available_models = []
            logger.debug('Available Groq models: %s', available_models)
        except Exception:
            logger.debug('Could not list Groq models via API for debugging')
    if context:
        # Return the most relevant context fragment or a short summary
        return (f"No puedo generar la respuesta ahora mismo, pero aquí tienes información relacionada:\n{context.splitlines()[0][:800]}")
    return "Lo siento, no puedo procesar tu pregunta en este momento. Inténtalo de nuevo más tarde."
