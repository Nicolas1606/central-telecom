"""Cliente do Ollama com orçamento limitado, telemetria e contratos tipados."""
import hashlib
import json
import os
import time
import httpx
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from .knowledge import ROOT

CONFIG = json.loads((ROOT / "config/agents.json").read_text(encoding="utf-8"))
class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")
class Route(Strict):
    domains: list[Literal["cobranca","suporte","cancelamento","humano","outras","esclarecer"]] = Field(min_length=1,max_length=3)
class Choice(Strict):
    source_id: str = Field(max_length=16)
class Verdict(Strict):
    verdict: Literal["pass","fail"]
    reason: str = Field(min_length=5,max_length=600)
class Unavailable(Exception):
    pass

class Ollama:
    def __init__(self):
        self.url = os.getenv("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
        self.config = CONFIG
        if os.getenv("AGENT_CONFIG"):
            self.config = json.loads(open(os.environ["AGENT_CONFIG"],encoding="utf-8").read())

    def chat(self, role, messages, trace, *, contract=None, tools=None):
        cfg = self.config[role]
        version = cfg.get("prompt_version","v2" if role == "router" else "v1")
        system = (ROOT / f"prompts/{role}.{version}.txt").read_text(encoding="utf-8")
        data = {"model":cfg["model"],"stream":False,"think":cfg["think"],
                "options":{"temperature":cfg["temperature"],"num_predict":cfg["max_tokens"],"num_ctx":4096},
                "messages":[{"role":"system","content":system},*messages]}
        if contract:
            data["format"] = contract.model_json_schema()
        if tools:
            data["tools"] = tools
        span = {"agent":role,"model":cfg["model"],"prompt":version,
                "hash":hashlib.sha256(system.encode()).hexdigest()[:12],"tokens_in":None,"tokens_out":None,
                "cost_usd":None,"ok":False}
        start = time.perf_counter()
        try:
            with httpx.Client(trust_env=False,timeout=60) as client:
                response = client.post(self.url+"/api/chat", json=data)
            response.raise_for_status()
            result = response.json()
            msg = result["message"]
            a,b = result.get("prompt_eval_count"),result.get("eval_count")
            span.update(tokens_in=a,tokens_out=b)
            rates = cfg["input_usd_per_million"],cfg["output_usd_per_million"]
            if all(v is not None for v in (*rates,a,b)):
                span["cost_usd"] = (a*rates[0]+b*rates[1])/1e6
            output = contract.model_validate_json(msg["content"]) if contract else msg
            span["ok"] = True
            return output
        except (httpx.HTTPError,ValueError,KeyError,TypeError) as exc:
            span["error"] = type(exc).__name__
            raise Unavailable("Resposta do provedor indisponível ou fora do contrato") from exc
        finally:
            span["latency_ms"] = round((time.perf_counter()-start)*1000,2)
            trace.append(span)

def user(data):
    return {"role":"user","content":json.dumps(data,ensure_ascii=False)}
