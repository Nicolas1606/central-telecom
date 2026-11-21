import csv
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from central.engine import Engine
from central.knowledge import ROOT
from central.provider import ToolPlan
from central.web import create_app
from scripts.benchmark import plans
from scripts.revisao_cega import prepare, receive, rows
from scripts.finops import summarize

class CandidateTests(unittest.TestCase):
    def test_no_contract_for_unrelated_question(self):
        engine=Engine("ollama")
        engine.llm.config=plans()["escopo"][1]
        with patch.object(engine.llm,"chat",side_effect=AssertionError("Não chamar modelo para assunto externo")):
            result=engine.turn("O que fazer com o passaporte?",{"account":"A"})
        self.assertEqual(result["reason"],"fora_escopo")

    def test_validate_plan_before_tool(self):
        engine=Engine("ollama")
        engine.llm.config=plans()["escopo"][1]
        with patch.object(engine.llm,"chat",return_value=ToolPlan(name="eligibility")):
            result=engine.turn("Quero ver minha fatura",{"account":"A"})
        self.assertEqual(result["reason"],"falha_validacao")
        self.assertFalse(any("tool" in x for x in result["trace"]))

    def test_operator_queue_protected(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"TELECOM_ENV":"pilot","TELECOM_OPERATOR_TOKEN":"a"*32}):
            client=TestClient(create_app(Path(temp)/"demo.db"))
            for route in ("/api/tickets","/api/metrics"):
                self.assertEqual(client.get(route).status_code,401)
                self.assertEqual(client.get(route,headers={"Authorization":"Bearer "+"a"*32}).status_code,200)

    def test_reject_weak_operator_secret_for_pilot(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ,{"TELECOM_ENV":"pilot","TELECOM_OPERATOR_TOKEN":"curto"}):
            with self.assertRaises(ValueError):
                create_app(Path(temp)/"demo.db")

    def test_config_matches_experiment(self):
        self.assertEqual(json.loads((ROOT/"config/piloto.json").read_text()),plans()["escopo"][1])

    def test_blind_review_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            dest=root/"revisao"
            row={"caso":"TEST","turno":1,"repeticao":1,"pergunta":"Fatura?","message":"R$ 94,00","sources":[]}
            (root/"traces.jsonl").write_text(json.dumps(row))
            (root/"human_review.csv").write_text("run_case,case,turn,human_grade,critical_error,reviewer,observacao\n1-TEST,TEST,1,,,,\n")
            prepare(root,dest)
            results=rows(dest/"para_revisor.csv")
            self.assertFalse({"judge","ok","expected","case","run_case","latency_ms"}.intersection(results[0]))
            with self.assertRaises(ValueError):
                receive(root,dest)
            results[0].update(human_grade="pass",critical_error="false",reviewer="R01")
            with (dest/"para_revisor.csv").open("w",newline="",encoding="utf-8") as stream:
                writer=csv.DictWriter(stream,fieldnames=list(results[0]))
                writer.writeheader(); writer.writerows(results)
            receive(root,dest)
            self.assertEqual(rows(root/"human_review.csv")[0]["reviewer"],"R01")

    def test_unknown_cost_stays_missing(self):
        frame=summarize([ROOT/"reports/validacao_llm"],1,3)
        self.assertTrue(frame.loc[frame.braco=="esforco","custo_cenario_usd_por_conversa"].isna().all())
