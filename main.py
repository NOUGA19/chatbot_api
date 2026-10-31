from dotenv import load_dotenv
load_dotenv()

import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from context import get_context
from llm import configured_providers, stream_answer
from prompts import build_system_prompt

app = FastAPI(title="Chatbot procédures")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=20)
    mode: Literal["text", "assistant"] = "text"


@app.post("/chat")
async def chat(req: ChatRequest):
    history = [m.model_dump() for m in req.messages]
    system = build_system_prompt(get_context(history[-1]["content"]), req.mode)
    return StreamingResponse(stream_answer(system, history), media_type="text/plain; charset=utf-8")


@app.get("/health")
def health():
    return {"status": "ok", "providers": configured_providers()}


@app.get("/procedures", response_class=PlainTextResponse)
def procedures():
    """Expose la source de vérité (utile au site Next.js de ton camarade)."""
    return get_context()
