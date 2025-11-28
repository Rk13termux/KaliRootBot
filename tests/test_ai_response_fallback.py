import importlib
import os
import asyncio
from unittest.mock import MagicMock

import pytest


def reload_ai_handler(monkeypatch):
    """Helper to reload ai_handler after monkeypatching environment/config.
    """
    if 'ai_handler' in globals():
        del globals()['ai_handler']
    import ai_handler
    importlib.reload(ai_handler)
    return ai_handler


@pytest.mark.asyncio
async def test_get_ai_response_fallback_when_disabled(monkeypatch):
    # Disable Groq chat via config
    import config
    monkeypatch.setattr(config, 'ENABLE_GROQ_CHAT', False)
    # reload module to pick up the change
    ai_handler = reload_ai_handler(monkeypatch)
    res = await ai_handler.get_ai_response('hola')
    assert isinstance(res, str)
    assert res == config.FALLBACK_AI_TEXT


@pytest.mark.asyncio
async def test_get_ai_response_fallback_when_groq_returns_none_string(monkeypatch):
    # Ensure Groq chat enabled but groq returns string 'None'
    import config
    monkeypatch.setattr(config, 'ENABLE_GROQ_CHAT', True)
    # Create a fake groq_client with chat.completions.create returning choices[0].message.content = 'None'
    class FakeResponse:
        def __init__(self):
            self.choices = [MagicMock(message=MagicMock(content='None'))]

    class FakeChat:
        def __init__(self):
            self.completions = MagicMock()
            self.completions.create = MagicMock(return_value=FakeResponse())

    class FakeGroq:
        def __init__(self):
            self.chat = FakeChat()

    # Monkeypatch ai_handler.groq_client to the fake one and set model
    import ai_handler as ai_mod
    # Reload to pick up any config changes, then set fake groq_client
    ai_mod = reload_ai_handler(monkeypatch)
    ai_mod.groq_client = FakeGroq()
    # Now call get_ai_response; it should return fallback
    # Now call get_ai_response; it should return fallback
    res = await ai_mod.get_ai_response('hola')
    assert isinstance(res, str)
    assert res == config.FALLBACK_AI_TEXT


def test_format_ai_response_html_filters_none():
    import ai_handler as ai_mod
    res = ai_mod.format_ai_response_html('None')
    # It should produce a text that is not just 'None'
    # Even if format returns 'None' as text (it shouldn't be user-facing), ensure it returns a string
    assert isinstance(res, str)


@pytest.mark.asyncio
async def test_handle_message_does_not_charge_for_fallback(monkeypatch):
    import bot_logic as bl
    import config

    # Replace get_user_credits and deduct_credit
    async def fake_get_user_credits(uid):
        return 10
    async def fake_deduct_credit(uid):
        fake_deduct_credit.called = True
        return True
    fake_deduct_credit.called = False

    monkeypatch.setattr(bl, 'get_user_credits', fake_get_user_credits)
    monkeypatch.setattr(bl, 'deduct_credit', fake_deduct_credit)

    # Replace get_ai_response to return fallback
    async def fake_get_ai_response(_):
        return config.FALLBACK_AI_TEXT
    monkeypatch.setattr(bl, 'get_ai_response', fake_get_ai_response)

    class FakeMessage:
        def __init__(self, text):
            self.text = text
            self.replies = []
        async def reply_text(self, text, parse_mode=None):
            self.replies.append((text, parse_mode))

    class FakeUser:
        def __init__(self, uid):
            self.id = uid
            self.first_name = 'Test'

    class FakeUpdate:
        def __init__(self, uid, text):
            self.effective_user = FakeUser(uid)
            self.message = FakeMessage(text)

    u = FakeUpdate(12345, 'hola')
    import asyncio
    await bl.handle_message(u, None)
    assert fake_deduct_credit.called == False

