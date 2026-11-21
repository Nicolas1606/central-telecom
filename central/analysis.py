"""Análise de dados de conhecimento e de conversas com pandas."""
import json
from pathlib import Path
import sqlite3
import pandas as pd
from .knowledge import ROOT,Index
from .tools import ACCOUNTS

def profile():
    knowledge=Index()
    frames=pd.DataFrame(knowledge.docs.values())
    cases=json.loads((ROOT/"evaluation/cases.json").read_text(encoding="utf-8"))
    turns=[(c,g) for c in cases for g in c["turns"]]
    assert len(set(c["id"] for c in cases))==len(cases)
    assert all(c["account"] in ACCOUNTS for c in cases)
    assert all(set(g["sources"])<=set(knowledge.docs) for c,g in turns)
    assert all(a["base"]>=0 and a["extra"]>=0 for a in ACCOUNTS.values())
    profile={"contas_ficticias":len(ACCOUNTS),"fontes":len(frames),"hashes_distintos":int(frames.sha256.nunique()),
             "campos_nulos":int(frames.isna().sum().sum()),"turnos":len(turns),
             "casos_por_grupo":pd.Series([c["split"] for c in cases]).value_counts().to_dict(),
             "acoes_esperadas":pd.Series([g["action"] for c,g in turns]).value_counts().to_dict(),
             "comprimento_mediano_pergunta":float(pd.Series([len(g["text"]) for c,g in turns]).median())}
    public = pd.read_csv(ROOT/"data/anatel_reclamacoes.csv")
    categories = ["cobranca","qualidade_funcionamento_reparo","cancelamento"]
    public["fracao_dos_tres_assuntos"] = public[categories].sum(axis=1) / public.total
    profile["anatel_por_ano"] = public.to_dict(orient="records")
    dest=ROOT/"reports/data_profile.json"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding="utf-8")
    return dest

def analyze(db,output=None):
    from .storage import Store
    if not Path(db).exists():
        raise ValueError("Nenhuma instalação nesse caminho. Abra o chat primeiro.")
    out=Path(output or ROOT/"runtime/analytics");out.mkdir(parents=True,exist_ok=True)
    store=Store(db)
    with store.db() as con:
        events=pd.read_sql_query("SELECT ts,payload FROM turns ORDER BY ts",con)
    if events.empty:
        return "Nenhum turno registrado."
    rows=[]
    for event in events.itertuples():
        data=json.loads(event.payload)
        rows.append({"dia":pd.to_datetime(event.ts,unit="s",utc=True).date(),"acao":data["action"],
                     "motivo":data["reason"],"ms":data["latency_ms"],"dominio":"+".join(data["domains"]) or "controle"})
    df=pd.DataFrame(rows)
    df.groupby(["dia","dominio","acao","motivo"]).agg(turnos=("ms","size"),mediana_ms=("ms","median")).to_csv(out/"operacao.csv")
    (out/"indicadores.json").write_text(json.dumps(store.metrics(),ensure_ascii=False,indent=2),encoding="utf-8")
    from matplotlib import use
    use("Agg")
    import matplotlib.pyplot as plt
    ax=df.groupby(["dia","acao"]).size().unstack(fill_value=0).plot.bar(stacked=True,figsize=(8,4),rot=0)
    ax.set_ylabel("Turnos registrados"); ax.set_xlabel("Data UTC")
    ax.figure.tight_layout(); ax.figure.savefig(out/"volume.png",dpi=150); plt.close(ax.figure)
    return out
