import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from central.comparison import compare
from central.engine import Engine
from central.evaluation import evaluate,calibrate
from central.knowledge import ROOT
from central.release import assess

class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.engine=Engine()
        self.cases=json.loads((ROOT/"evaluation/cases.json").read_text(encoding="utf-8"))[:1]

    def test_repeated_run_and_ungraded_release(self):
        run,metrics=evaluate(self.engine,self.cases,2,base=self.tmp.name)
        self.assertEqual(metrics["por_grupo"]["dev"]["turnos"],4)
        self.assertEqual(metrics["variacao_de_acao"],0)
        self.assertEqual(calibrate(run)["pares"],0)
        decision=assess(run,self.engine.llm.config)
        self.assertFalse(decision["promover"])
        self.assertTrue(decision["criterios"]["mesmo_candidato"])
        self.assertFalse(decision["criterios"]["modelo_real"])
        self.assertEqual(compare(run,run)["piorou"],0)

    def test_reject_mismatched_experiments(self):
        first,_=evaluate(self.engine,self.cases,base=self.tmp.name)
        second,_=evaluate(self.engine,self.cases,2,base=self.tmp.name)
        with self.assertRaises(ValueError):
            compare(first,second)

    def test_judge_calibration_detects_false_approval(self):
        run,_=evaluate(self.engine,self.cases,base=self.tmp.name)
        turns=pd.read_csv(run/"turns.csv");turns["judge"]=["pass","fail"]
        turns.to_csv(run/"turns.csv",index=False)
        humans=pd.read_csv(run/"human_review.csv");humans["human_grade"]=["fail","fail"]
        humans.to_csv(run/"human_review.csv",index=False)
        c=calibrate(run)
        self.assertEqual(c["falsas_aprovacoes"],1)
        self.assertEqual(c["concordancia"],0.5)
