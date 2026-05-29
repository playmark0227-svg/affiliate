"""Thin wrapper around the Claude Messages API.

Centralizes the Opus 4.8-era settings so both call sites stay consistent:

- adaptive thinking (`thinking={"type": "adaptive"}`) — higher reasoning quality
- effort control (`output_config={"effort": ...}`) — depth/cost tradeoff
- structured outputs (`output_config={"format": {...}}`) — guaranteed valid JSON,
  so we no longer depend on fragile code-fence stripping
- prompt caching on the system block — the breakpoint is harmless when the
  prefix is below the model's minimum cacheable size and pays off once it isn't
  (long editorial guidelines, or multi-pass within a single run)
- streaming for long generations — avoids HTTP timeouts on big articles

A defensive fallback keeps the unattended cron alive: if the installed SDK or
the target model rejects one of the newer parameters, we retry with a plain
call and tolerant JSON parsing instead of crashing the whole run.
"""
from __future__ import annotations

import json
from typing import Any

import anthropic


def _extract_text(message: Any) -> str:
    """Join the text blocks of a Message, skipping thinking/tool blocks."""
    return "".join(
        b.text for b in message.content if getattr(b, "type", None) == "text"
    ).strip()


def _strip_fences(text: str) -> str:
    """Tolerantly unwrap ```json ... ``` fences from a model reply."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    return text


def generate_json(
    client: anthropic.Anthropic,
    *,
    model: str,
    system: str,
    user: str,
    schema: dict[str, Any],
    effort: str = "high",
    max_tokens: int = 16000,
    stream: bool = True,
) -> dict[str, Any]:
    """Return parsed JSON from a single Claude call.

    Raises ``json.JSONDecodeError`` if even the fallback reply isn't parseable;
    callers decide whether to use a hardcoded fallback or skip the item.
    """
    system_blocks = [
        {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}
    ]
    messages = [{"role": "user", "content": user}]
    output_config = {
        "effort": effort,
        "format": {"type": "json_schema", "schema": schema},
    }

    try:
        if stream:
            with client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system_blocks,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config=output_config,
            ) as s:
                message = s.get_final_message()
        else:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_blocks,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config=output_config,
            )
        _log_cache(message)
        # The format constraint guarantees the text block is valid JSON.
        return json.loads(_extract_text(message))
    except (TypeError, anthropic.BadRequestError) as e:
        # Older SDK (unexpected kwarg) or a model that rejects a newer
        # parameter — degrade gracefully rather than kill the run.
        print(f"[llm] enhanced path unavailable ({type(e).__name__}: {e}); basic call")
        message = client.messages.create(
            model=model,
            max_tokens=min(max_tokens, 8000),  # stay under the non-stream timeout guard
            system=system,
            messages=[{"role": "user", "content": user + "\n\n出力は厳密なJSONのみ。"}],
        )
        return json.loads(_strip_fences(_extract_text(message)))


def _log_cache(message: Any) -> None:
    """Surface cache effectiveness in the run log (best-effort)."""
    usage = getattr(message, "usage", None)
    read = getattr(usage, "cache_read_input_tokens", None)
    if read:
        print(f"[llm] cache_read_input_tokens={read}")
