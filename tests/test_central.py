import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from central.engine import Engine
from central.knowledge import ROOT,Index
from central.provider import Ollama
from central.storage import Store,Conflict
from central.web import create_app

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/"test.db"
        self.store=Store(self.db)
        self.engine=Engine()
        self.sid=self.store.new("A",self.engine)

    def chat(self,text,rev=0):
        return self.store.chat(self.sid,str(uuid.uuid4()),text,self.engine,rev)

    def test_public_development(self):
        from central.evaluation import equal
        for c in json.loads((ROOT/"evaluation/cases.json").read_text(encoding="utf-8")):
            if c["split"]!="dev": continue
            sid=self.store.new(c["account"],self.engine)
            for rev,g in enumerate(c["turns"]):
                with self.subTest(caso=c["id"],turno=rev):
                    self.assertTrue(equal(self.store.chat(sid,str(uuid.uuid4()),g["text"],self.engine,rev),g))

    def test_retry_and_persistence(self):
        key=str(uuid.uuid4())
        a=self.store.chat(self.sid,key,"Quero um atendente",self.engine,0)
        b=Store(self.db).chat(self.sid,key,"Quero um atendente",self.engine,0)
        self.assertEqual(a,b)
        self.assertEqual(len(self.store.tickets()),1)
        with self.assertRaises(Conflict):
            self.store.chat(self.sid,key,"Outra mensagem",self.engine,0)
        with self.assertRaises(Conflict):
            self.chat("oi",1)

    def test_concurrent_confirmations(self):
        self.chat("Existe desconto?")
        def confirm(_):
            try: return self.chat("Aceito a oferta",1)["action"]
            except Conflict: return "conflict"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(pool.map(confirm,range(2)),["converted","conflict"])
        m=self.store.metrics()
        self.assertEqual((m["aceites"],m["ofertas"],m["conversao"]),(1,1,1))

    def test_stale_offer(self):
        self.chat("Tem desconto?")
        self.chat("Quanto deu a fatura?",1)
        self.assertEqual(self.chat("Aceito a oferta",2)["reason"],"sem_proposta")

    def test_customer_requests_cancel_after_offer(self):
        self.chat("Quero uma alternativa")
        out=self.chat("Quero cancelar agora",1)
        self.assertEqual(out["reason"],"encerramento")
        self.assertIn("R$ 10,00",self.store.tickets()[0]["summary"]["historico"][0]["orientacao"])
        self.assertEqual(self.store.metrics()["aceites"],0)

    def test_case_does_not_open_business_ticket_on_question_only(self):
        self.chat("Se isso continuar quero cancelar")
        self.assertEqual(self.store.tickets(),[])

    def test_empty_metrics(self):
        self.assertIsNone(self.store.metrics()["conversao"])
        self.assertEqual(self.store.metrics()["conversas"],0)

    def test_negative_handoff(self):
        self.assertEqual(self.chat("Não quero falar com um atendente, qual o valor da fatura?")["action"],"answer")

    def test_ambiguous_value(self):
        self.assertEqual(self.chat("O valor de sempre mudou, de onde veio a diferença?")["action"],"clarify")

    def test_priority_over_offer(self):
        response=self.chat("Não reconheço a cobrança e queria ver um desconto.")
        self.assertEqual(response["action"],"handoff")
        self.assertNotIn("ACEITO A OFERTA",response["message"])

    def test_ticket_review(self):
        tid=self.chat("Quero falar com atendente")["ticket"]
        self.store.close(tid)
        self.assertEqual(self.store.tickets()[0]["status"],"revisado")

    def test_private_question_not_logged(self):
        self.chat("CPF 00000000000")
        with self.store.db() as db:
            text=str(tuple(db.execute("SELECT * FROM turns").fetchone()))
        self.assertNotIn("00000000000",text)

    def test_http(self):
        with TestClient(create_app(self.db,self.engine)) as c:
            self.assertEqual(c.get("/health").json()["mode"],"demo")
            self.assertIn("Central Telecom",c.get("/").text)
            sid=c.post("/api/sessions",json={"account":"B"}).json()["id"]
            for question in [" ","X"*1001]:
                self.assertEqual(c.post(f"/api/sessions/{sid}/turn",json={"revision":0,"key":str(uuid.uuid4()),"text":question}).status_code,422)
            out=c.post(f"/api/sessions/{sid}/turn",json={"revision":0,"key":str(uuid.uuid4()),"text":"A rede caiu"}).json()
            self.assertIn("NET-08",out["message"])
            self.assertEqual(c.get("/api/metrics").json()["conversas"],1)
            self.assertEqual(c.post("/api/sessions",json={},headers={"Origin":"https://other.example"}).status_code,403)

    def test_index(self):
        for mode in ("lexical","semantic","hybrid"):
            self.assertEqual(self.engine.index.search("xyzzzz",mode=mode),[])
            hits=self.engine.index.search("contestação de lançamento","cobranca",mode)
            self.assertEqual(hits[0]["id"],"FAT-02")
        self.assertEqual(len(self.engine.index.docs),6)
