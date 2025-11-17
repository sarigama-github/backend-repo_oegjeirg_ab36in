import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="FlameWire API", version="1.0.0")

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

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/api/health")
def api_health(request: Request):
    started = time.time()
    # lightweight work
    _ = len(SUPPORTED_CHAINS)
    latency_ms = int((time.time() - started) * 1000)
    return {
        "status": "ok",
        "service": "flamewire",
        "latency_ms": latency_ms,
        "chains": SUPPORTED_CHAINS,
        "region": os.getenv("REGION", "global"),
        "version": "1.0.0",
    }

@app.get("/api/chains")
def get_chains():
    return {"chains": SUPPORTED_CHAINS}

@app.post("/api/rpc/{chain}")
def proxy_rpc(chain: str = Path(..., description="Chain code, e.g., eth, bittensor, sui"), payload: RPCRequest = None):
    codes = {c["code"] for c in SUPPORTED_CHAINS}
    if chain not in codes:
        raise HTTPException(status_code=404, detail="Unsupported chain")

    # Mock behavior: return deterministic sample data per method
    method = (payload.method or "").lower()
    rid = payload.id if payload and payload.id is not None else 1

    if chain == "eth" and method == "eth_blocknumber":
        return RPCResponse(jsonrpc="2.0", id=rid, result="0x12ab34")
    if chain == "sui" and method == "sui_getlatestcheckpointsequence".lower():
        return RPCResponse(jsonrpc="2.0", id=rid, result=123456)
    if chain == "bittensor" and method == "subnet.get_state":
        return RPCResponse(jsonrpc="2.0", id=rid, result={"subnets": 32})

    # default echo for unknown methods
    return RPCResponse(jsonrpc="2.0", id=rid, result={
        "echo": {
            "chain": chain,
            "method": payload.method,
            "params": payload.params or [],
        },
        "note": "Mock response. Connect real nodes/providers to enable live routing.",
    })

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
