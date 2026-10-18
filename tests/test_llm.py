import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src import config, llm


@pytest.mark.asyncio
@pytest.mark.parametrize('polish', [False, True])
async def test_claude_dispatch(monkeypatch, polish):
    import claude_agent_sdk as sdk
    captured = {}

    async def query(**kwargs):
        captured.update(kwargs)
        yield sdk.AssistantMessage(content=[sdk.TextBlock(text='{"script": []}')], model='test')

    monkeypatch.setattr(config, 'LLM_PROVIDER', 'claude')
    monkeypatch.setattr(sdk, 'query', query)
    assert await llm.generate_text('system', 'paper', polish=polish) == '{"script": []}'
    assert captured['options'].model == (config.CLAUDE_POLISH_MODEL if polish else config.CLAUDE_MODEL)
    assert captured['options'].system_prompt == 'system'
    assert captured['options'].allowed_tools == []


@pytest.mark.asyncio
@pytest.mark.parametrize('polish,model', [(False, 'draft-model'), (True, 'review-model')])
async def test_codex_stdin_and_output(monkeypatch, polish, model):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'codex')
    monkeypatch.setattr(config, 'CODEX_MODEL', 'draft-model')
    monkeypatch.setattr(config, 'CODEX_POLISH_MODEL', 'review-model')

    async def launch(*args, **kwargs):
        assert args[args.index('--model') + 1] == model
        assert 'paper text' not in args
        assert kwargs['cwd'] != str(config.PROJECT_ROOT)
        output = Path(args[args.index('--output-last-message') + 1])

        async def communicate(data):
            assert b'system' in data and b'paper text' in data
            output.write_text('{"script": []}')
            return None, b''

        return SimpleNamespace(returncode=0, communicate=communicate)

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', launch)
    assert await llm.generate_text('system', 'paper text', polish=polish) == '{"script": []}'


@pytest.mark.asyncio
@pytest.mark.parametrize('case,match', [('missing', 'not found'), ('failed', 'exited'), ('no_output', 'response file'), ('empty', 'empty response'), ('timeout', 'timed out')])
async def test_codex_errors(monkeypatch, case, match):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'codex')
    process = SimpleNamespace(returncode=1 if case == 'failed' else 0, kill=AsyncMock())

    async def launch(*args, **kwargs):
        if case == 'missing':
            raise FileNotFoundError()
        if case == 'empty':
            Path(args[args.index('--output-last-message') + 1]).write_text(' ')
        process.communicate = AsyncMock(return_value=(None, b'private diagnostic'))
        if case == 'timeout':
            process.returncode = None
            process.kill = lambda: setattr(process, 'returncode', -9)
            process.communicate.side_effect = [asyncio.TimeoutError(), (None, b'')]  # noqa: UP041 (Python 3.10)
        return process

    monkeypatch.setattr(asyncio, 'create_subprocess_exec', launch)
    with pytest.raises(RuntimeError, match=match):
        await llm.generate_text('system', 'paper')
    if case == 'timeout':
        assert process.returncode == -9


@pytest.mark.asyncio
async def test_invalid_provider(monkeypatch):
    monkeypatch.setattr(config, 'LLM_PROVIDER', 'typo')
    with pytest.raises(ValueError, match='LLM_PROVIDER'):
        await llm.generate_text('system', 'paper')


@pytest.mark.asyncio
async def test_all_script_stages_use_shared_provider(monkeypatch):
    from src.anime import script_gen
    from src.script import generator, shorts_generator

    calls = []

    async def generate(system, prompt, **kwargs):
        calls.append((system, prompt, kwargs))
        return '{"script": []}'

    for module in [generator, shorts_generator, script_gen]:
        monkeypatch.setattr(module, 'generate_text', generate)
    await generator._query_claude('longform')
    await shorts_generator._query('shorts', lang='en')
    await shorts_generator._critic_query('{}')
    await shorts_generator._refine_query('{}', '{}')
    await shorts_generator._opus_polish({'script': []})
    await script_gen._query('anime')
    assert len(calls) == 6
    assert calls[1][0] == shorts_generator.SHORTS_SYSTEM_EN
    assert calls[4][2] == {'polish': True}
