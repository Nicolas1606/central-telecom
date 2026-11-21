"""Comparação pareada de arquiteturas em exatamente os mesmos casos e repetições."""
from pathlib import Path
import json
import pandas as pd

def compare(left,right):
    roots=[Path(left),Path(right)]
    a,b=[json.loads((p/"summary.json").read_text(encoding="utf-8")) for p in roots]
    if a["casos_sha256"]!=b["casos_sha256"] or a["repeticoes"]!=b["repeticoes"]:
        raise ValueError("Escolha execuções com os mesmos casos e repetições.")
    frames=[pd.read_csv(p/"turns.csv").set_index(["run_case","turn"]).sort_index() for p in roots]
    if not frames[0].index.equals(frames[1].index):
        raise ValueError("Turnos incompatíveis.")
    x,y=frames
    stats=[]
    for s,df in zip((a,b),frames):
        op=s["operacao_no_replay"]
        stats.append({"modo":s["modo"],"arquitetura":s["arquitetura"],"qualidade":float(df.ok.mean()),
                      "p95_ms":op["p95_ms"],"tokens_entrada":op["tokens_entrada"],"tokens_saida":op["tokens_saida"],
                      "custo_usd_conversa":op["custo_inferencia_usd_por_conversa"]})
    return {"primeira":stats[0],"segunda":stats[1],"melhorou":int((~x.ok & y.ok).sum()),"piorou":int((x.ok & ~y.ok).sum())}
