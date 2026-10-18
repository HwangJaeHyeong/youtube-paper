"""Shared text generation for Claude Agent SDK and authenticated Codex CLI."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from src import config


async def generate_text(system_prompt: str, prompt: str, *, polish: bool = False) -> str:
    provider = config.LLM_PROVIDER
    if provider == "claude":
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            model=config.CLAUDE_POLISH_MODEL if polish else config.CLAUDE_MODEL,
            allowed_tools=[],
        )
        chunks = []
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                chunks.extend(b.text for b in message.content if isinstance(b, TextBlock))
        result = "".join(chunks)
    elif provider == "codex":
        result = await _codex(system_prompt, prompt, polish=polish)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER {provider!r}; choose claude or codex")
    if not result.strip():
        raise RuntimeError(f"{provider} returned an empty response")
    return result


async def _codex(system_prompt: str, prompt: str, *, polish: bool) -> str:
    # Isolated working directory avoids loading repository instructions into a
    # writing task. Send long paper text through stdin, never shell arguments.
    with tempfile.TemporaryDirectory(prefix="papercast-codex-") as directory:
        output = Path(directory) / "response.txt"
        command = [
            config.CODEX_BIN, "exec", "--skip-git-repo-check", "--ephemeral",
            "--sandbox", "read-only", "--color", "never",
            "--output-last-message", str(output),
        ]
        model = config.CODEX_POLISH_MODEL if polish else config.CODEX_MODEL
        if model:
            command.extend(["--model", model])
        command.append("-")
        try:
            process = await asyncio.create_subprocess_exec(
                *command, cwd=directory, stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Codex CLI not found; install it or set CODEX_BIN, then run codex login") from exc
        instructions = (
            "Generate text only. Do not use tools or inspect files. "
            "Return only the requested JSON, without Markdown fences.\n\n"
            f"[Instructions]\n{system_prompt}\n\n[Input]\n{prompt}"
        )
        try:
            await asyncio.wait_for(
                process.communicate(instructions.encode("utf-8")),
                timeout=config.CODEX_TIMEOUT_SECONDS,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError) as exc:  # noqa: UP041 (Python 3.10)
            if process.returncode is None:
                process.kill()
            await process.communicate()
            if isinstance(exc, asyncio.CancelledError):
                raise
            raise RuntimeError("Codex generation timed out; adjust CODEX_TIMEOUT_SECONDS") from exc
        if process.returncode:
            # CLI diagnostics may contain input text; do not echo them.
            raise RuntimeError(
                f"Codex exited with code {process.returncode}; check codex login status and model access"
            )
        if not output.exists():
            raise RuntimeError("Codex completed without a response file")
        return output.read_text(encoding="utf-8")
