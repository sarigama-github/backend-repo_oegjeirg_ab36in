import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

try:
    from database import db, create_document
except Exception:
    db = None
    def create_document(*args, **kwargs):
        return None

app = FastAPI(title="FlameWire API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_CHAINS = [
    {"name": "Ethereum", "code": "eth"},
    {"name": "Bittensor", "code": "bittensor"},
    {"name": "Sui", "code": "sui"},
    {"name": "Polkadot", "code": "dot"},
    {"name": "Solana", "code": "sol"},
]

class RPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[List[Any]] = None
    id: Optional[Any] = 1

class RPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any
    result: Any

class ContactMessage(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(..., min_length=5, max_length=5000)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/api/health")
def api_health(request: Request):
    started = time.time()
    _ = len(SUPPORTED_CHAINS)
    latency_ms = int((time.time() - started) * 1000)
    return {
        "status": "ok",
        "service": "flamewire",
        "latency_ms": latency_ms,
        "chains": SUPPORTED_CHAINS,
        "region": os.getenv("REGION", "global"),
        "version": "1.1.0",
    }

@app.get("/api/chains")
def get_chains():
    return {"chains": SUPPORTED_CHAINS}

@app.post("/api/rpc/{chain}")
def proxy_rpc(chain: str = Path(..., description="Chain code, e.g., eth, bittensor, sui"), payload: RPCRequest = None):
    codes = {c["code"] for c in SUPPORTED_CHAINS}
    if chain not in codes:
        raise HTTPException(status_code=404, detail="Unsupported chain")

    method = (payload.method or "").lower() if payload else ""
    rid = payload.id if payload and payload.id is not None else 1

    if chain == "eth" and method == "eth_blocknumber":
        return RPCResponse(jsonrpc="2.0", id=rid, result="0x12ab34")
    if chain == "sui" and method == "sui_getlatestcheckpointsequence":
        return RPCResponse(jsonrpc="2.0", id=rid, result=123456)
    if chain == "bittensor" and method == "subnet.get_state":
        return RPCResponse(jsonrpc="2.0", id=rid, result={"subnets": 32})

    return RPCResponse(jsonrpc="2.0", id=rid, result={
        "echo": {
            "chain": chain,
            "method": payload.method if payload else None,
            "params": payload.params if payload and payload.params else [],
        },
        "note": "Mock response. Connect real nodes/providers to enable live routing.",
    })

@app.post("/api/contact")
def submit_contact(msg: ContactMessage):
    doc_id = None
    try:
        if db is not None:
            doc_id = create_document("contactmessage", msg)
    except Exception:
        doc_id = None
    return {"status": "ok", "stored": bool(doc_id), "id": doc_id}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        from database import db as _db
        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
