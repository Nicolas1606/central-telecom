"""Replay público reproduzível. Fixtures separadas do motor, resultados atômicos por execução."""
from pathlib import Path
import hashlib
import json
import platform
import tempfile
import uuid
from datetime import datetime, timezone
import pandas as pd
from .knowledge import ROOT
from .engine import Engine
from .storage import Store, Conflict
from .provider import Verdict, Unavailable, user
from .tools import ACCOUNTS
from .release import fingerprint

def equal(actual,gold):
    return (actual["action"]==gold["action"] and actual["domains"]==gold["domains"] and
            set(s["id"] for s in actual["sources"])==set(gold["sources"]) and
            all(s.casefold() in actual["message"].casefold() for s in gold["contains"]) and
            (not gold.get("reason") or actual["reason"]==gold["reason"]))

def metrics(rows):
    return {"turnos":len(rows),"corretos":sum(r["ok"] for r in rows),
            "acerto_turnos":sum(r["ok"] for r in rows)/len(rows) if rows else None,
            "acerto_acao":sum(r["expected"]==r["actual"] for r in rows)/len(rows) if rows else None,
            "aceites_indevidos_observados":sum(r["actual"]=="converted" and r["expected"]!="converted" for r in rows),
            "casos":len(set(r["run_case"] for r in rows)),
            "casos_integrais":sum(all(x["ok"] for x in rows if x["run_case"]==k) for k in set(r["run_case"] for r in rows))}

def evaluate(engine,cases,repeats=1,judge=False,base=None):
    run = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+"-"+engine.mode+"-"+engine.design
    out = Path(base or ROOT/"reports"/"runs")/run
    out.mkdir(parents=True)
    rows,outputs = [],[]
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp)/"evaluation.db")
        for rep in range(repeats):
            for case in cases:
                sid = store.new(case["account"],engine)
                revision = 0
                for i,g in enumerate(case["turns"]):
                    try:
                        answer = store.chat(sid,str(uuid.uuid4()),g["text"],engine,revision)
                        revision = answer["revision"]
                    except Conflict:
                        answer = {"action":"blocked","reason":"sessao_encerrada","domains":[],"sources":[],"message":"","trace":[],"latency_ms":None}
                    row = {"run_case":f"{rep+1}-{case['id']}","case":case["id"],"turn":i+1,"split":case["split"],
                           "expected":g["action"],"actual":answer["action"],"reason":answer["reason"],
                           "ok":bool(equal(answer,g)),"latency_ms":answer["latency_ms"],"judge":None}
                    if judge:
                        trace = []
                        try:
                            v = engine.llm.chat("judge",[user({"tarefa":g["text"],"referencia":g,
                                "perfil_ficticio":ACCOUNTS[case["account"]],"resposta":answer["message"],
                                "fontes":answer["sources"],"acao":answer["action"]})],trace,contract=Verdict)
                            row["judge"],row["judge_reason"] = v.verdict,v.reason
                        except Unavailable:
                            row["judge"] = "unavailable"
                        row["judge_trace"] = trace
                    rows.append(row)
                    outputs.append({"caso":case["id"],"turno":i+1,"repeticao":rep+1,"pergunta":g["text"],**answer})
        summary = {"tipo":"replay público sintético","modo":engine.mode,"arquitetura":engine.design,"repeticoes":repeats,
                   "python":platform.python_version(),"config":engine.llm.config,"release_sha256":fingerprint(engine.llm.config),"por_grupo":{k:metrics([r for r in rows if r["split"]==k]) for k in sorted(set(r["split"] for r in rows))},
                   "operacao_no_replay":store.metrics()}
    (out/"rubrica.json").write_text(json.dumps([{"id":c["id"],"account":c["account"]} for c in cases],ensure_ascii=False),encoding="utf-8")
    # Busca medida apenas com a pergunta, sem o domínio nem a política conhecidos pelo motor.
    search = []
    for case in cases:
        for g in case["turns"]:
            needed = set(g["sources"])
            if not needed: continue
            for mode in ["lexical","semantic","hybrid"]:
                hits = [x["id"] for x in engine.index.search(g["text"],mode=mode)]
                search.append({"caso":case["id"],"split":case["split"],"metodo":mode,
                               "recall_at_3":len(needed.intersection(hits))/len(needed),"ids":" ".join(hits)})
    summary["recall_at_3"] = pd.DataFrame(search).groupby("metodo").recall_at_3.mean().to_dict() if search else {}
    summary["variacao_de_acao"] = sum(len({r["actual"] for r in rows if (r["case"],r["turn"])==k})>1 for k in {(r["case"],r["turn"]) for r in rows}) if repeats>1 else None
    data=json.dumps(cases,ensure_ascii=False,sort_keys=True).encode()
    summary["casos_sha256"]=hashlib.sha256(data).hexdigest()
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"traces.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in outputs),encoding="utf-8")
    pd.DataFrame(rows).to_csv(out/"turns.csv",index=False)
    pd.DataFrame(search).to_csv(out/"retrieval.csv",index=False)
    pd.DataFrame([{"case":r["case"],"turn":r["turn"],"run_case":r["run_case"],"human_grade":"","critical_error":"","reviewer":"","observacao":""} for r in rows]).to_csv(out/"human_review.csv",index=False)
    return out,summary

def report(run):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    run = Path(run)
    df = pd.read_csv(run/"turns.csv")
    table = pd.crosstab(df["expected"],df["actual"])
    table.to_csv(run/"confusao.csv")
    figures,axes=plt.subplots(1,2,figsize=(10,4.5))
    ax=axes[0]
    ax.imshow(table,cmap="GnBu")
    ax.set_xticks(range(len(table.columns)),table.columns,rotation=35,ha="right")
    ax.set_yticks(range(len(table.index)),table.index)
    for i in range(len(table.index)):
        for j in range(len(table.columns)):
            ax.text(j,i,str(table.iloc[i,j]),ha="center",va="center",bbox={"facecolor":"white","alpha":0.8,"edgecolor":"none"})
    ax.set_title("Ação esperada × observada")
    df.groupby("split").ok.mean().plot.bar(ax=axes[1],color="#087866",ylim=(0,1.13),rot=0)
    axes[1].set_title("Proporção de turnos corretos"); axes[1].set_xlabel("")
    figures.tight_layout(); figures.savefig(run/"avaliacao.png",dpi=150); plt.close(figures)
    errors=df.loc[~df.ok,["case","turn","expected","actual","reason"]]
    errors.to_csv(run/"falhas.csv",index=False)

def calibrate(run):
    run=Path(run)
    df=pd.read_csv(run/"turns.csv").merge(pd.read_csv(run/"human_review.csv"),on=["run_case","case","turn"],validate="one_to_one")
    reviewed=df[df.human_grade.isin(["pass","fail"]) & df.judge.isin(["pass","fail"])]
    if reviewed.empty:
        return {"status":"pendente","pares":0}
    return {"status":"calibracao_parcial" if len(reviewed)<len(df) else "calibrado_na_amostra",
            "pares":len(reviewed),"concordancia":float((reviewed.human_grade==reviewed.judge).mean()),
            "falsas_aprovacoes":int(((reviewed.judge=="pass") & (reviewed.human_grade=="fail")).sum())}
