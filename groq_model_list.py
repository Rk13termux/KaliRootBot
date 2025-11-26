#!/usr/bin/env python3
"""
Quick helper: list models available in your Groq account via the API.
Require: GROQ_API_KEY in environment or .env
"""
import os
from groq import Groq
from config import GROQ_API_KEY
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    if not GROQ_API_KEY:
        logger.error('GROQ_API_KEY not set in environment')
        return
    client = Groq(api_key=GROQ_API_KEY)
    try:
        models = client.models.list()  # type: ignore[attr-defined]
        if hasattr(models, 'data') and models.data:
            for m in models.data:
                print(m.id)
        elif isinstance(models, dict) and models.get('data'):
            for m in models.get('data'):
                print(m.get('id'))
        else:
            print('No models returned')
    except Exception as e:
        logger.exception('Failed to list models: %s', e)


if __name__ == '__main__':
    main()
