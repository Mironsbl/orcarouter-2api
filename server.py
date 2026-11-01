import os
import json
import itertools
import httpx
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="OrcaRouter 2API Autonomous Gateway", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(BASE_DIR, "keys_pool.json")
UPSTREAM_CHAT_URL = "https://www.orcarouter.ai/api/v1/chat/completions"
UPSTREAM_MODELS_URL = "https://www.orcarouter.ai/api/v1/models"
PROXY_URL = os.getenv("HTTP_PROXY", "http://127.0.0.1:3067")

# Target models
MODELS_MAP = {
    "tencent/hy4-preview-free": "Tencent Hunyuan 4 (770B MoE, 1M Context, MTP speculative)",
    "z-ai/glm-5.3-flash-free": "Z.ai GLM 5.3 Flash (320B, 1M Context, Vision-Language)",
    "deepseek/deepseek-v4.1-flash-free": "DeepSeek V4.1 Flash (1M Context, Native Thinking)",
    "orcarouter/free": "OrcaRouter Free Load Balancer"
}

def load_keys() -> List[str]:
    if not os.path.exists(KEYS_FILE):
        default_data = {
            "keys": ["orca_live_demo_key_placeholder"],
            "description": "OrcaRouter API Keys Pool"
        }
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)
        return default_data["keys"]
    
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return [k.strip() for k in data.get("keys", []) if k.strip() and not k.startswith("orca_live_demo")]

keys_pool = load_keys()
key_cycler = itertools.cycle(keys_pool) if keys_pool else None

def get_next_key() -> str:
    global keys_pool, key_cycler
    if not keys_pool:
        keys_pool = load_keys()
        if not keys_pool:
            raise HTTPException(status_code=500, detail="OrcaRouter keys pool empty! Run auth_device.py to add keys.")
        key_cycler = itertools.cycle(keys_pool)
    return next(key_cycler)

@app.get("/")
def root():
    return {
        "service": "OrcaRouter 2API Gateway",
        "status": "operational",
        "active_keys": len(keys_pool),
        "supported_models": list(MODELS_MAP.keys())
    }

@app.get("/health")
def health():
    return {
        "status": "ok",
        "keys_count": len(keys_pool),
        "proxy": PROXY_URL
    }

@app.get("/v1/models")
async def list_models():
    models = []
    for m_id, desc in MODELS_MAP.items():
        models.append({
            "id": m_id,
            "object": "model",
            "created": 1740000000,
            "owned_by": m_id.split("/")[0],
            "permission": [],
            "root": m_id,
            "parent": None
        })
    # Also add short aliases
    models.append({"id": "hy4-free", "object": "model", "owned_by": "tencent", "root": "hy4-free"})
    models.append({"id": "glm-5.3-free", "object": "model", "owned_by": "z-ai", "root": "glm-5.3-free"})
    return {"object": "list", "data": models}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    stream = body.get("stream", False)
    req_model = body.get("model", "tencent/hy4-preview-free")

    # Resolve aliases
    if req_model == "hy4-free" or "hy4" in req_model.lower():
        body["model"] = "tencent/hy4-preview-free"
    elif req_model == "glm-5.3-free" or "glm-5.3" in req_model.lower():
        body["model"] = "z-ai/glm-5.3-flash-free"
    elif "deepseek" in req_model.lower() and not req_model.endswith("-free"):
        body["model"] = "deepseek/deepseek-v4.1-flash-free"

    active_key = get_next_key()

    headers = {
        "Authorization": f"Bearer {active_key}",
        "Content-Type": "application/json",
        "User-Agent": "curl/8.4.0 (Windows NT 10.0; Win64; x64)"
    }

    mounts = None
    if PROXY_URL:
        mounts = {
            "http://": httpx.AsyncHTTPTransport(proxy=PROXY_URL),
            "https://": httpx.AsyncHTTPTransport(proxy=PROXY_URL)
        }

    client = httpx.AsyncClient(mounts=mounts, timeout=180.0)

    if stream:
        async def stream_generator():
            try:
                async with client.stream("POST", UPSTREAM_CHAT_URL, headers=headers, json=body) as response:
                    if response.status_code != 200:
                        err_bytes = await response.aread()
                        yield f"data: {json.dumps({'error': {'message': err_bytes.decode('utf-8', errors='ignore'), 'code': response.status_code}})}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    async for line in response.aiter_lines():
                        if line:
                            yield f"{line}\n"
                        else:
                            yield "\n"
            finally:
                await client.aclose()

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        try:
            resp = await client.post(UPSTREAM_CHAT_URL, headers=headers, json=body)
            await client.aclose()
            return JSONResponse(status_code=resp.status_code, content=resp.json())
        except Exception as e:
            await client.aclose()
            raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  OrcaRouter 2API Autonomous Gateway (:8095)")
    print(f"  Flagship: tencent/hy4-preview-free (770B MoE, 1M Context)")
    print(f"  Active Keys: {len(keys_pool)}")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8095)
