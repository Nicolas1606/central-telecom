import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid
import httpx
from central.engine import Engine
from central.knowledge import ROOT

class IntegrationTests(unittest.TestCase):
    def test_mcp_in_workflow(self):
        with patch.dict(os.environ,{"POLICY_TRANSPORT":"mcp"}):
            out=Engine().turn("Qual o total da fatura?",{"account":"A","last":""})
        self.assertEqual(out["action"],"answer")
        self.assertEqual(out["sources"][0]["id"],"FAT-01")

    @unittest.skipUnless(importlib.util.find_spec("langgraph"),"Instale requirements-graph.txt para o executor LangGraph")
    def test_graph_two_specialists(self):
        with patch.dict(os.environ,{"ORCHESTRATOR":"langgraph"}):
            out=Engine().turn("Quero o boleto e minha conexão caiu",{"account":"A","last":""})
        self.assertEqual(out["domains"],["cobranca","suporte"])
        self.assertEqual(len(out["sources"]),2)

    def test_deployed_channel(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket() as probe:
            probe.bind(("127.0.0.1",0));port=probe.getsockname()[1];probe.close()
            env={**os.environ,"PORT":str(port),"TELECOM_BIND":"127.0.0.1","AGENT_MODE":"demo","TELECOM_DB":folder+"/channel.db"}
            p=subprocess.Popen([sys.executable,"main.py","serve"],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                with httpx.Client(base_url=f"http://127.0.0.1:{port}",trust_env=False,timeout=5) as client:
                    for _ in range(150):
                        try:
                            client.get("/health").raise_for_status()
                            break
                        except httpx.TransportError:
                            time.sleep(.1)
                    for path in ["/","/static/app.js","/static/app.css","/docs"]:
                        self.assertEqual(client.get(path).status_code,200)
                    sid=client.post("/api/sessions",json={"account":"A"}).json()["id"]
                    def send(message,revision):
                        return client.post("/api/sessions/"+sid+"/turn",json={"text":message,"key":str(uuid.uuid4()),"revision":revision}).json()
                    self.assertEqual(send("Minha fatura veio mais cara e se isso continuar quero cancelar",0)["action"],"clarify")
                    tid=send("Quero cancelar agora",1)["ticket"]
                    self.assertEqual(client.get("/api/tickets").json()[0]["id"],tid)
                    self.assertEqual(client.post(f"/api/tickets/{tid}/revisar").json()["status"],"revisado")
                    self.assertEqual(client.get("/api/metrics").json()["turnos"],2)
                subprocess.run([sys.executable,"main.py","analyze","--db",env["TELECOM_DB"],"--output",folder+"/analytics"],cwd=ROOT,check=True,capture_output=True)
                self.assertTrue(Path(folder,"analytics/volume.png").exists())
            finally:
                p.terminate()
                p.wait(timeout=10)
