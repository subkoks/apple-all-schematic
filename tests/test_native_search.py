"""Regression cases for native model queries (no Telegram access)."""

import pytest

from native_search import matches


@pytest.mark.parametrize(('text', 'query', 'expected'), [
    ('820-1960 (project M50).rar', 'M5', False),
    ('MacBook_Pro_M5.pdf', 'MacBook Pro M5', True),
    ('MacBookPro M5Pro schematic.pdf', 'MacBook Pro M5', True),
    ('Mac Book Pro M5.pdf', 'macbook pro m5', True),
    ('MacBook Pro M4.pdf', 'MacBook Pro M5', False),
    ('MacBook Air M5.pdf', 'MacBook Pro M5', False),
    ('MacBook Pro M50.pdf', 'MacBook Pro M5', False),
    ('MacBook Pro M5.pdf', 'M5 Max', False),
    ('820-1960.pdf', '820-1960', True),
    ('820-19601.pdf', '820-1960', False),
    ('any.pdf', ' ', True),
    ('any.pdf', '---', False),
])
def test_model_queries(text, query, expected):
    assert matches(text, query) is expected


@pytest.mark.asyncio
async def test_native_filter_rejects_false_downloads(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    import tg_schematic_downloader as scraper

    names = ['MacBook Pro M5.pdf', 'MacBook Pro M50.pdf', 'MacBook Air M5.pdf']
    messages = [SimpleNamespace(id=i, message='', name=name) for i, name in enumerate(names)]

    async def iterate(*args, **kwargs):
        for message in messages:
            yield message

    monkeypatch.setattr(scraper, 'DOWNLOAD_DIR', tmp_path)
    monkeypatch.setattr(scraper, 'get_filename', lambda message: message.name)
    monkeypatch.setattr(scraper, 'save_state', lambda state: None)
    download = AsyncMock()
    client = SimpleNamespace(get_entity=AsyncMock(return_value='fixture'),
                             iter_messages=iterate, download_media=download)
    await scraper.process_channel(client, 'fixture', {'downloaded': {}}, False,
                                  ['MacBook', 'Pro', 'M5'], None, False, exact_keywords=True)
    assert [call.args[0].name for call in download.call_args_list] == [names[0]]
    download.reset_mock()
    await scraper.process_channel(client, 'fixture', {'downloaded': {}}, False,
                                  ['MacBook', 'Pro', 'M5'], None, False)
    assert download.await_count == len(names)  # Legacy CLI/Qt matching stays unchanged.
