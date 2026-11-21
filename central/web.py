import os
from typing import Literal
from uuid import UUID
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from .engine import Engine
from .knowledge import ROOT
from .storage import Conflict, Store

class Start(BaseModel):
    account: Literal["A","B"] = "A"

class Turn(BaseModel):
    key: UUID
    revision: int = Field(ge=0)
    text: str = Field(min_length=1,max_length=1000)
    @field_validator("text")
    @classmethod
    def meaningful(cls,value):
        if not value.strip():
            raise ValueError("Digite uma mensagem.")
        return value.strip()

def create_app(db=None,engine=None):
    app = FastAPI(title="Central Telecom",version="1.0")
    engine = engine or Engine(os.getenv("AGENT_MODE","demo"),os.getenv("AGENT_DESIGN","multi"))
    if os.getenv("ORCHESTRATOR")=="langgraph":
        import langgraph.graph
    store = Store(db or os.getenv("TELECOM_DB",str(ROOT/"runtime/telecom.sqlite3")))
    app.mount("/static",StaticFiles(directory=ROOT/"ui"),name="arquivos")
    @app.middleware("http")
    async def local_origin(request:Request,call_next):
        from urllib.parse import urlparse
        from fastapi.responses import JSONResponse
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail":"Origem diferente da aplicação."},status_code=403)
        return await call_next(request)
    @app.get("/")
    def home():
        return FileResponse(ROOT/"ui/index.html")
    @app.get("/health")
    def health():
        return {"status":"ok","mode":engine.mode,"design":engine.design,"sources":len(engine.index.docs)}
    @app.post("/api/sessions",status_code=201)
    def start(body:Start):
        return {"id":store.new(body.account,engine),"revision":0,"mode":engine.mode}
    @app.post("/api/sessions/{sid}/turn")
    def turn(sid:str,body:Turn):
        try:
            return store.chat(sid,str(body.key),body.text,engine,body.revision)
        except KeyError as exc:
            raise HTTPException(404,"Sessão inexistente") from exc
        except Conflict as exc:
            raise HTTPException(409,str(exc)) from exc
    @app.get("/api/metrics")
    def metrics():
        return store.metrics()
    @app.get("/api/tickets")
    def tickets():
        return store.tickets()
    @app.post("/api/tickets/{tid}/revisar")
    def review(tid:str):
        try:
            store.close(tid)
        except KeyError as exc:
            raise HTTPException(404,"Ticket inexistente") from exc
        return {"status":"revisado"}
    return app
