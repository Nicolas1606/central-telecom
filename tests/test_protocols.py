"""Exercita HTTP nativo do provedor com um servidor de contrato e MCP real via stdio."""
import asyncio
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
from central.engine import Engine
from central.knowledge import ROOT
from central.provider import Ollama, Verdict, user, Unavailable

class Stub(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass
    def do_POST(self):
        data=json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(data)
        reply=self.server.replies.pop(0)
        body=json.dumps({"message":reply,"prompt_eval_count":18,"eval_count":5}).encode()
        self.send_response(200); self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)

class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Stub)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.server.requests=[]
        self.server.replies=[]
        self.llm=Ollama()
        self.llm.url="http://127.0.0.1:"+str(self.server.server_port)
        self.engine=Engine("ollama",llm=self.llm)
        self.state={"account":"A","last":""}

    def setup_replies(self,tool="invoice",arguments=None,source="FAT-01"):
        self.server.replies=[{"content":'{"domains":["cobranca"]}'},
             {"content":"","tool_calls":[{"function":{"name":tool,"arguments":arguments or {}}}]},
             {"content":json.dumps({"source_id":source})}]

    def test_real_http_contract(self):
        self.setup_replies()
        r=self.engine.turn("Quanto deu a fatura?",self.state)
        self.assertEqual(r["action"],"answer")
        self.assertEqual(r["sources"][0]["id"],"FAT-01")
        self.assertEqual([s["tokens_out"] for s in r["trace"] if "model" in s],[5,5,5])
        q=self.server.requests
        self.assertEqual(q[1]["tools"][0]["function"]["name"],"invoice")
        self.assertEqual(q[2]["messages"][-2]["role"],"tool")
        self.assertTrue(all(d["stream"] is False for d in q))

    def test_tool_cannot_choose_account(self):
        self.setup_replies(arguments={"account":"B"})
        self.assertEqual(self.engine.turn("fatura",self.state)["reason"],"falha_validacao")

    def test_unlisted_tool(self):
        self.setup_replies(tool="eligibility")
        self.assertEqual(self.engine.turn("fatura",self.state)["action"],"handoff")

    def test_fabricated_citation(self):
        self.setup_replies(source="FAT-99")
        self.assertEqual(self.engine.turn("fatura",self.state)["reason"],"falha_validacao")

    def test_malformed_router(self):
        self.server.replies=[{"content":'{"domains":["alien"]}'}]
        self.assertEqual(self.engine.turn("oi",self.state)["action"],"handoff")

    def test_judge_schema(self):
        self.server.replies=[{"content":'{"verdict":"fail","reason":"Informação divergente da fatura."}'}]
        v=self.llm.chat("judge",[user({"tarefa":"rubrica"})],[],contract=Verdict)
        self.assertEqual(v.verdict,"fail")

    def test_explicit_exit_survives_wrong_model_route(self):
        self.server.replies=[{"content":'{"domains":["cobranca"]}'}]
        response=self.engine.turn("Encerre meu contrato",self.state)
        self.assertEqual(response["reason"],"encerramento")
        self.assertEqual(len(self.server.requests),1)

    def test_commercial_consent_never_generic_yes(self):
        self.server.replies=[{"content":'{"domains":["esclarecer"]}'}]
        self.assertNotEqual(self.engine.turn("sim",{**self.state,"pending":True})["action"],"converted")

    def test_duplicate_route(self):
        self.server.replies=[{"content":'{"domains":["cobranca","cobranca"]}'}]
        self.assertEqual(self.engine.turn("fatura",self.state)["reason"],"falha_validacao")

class MCPTests(unittest.TestCase):
    def test_stdio_search(self):
        async def check():
            params=StdioServerParameters(command=sys.executable,args=["-m","central.mcp_server"],cwd=str(ROOT))
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as client:
                    await client.initialize()
                    self.assertEqual([x.name for x in (await client.list_tools()).tools],["buscar_politica"])
                    answer=await client.call_tool("buscar_politica",{"pergunta":"contestação de lançamento"})
                    self.assertFalse(answer.isError)
                    self.assertIn("FAT-02"," ".join(block.text for block in answer.content))
        asyncio.run(check())
