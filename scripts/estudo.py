"""Mede tempo e correção pareados. As notas vêm da pessoa que revisou as entregas."""
import argparse
import csv
import json
import math
from pathlib import Path
from statistics import median

FIELDS=["participante","familia","condicao","variante","ordem","segundos","correto","critico","revisor"]

def create(path):
    with path.open("x",encoding="utf-8-sig",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=FIELDS)
        w.writeheader()
        for i in range(5):
            for j,family in enumerate(("cobranca","suporte")):
                order=["manual","assistida"] if (i+j)%2==0 else ["assistida","manual"]
                for n,condition in enumerate(order):
                    w.writerow(dict(participante=f"P{i+1:02}",familia=family,condicao=condition,
                                    variante=["A","B"][(i+n)%2],ordem=n+1))

def analyze(path):
    with path.open(encoding="utf-8-sig",newline="") as fp:
        records=list(csv.DictReader(fp))
    pairs={}
    for r in records:
        pair=pairs.setdefault((r["participante"],r["familia"]),{})
        cond=r["condicao"]
        if cond not in {"manual","assistida"} or cond in pair:
            raise ValueError("Condição repetida ou inválida.")
        pair[cond]=r
    changes=[]
    counts={"manual":0,"assistida":0}
    critical=0
    people=set()
    for (person,_),pair in pairs.items():
        if len(pair)!=2 or any(not all(r[k].strip() for k in FIELDS) for r in pair.values()):
            continue
        if {r["ordem"] for r in pair.values()}!={"1","2"} or len({r["variante"] for r in pair.values()})!=2:
            raise ValueError("Use ordens e variantes diferentes no mesmo par.")
        durations={}
        for cond,r in pair.items():
            sec=float(r["segundos"])
            if not math.isfinite(sec) or sec<=0 or r["correto"] not in {"0","1"} or r["critico"] not in {"0","1"}:
                raise ValueError("Segundos positivos e notas 0 ou 1 são obrigatórios.")
            counts[cond]+=int(r["correto"]);durations[cond]=sec
        critical+=int(pair["assistida"]["critico"])
        changes.append(100*(1-durations["assistida"]/durations["manual"]))
        people.add(person)
    gain=median(changes) if changes else None
    sufficient=len(changes)>=10 and len(people)>=5 and len(changes)==len(pairs)
    return {"pares_previstos":len(pairs),"pares_completos":len(changes),"participantes_com_pares":len(people),
            "pendentes":len(pairs)-len(changes),"acertos":counts,"criticos_assistida":critical,"ganho_mediano_pct":gain,
            "criterio_exploratorio":("atingido" if gain>=20 and counts["assistida"]>=counts["manual"] and not critical else "abaixo_da_meta") if sufficient else "pendente"}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("acao",choices=["preparar","medir"]);p.add_argument("csv",type=Path)
    a=p.parse_args()
    if a.acao=="preparar": create(a.csv)
    else: print(json.dumps(analyze(a.csv),indent=2,ensure_ascii=False))
