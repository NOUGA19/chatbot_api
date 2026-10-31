"""Gemini et Groq en streaming, avec ordre configurable et mesure du temps."""
import json
import os
import time
from typing import AsyncIterator

import httpx

FALLBACK_MSG = ("Désolé, l'assistant est momentanément indisponible. "
                "Vous pouvez utiliser la recherche du site ou contacter la scolarité.")

# connexion rapide à échouer, lecture assez patiente
TIMEOUT = httpx.Timeout(connect=5, read=30, write=10, pool=5)


async def _gemini(system: str, messages: list[dict]) -> AsyncIterator[str]:
    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {"temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream("POST", url, json=body, headers={"x-goog-api-key": key}) as r:
            if r.status_code != 200:
                raise RuntimeError(f"Gemini {r.status_code}: {(await r.aread())[:200]!r}")
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = json.loads(line[5:].strip())
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        if part.get("text") and not part.get("thought"):
                            yield part["text"]


async def _groq(system: str, messages: list[dict]) -> AsyncIterator[str]:
    key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    body = {
        "model": model,
        "stream": True,
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}] + messages,
    }
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"   # moins de « réflexion », premier mot plus vite
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        async with client.stream(
            "POST", "https://api.groq.com/openai/v1/chat/completions",
            json=body, headers={"Authorization": f"Bearer {key}"},
        ) as r:
            if r.status_code != 200:
                raise RuntimeError(f"Groq {r.status_code}: {(await r.aread())[:200]!r}")
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                delta = json.loads(payload)["choices"][0]["delta"].get("content")
                if delta:
                    yield delta


def configured_providers() -> list[str]:
    """Ordre défini par PROVIDER_ORDER (ex. 'groq,gemini'), seulement ceux qui ont une clé."""
    keys = {"gemini": os.getenv("GEMINI_API_KEY"), "groq": os.getenv("GROQ_API_KEY")}
    order = [p.strip() for p in os.getenv("PROVIDER_ORDER", "groq,gemini").split(",")]
    return [p for p in order if keys.get(p)]


async def stream_answer(system: str, messages: list[dict]) -> AsyncIterator[str]:
    funcs = {"gemini": _gemini, "groq": _groq}
    for name in configured_providers():
        sent = False
        t0 = time.time()
        try:
            async for chunk in funcs[name](system, messages):
                if not sent:
                    print(f"[llm] {name} : premier texte après {time.time() - t0:.1f}s")
                sent = True
                yield chunk
            if sent:
                print(f"[llm] {name} : terminé en {time.time() - t0:.1f}s")
                return
        except Exception as e:
            print(f"[llm] {name} a échoué après {time.time() - t0:.1f}s : {e}")
            if sent:
                return
    yield FALLBACK_MSG