import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import tiktoken
import google.generativeai as genai
from transformers import AutoTokenizer
from dotenv import load_dotenv
# read key-value pairs from backend/.env
from typing import Literal, List
load_dotenv()         

# ---------- tokenizers ----------
# OpenAI GPT-3.5/4 and Claude 3 families share the cl100k_base vocabulary
enc_openai  = tiktoken.get_encoding("cl100k_base")
enc_claude  = tiktoken.get_encoding("cl100k_base")
enc_fallback = tiktoken.get_encoding("gpt2")        # GPT-2 vocab for “other”

# lazy-load open-source tokenizers only once
_tokenizers: dict[str, AutoTokenizer] = {}
def get_hf_tok(model_id: str = "hf-internal-testing/llama-tokenizer") -> AutoTokenizer:
    if model_id not in _tokenizers:
        _tokenizers[model_id] = AutoTokenizer.from_pretrained(model_id)
    return _tokenizers[model_id]

# ---------- FastAPI ----------
app = FastAPI(title="Token Counter API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", 
                   "http://127.0.0.1:5173",
                   "https://token-counter.vercel.app", 
    ],      
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMsg(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatReq(BaseModel):
    messages: List[ChatMsg]
    model: str = "openai"          # openai | claude | gemini | llama


class CountReq(BaseModel):
    text: str
    model: str = "openai"         # openai | claude | gemini | llama
    hf_model_id: str | None = None  # optional HuggingFace id

@app.post("/count")
async def count_tokens(req: CountReq):
    txt = req.text or ""
    try:
        match req.model.lower():
            case "openai":
                n = len(enc_openai.encode(txt))

            case "claude":
                n = len(enc_claude.encode(txt))

            case "gemini":
                api_key = os.getenv("GEMINI_API_KEY")
                if not api_key:
                    raise HTTPException(
                        500, "Gemini counting requires GEMINI_API_KEY env var"
                    )
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-pro-latest")
                n = model.count_tokens(txt).total_tokens

            case "llama":
                tok = get_hf_tok(req.hf_model_id or "hf-internal-testing/llama-tokenizer")
                n = len(tok(txt)["input_ids"])

            case _:
                n = len(enc_fallback.encode(txt))

    except Exception as e:
        raise HTTPException(500, f"Counting failed: {e}")

    return {"tokens": n}

@app.post("/chat-count")
async def chat_tokens(req: ChatReq):
    msgs = req.messages
    model = req.model.lower()

    # ---------- OpenAI & Claude (cl100k_base) ----------
    if model in {"openai", "claude"}:
        enc = enc_openai if model == "openai" else enc_claude
        total = 0
        for m in msgs:
            total += len(enc.encode(m.content))
            total += 4 if model == "openai" else 6      # wrapper per message
        if model == "openai":
            total += 2                                  # assistant priming
        return {"tokens": total}

    # ---------- Google Gemini ----------
    if model == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(500, "Gemini counting requires GEMINI_API_KEY")
        genai.configure(api_key=api_key)

        # Gemini count_tokens() accepts only role="user" or "model".
        combined = "\n\n".join(f"[{m.role}] {m.content}" for m in msgs)
        gm_msgs  = [{ "role": "user", "parts": [combined] }]

        n = genai.GenerativeModel("gemini-1.5-pro-latest")\
                .count_tokens(contents=gm_msgs).total_tokens
        return {"tokens": n}

    # ---------- Llama-2 Chat ----------
    if model == "llama":
        tok = get_hf_tok()            # default tokenizer
        total = 1  # BOS
        for m in msgs:
            total += 2                                # [INST] ... [/INST]\n
            total += len(tok(m.content)["input_ids"])
        return {"tokens": total}

    raise HTTPException(400, "Unknown model")
