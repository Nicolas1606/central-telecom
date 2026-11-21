"""Experimentos reproduzíveis com Ollama real. Cada braço tem pasta própria."""
import argparse
import copy
import hashlib
import json
import os
import platform
import sys
from datetime import datetime,timezone
from pathlib import Path

import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from central.engine import Engine
from central.provider import Ollama
from central.evaluation import evaluate,report

def plans():
    base=json.loads((ROOT/"config/agents.json").read_text(encoding="utf-8"))
    for role, cfg in base.items():
        cfg.update(model="qwen3:0.6b",think=False,temperature=0,max_tokens=96,threads=4)
    base["judge"].update(model="qwen3:1.7b",prompt_version="v2",max_tokens=128)
    revised=copy.deepcopy(base)
    revised["router"]["prompt_version"]="v3"
    improved=copy.deepcopy(revised)
    for role in ("cobranca","suporte","cancelamento"):
        improved[role]["source_selection"]="validated_top1"
    larger=copy.deepcopy(improved);larger["router"]["model"]="qwen3:1.7b"
    effort=copy.deepcopy(larger);effort["router"].update(think=True,max_tokens=192)
    warm=copy.deepcopy(improved);warm["router"]["temperature"]=0.7
    scoped=copy.deepcopy(revised)
    scoped["router"]["routing"]="anchored"
    for role in ("cobranca","suporte","cancelamento"):
        scoped[role].update(tool_protocol="plan",prompt_version="v2")
    lean=copy.deepcopy(scoped)
    for role in ("cobranca","suporte","cancelamento"):
        lean[role]["source_selection"]="validated_top1"
    bounded=copy.deepcopy(lean)
    bounded["router"]["routing"]="scope_gate"
    return {"escopo":("multi",bounded),"estruturado":("multi",scoped),"enxuto":("multi",lean),
        "single":("single",base),"multi":("multi",base),"prompt":("multi",revised),
        "economico":("multi",improved),"maior":("multi",larger),
        "esforco":("multi",effort),"temperatura":("multi",warm)}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--cases",type=Path,default=ROOT/"evaluation/paired.json")
    parser.add_argument("--arms",nargs="+",choices=list(plans()),default=list(plans()))
    parser.add_argument("--repeat",type=int,default=1)
    parser.add_argument("--judge",action="store_true")
    args=parser.parse_args()
    if not 1<=args.repeat<=20: parser.error("Repetições entre 1 e 20.")
    cases=json.loads(args.cases.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True,exist_ok=False)
    llm=Ollama()
    with httpx.Client(trust_env=False,timeout=10) as client:
        models=client.get(llm.url+"/api/tags");models.raise_for_status()
        version=client.get(llm.url+"/api/version");version.raise_for_status()
    records={x["name"]:x["digest"] for x in models.json()["models"]}
    arms=plans()
    required={v["model"] for a in args.arms for v in arms[a][1].values()}
    if missing:=required-set(records): raise SystemExit("Baixe no Ollama: "+", ".join(sorted(missing)))
    meta={"runtime":version.json(),"pesos":{k:records[k] for k in sorted(required)},"python":platform.python_version(),
          "plataforma":platform.system()+" "+platform.machine(),"data_utc":datetime.now(timezone.utc).isoformat(),
          "modo":"ollama","executor":os.getenv("ORCHESTRATOR","nativo"),"ordem":args.arms,
          "repeticoes":args.repeat,"juiz":args.judge}
    (args.output/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    for arm in args.arms:
        design,conf=arms[arm]
        engine=Engine("ollama",design)
        engine.llm.config=copy.deepcopy(conf)
        path,metrics=evaluate(engine,cases,args.repeat,args.judge,args.output/arm)
        report(path)
        print(arm,metrics["por_grupo"],metrics["operacao_no_replay"]["chamadas_llm"],flush=True)

if __name__=="__main__":
    main()
