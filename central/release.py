"""Verificação reprodutível para promoção de um candidato Ollama."""
import hashlib
import json
from pathlib import Path
import pandas as pd
from .knowledge import ROOT

def fingerprint(config):
    sha=hashlib.sha256(json.dumps(config,sort_keys=True).encode())
    inputs=[ROOT/"data/accounts.json",*sorted((ROOT/"knowledge").glob("*.md")),
            *sorted((ROOT/"prompts").glob("*.txt")),*sorted((ROOT/"central").glob("*.py"))]
    for path in inputs:
        sha.update(path.relative_to(ROOT).as_posix().encode())
        sha.update(path.read_text(encoding="utf-8").encode())
    return sha.hexdigest()

def assess(run,config):
    path=Path(run)
    s=json.loads((path/"summary.json").read_text(encoding="utf-8"))
    turns=pd.read_csv(path/"turns.csv")
    grades=pd.read_csv(path/"human_review.csv")
    keys=["run_case","case","turn"]
    reviewed=turns.merge(grades,on=keys,how="left",validate="one_to_one")
    verdict=reviewed.human_grade.isin(["pass","fail"])
    critical=reviewed["critical_error"].astype(str).str.lower() if "critical_error" in reviewed else pd.Series("",index=reviewed.index)
    reviewers=reviewed["reviewer"].fillna("").str.strip() if "reviewer" in reviewed else pd.Series("",index=reviewed.index)
    op=s["operacao_no_replay"]
    checks={
        "modelo_real":s["modo"]=="ollama" and op["chamadas_llm"]>0 and bool(op["tokens_saida"]),
        "mesmo_candidato":s.get("release_sha256")==fingerprint(config),
        "amostra_privada_declarada":set(turns.split)=={"private"},
        "cobertura_minima":turns["case"].nunique()>=20 and {"answer","clarify","handoff"}.issubset(set(turns.expected)),
        "triagem":float((turns.expected==turns.actual).mean())>=0.90,
        "contratos_e_fatos":float(turns.ok.mean())>=0.95,
        "revisao_identificada":bool(verdict.all() and reviewers.ne("").all()),
        "qualidade_humana":float((reviewed.human_grade=="pass").mean())>=0.95,
        "erros_criticos_revisados":bool(critical.isin(["false","0"]).all()),
        "aceites_com_consentimento":not bool(((turns.actual=="converted") & (turns.expected!="converted")).any()),
        "juiz_disponivel":bool(reviewed.judge.isin(["pass","fail"]).all()),
        "orcamento_de_inferencia_conhecido":op["custo_inferencia_usd_por_conversa"] is not None,
        "latencia":op["p95_ms"] is not None and op["p95_ms"]<=10000}
    return {"promover":all(checks.values()),"criterios":checks,
            "nota":"A independência do revisor e a origem das perguntas precisam ser verificadas pelo responsável pelo piloto."}
