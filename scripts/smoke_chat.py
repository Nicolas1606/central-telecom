"""Valide a implantação em loopback com CRM fictício, modelo real e transbordo."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import httpx

ROOT=Path(__file__).resolve().parents[1]

def check():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    with tempfile.TemporaryDirectory() as tmp:
        token=secrets.token_urlsafe(32)
        env={**os.environ,"AGENT_MODE":"ollama","ORCHESTRATOR":"langgraph","AGENT_CONFIG":str(ROOT/"config/piloto.json"),
             "TELECOM_BIND":"127.0.0.1","PORT":str(port),"TELECOM_ENV":"pilot","TELECOM_OPERATOR_TOKEN":token,
             "TELECOM_DB":str(Path(tmp)/"smoke.sqlite3")}
        process=subprocess.Popen([sys.executable,"main.py","serve"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL)
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}",trust_env=False,timeout=90) as client:
                for _ in range(100):
                    if process.poll() is not None: raise RuntimeError("A API encerrou antes da abertura.")
                    try:
                        client.get("/health").raise_for_status()
                        break
                    except httpx.TransportError:
                        time.sleep(.1)
                sid=client.post("/api/sessions",json={"account":"A"}).json()["id"]
                def turn(revision,text):
                    r=client.post(f"/api/sessions/{sid}/turn",json={"key":str(uuid4()),"text":text,"revision":revision})
                    r.raise_for_status()
                    return r.json()
                bill=turn(0,"Qual é o total da minha fatura?")
                if bill["action"]!="answer" or "R$ 94,00" not in bill["message"] or not any(t.get("model") and t.get("ok") for t in bill["trace"]):
                    raise RuntimeError("O modelo não completou a consulta de fatura.")
                ticket=turn(1,"Quero falar com um atendente.")
                headers={"Authorization":"Bearer "+token}
                blocked=client.get("/api/tickets").status_code
                tickets=client.get("/api/tickets",headers=headers).json()
                reviewed=client.post(f"/api/tickets/{ticket['ticket']}/revisar",headers=headers)
                reviewed.raise_for_status()
                if blocked!=401 or tickets[0]["id"]!=ticket["ticket"] or not tickets[0]["summary"]["historico"]:
                    raise RuntimeError("Transbordo ou acesso do operador inconsistente.")
                return {"ambiente":"chat HTTP local • CRM fictício","resposta":bill["message"],"trace":bill["trace"],
                        "fontes":[s["id"] for s in bill["sources"]],"resumo_recebido":tickets[0]["summary"],
                        "fila_sem_token_http":blocked,"resultado_revisao":reviewed.json(),
                        "metricas":client.get("/api/metrics",headers=headers).json()}
        finally:
            process.terminate()
            process.wait(15)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("saida",type=Path)
    args=parser.parse_args()
    with args.saida.open("x",encoding="utf-8") as dest:
        json.dump(check(),dest,ensure_ascii=False,indent=2)
