"""
Script para poblar la tabla 'knowledge_base' en Supabase con entradas de ejemplo y embeddings.
 - Calcula embeddings usando la API de Groq (modelo configurable con `GROQ_MODEL`).
- Inserta entradas con `content_embedding` y metadatos.

NOTAS DE SEGURIDAD (LEER):
- El contenido está orientado a educación y ética. Evita proporcionar instrucciones no éticas o paso-a-paso para actividades maliciosas.
- Este script solo inserta contenido de ejemplo; adapta los textos según tus necesidades y políticas legales.
"""

import os
import sys
import json
from typing import List
from config import SUPABASE_URL, SUPABASE_ANON_KEY, GROQ_API_KEY, GROQ_MODEL

# Validate imports and provide clearer guidance if missing
try:
    from supabase import create_client  # type: ignore[reportMissingImports]
except Exception as e:
    print("ERROR: No se puede importar 'supabase'. Asegúrate de activar tu venv y ejecutar: pip install supabase")
    print("Ejecuta: ./dev_setup.sh o python -m pip install supabase groq python-dotenv")
    raise

try:
    from groq import Groq  # type: ignore[reportMissingImports]
except Exception as e:
    print("ERROR: No se puede importar 'groq'. Asegúrate de activar tu venv y ejecutar: pip install groq")
    print("Ejecuta: ./dev_setup.sh o python -m pip install supabase groq python-dotenv")
    raise

# Inicializa Supabase y el modelo de embeddings
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
groq_client = Groq(api_key=GROQ_API_KEY)

# Lista de entradas de ejemplo (enfoque educativo, seguro y ético)
SAMPLES = [
    {
        "title": "Introducción a Kali Linux",
        "content": (
            "Kali Linux es una distribución basada en Debian orientada a pruebas de penetración y auditoría de seguridad. "
            "Se usa típicamente en entornos controlados de laboratorio y con permiso explícito. "
            "Este documento explica conceptos, no provee instrucciones para actividades ilegales."
        ),
        "tags": ["kali","introducción","ética","laboratorio"],
        "metadata": {"level": "beginner", "persona": "hacker_vibe"},
        "source": "kali-official-docs"
    },
    {
        "title": "Buenas prácticas para un laboratorio seguro",
        "content": (
            "Para realizar pruebas de seguridad, configura entornos aislados (VM o contenedores), usa redes internas y solicita permisos claros. "
            "Documenta cada paso y conserva registros de consentimiento y scope."
        ),
        "tags": ["lab","seguridad","ética"],
        "metadata": {"level": "intermediate", "persona": "hacker_vibe"},
        "source": "internal-guides"
    },
    {
        "title": "Herramientas comunes (visión general)",
        "content": (
            "Kali incluye herramientas para mapeo de red (por ejemplo: Nmap, en un contexto de auditoría), análisis de vulnerabilidades, forense y pentesting. "
            "Asegúrate de entender su propósito y limita su uso a entornos legales y autorizados."
        ),
        "tags": ["herramientas","nmap","pentesting"],
        "metadata": {"level": "intermediate"},
        "source": "kali-toolbox"
    },
    {
        "title": "Reconocimiento y enumeración — conceptos",
        "content": (
            "El reconocimiento es la fase de recopilación de información. Aquí se describen metodologías y principios: recopilación pasiva vs activa, alcance, y minimización del impacto. "
            "Este resumen no incluye comandos operativos.")
        ,
        "tags": ["reconocimiento","enumeración","metodología"],
        "metadata": {"level": "intermediate"},
        "source": "red-team-principles"
    },
    {
        "title": "Explotación responsable y reportes",
        "content": (
            "Una vez validada una vulnerabilidad en un entorno controlado, documenta el impacto, el método de prueba y remediaciones sugeridas. "
            "El objetivo es mejorar la seguridad y no causar daño."
        ),
        "tags": ["explotación","reporting","ética"],
        "metadata": {"level": "advanced"},
        "source": "ethical-hacking-guides"
    },
    {
        "title": "Hardening y contramedidas básicas",
        "content": (
            "Principios de fortificación: mantener sistemas actualizados, gestionar privilegios, configurar cortafuegos, y proteger puertos expuestos. "
            "La defensa informada es la mejor práctica para reducir la superficie de ataque."
        ),
        "tags": ["defense","hardening"],
        "metadata": {"level": "intermediate"},
        "source": "defense-playbook"
    },
    {
        "title": "Comandos útiles del shell (seguridad y administración)",
        "content": (
            "Comandos de administración estándar: 'ls', 'cd', 'pwd', 'ps aux', 'top', 'journalctl' — útiles para diagnóstico y administración. "
            "No se incluyen comandos de explotación ni uso ilegal."
        ),
        "tags": ["comandos","shell","administración"],
        "metadata": {"level": "beginner"},
        "source": "sysadmin-basics"
    },
    {
        "title": "Guía de estilo 'hacker' (ponte en el papel)"
        ,"content": (
            "Responde con un tono ágil y técnico: usa jerga técnica sin incitar a actividades ilegales; haz énfasis en ética, laboratorios y aprendizaje. "
            "Ejemplo: 'Bienvenido, cadete: en este laboratorio vas a practicar reconocimiento en una VM aislada, siempre con permiso.'"
        ),
        "tags": ["persona","hacker_vibe","tono"],
        "metadata": {"level": "guide"},
        "source": "assistant-persona"
    }
]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embeddings using the Groq embeddings API.

    If neither provider is available, raise an informative error.
    """
    # Generate embeddings via Groq for the provided texts
    if isinstance(texts, str):
        texts = [texts]
    try:
        resp = groq_client.embeddings.create(model=GROQ_MODEL, input=texts)
        out = []
        if hasattr(resp, 'data') and isinstance(resp.data, list):
            for item in resp.data:
                emb = item.get('embedding') if isinstance(item, dict) else None
                out.append(emb)
            return out
        elif isinstance(resp, dict) and resp.get('data'):
            for item in resp['data']:
                out.append(item.get('embedding'))
            return out
        elif isinstance(resp, list):
            return resp
    except Exception as e:
            raise RuntimeError(f"Error al generar embeddings con Groq: {e}")
    raise RuntimeError('No embeddings generated (Groq embeddings returned empty).')


def insert_samples(preview: bool = True):
    texts = [s["content"] for s in SAMPLES]
    embeddings = embed_texts(texts)

    for i, sample in enumerate(SAMPLES):
        payload = {
            "title": sample["title"],
            "content": sample["content"],
            "content_embedding": embeddings[i],
            "tags": sample["tags"],
            "metadata": sample["metadata"],
            "source": sample["source"]
        }
        if preview:
            print("---\nPayload (preview):",
                  json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            # Inserta en la tabla knowledge_base
            res = supabase.table("knowledge_base").insert(payload).execute()
            if res.status_code and 200 <= res.status_code < 300:
                print(f"Inserted: {payload['title']}")
            else:
                print(f"Failed to insert: {payload['title']}", res)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Poblar la tabla knowledge_base en Supabase')
    parser.add_argument('--preview', action='store_true', help='Solo mostrar payloads, no insertar (default ON)')
    parser.add_argument('--insert', dest='preview', action='store_false', help='Insertar en Supabase')
    args = parser.parse_args()

    print("Cargando embeddings y preparando inserción. Advertencia: contenido de ejemplo, respete la ley y ética.")
    insert_samples(preview=args.preview)
