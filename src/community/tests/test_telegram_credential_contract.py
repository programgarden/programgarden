"""Telegram setup contracts and a network-free validation boundary."""
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from programgarden_core.registry import get_credential_type_registry
from programgarden_community.nodes.messaging.telegram import TelegramNode


def test_telegram_form_and_native_schema_agree():
    field = TelegramNode.get_field_schema()['credential_id']
    assert field.credential_types == ['telegram_bot', 'telegram']
    assert field.ui_component == 'custom_credential_select'
    for alias in field.credential_types:
        fields = get_credential_type_registry().get(alias).widget_schema['fields']
        assert {f['key'] for f in fields if f.get('required')} >= {'bot_token', 'chat_id'}
    node = TelegramNode(id='notify', bot_token='private-bot-token', chat_id='-123456')
    assert 'private-bot-token' not in node.model_dump_json() + repr(node)
    assert '-123456' not in node.model_dump_json() + repr(node)


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['is_dry_run', 'is_deep_validate'])
async def test_direct_validation_does_not_send_messages(mode, monkeypatch):
    import aiohttp
    network = MagicMock(side_effect=AssertionError('Telegram send forbidden'))
    monkeypatch.setattr(aiohttp, 'ClientSession', network)
    node = TelegramNode(id='notify', bot_token='private-bot-token', chat_id='-123456', template='hello')
    result = await node.execute(SimpleNamespace(**{mode: True}))
    assert result['sent'] is False
    assert result['live_delivery_verified'] is False
    network.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_network_error_does_not_expose_token(monkeypatch):
    import aiohttp
    monkeypatch.setattr(aiohttp, 'ClientSession', MagicMock(side_effect=aiohttp.ClientError('https://api.telegram.org/botprivate-bot-token/sendMessage')))
    result = await TelegramNode(id='n', bot_token='private-bot-token', chat_id='-123456').execute(SimpleNamespace())
    assert result['sent'] is False and result['error_code'] == 'TELEGRAM_NETWORK_ERROR'
    assert 'private-bot-token' not in str(result)
