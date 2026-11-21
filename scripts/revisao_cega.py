"""Prepare respostas para avaliação independente e importe as notas após a revisão."""
import argparse
import csv
import json
import os
from pathlib import Path
import secrets

KEY = ["run_case", "case", "turn"]
GRADES = ["human_grade", "critical_error", "reviewer", "observacao"]


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, columns, records):
    with path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)


def prepare(run, dest):
    traces = [json.loads(line) for line in (run / "traces.jsonl").read_text(encoding="utf-8").splitlines()]
    secrets.SystemRandom().shuffle(traces)
    dest.mkdir(parents=True, exist_ok=False)
    accounts = {}
    for entry in json.loads((run / "rubrica.json").read_text(encoding="utf-8")) if (run / "rubrica.json").exists() else []:
        accounts[entry["id"]] = entry["account"]
    from itertools import groupby
    previous = {}
    for _, conversation in groupby(sorted(traces, key=lambda x: (x["caso"],x["repeticao"],x["turno"])), key=lambda x: (x["caso"],x["repeticao"])):
        history = []
        for entry in conversation:
            previous[(entry["caso"],entry["repeticao"],entry["turno"])] = list(history)
            history.append([entry["pergunta"],entry["message"]])
    packets, mapping = [], []
    for entry in traces:
        code = secrets.token_hex(8)
        case, rep, turn = entry["caso"], entry["repeticao"], entry["turno"]
        packets.append({"item": code, "perfil":accounts.get(case,"consultar ficha da tarefa"),
                        "historico":json.dumps(previous[(case,rep,turn)],ensure_ascii=False),
                        "pergunta":entry["pergunta"], "resposta":entry["message"],
                        "fontes":json.dumps([s["text"] for s in entry["sources"]],ensure_ascii=False)})
        mapping.append(dict(item=code,run_case=f"{rep}-{case}",case=case,turn=turn))
    write(dest/"para_revisor.csv",["item","perfil","historico","pergunta","resposta","fontes",*GRADES],packets)
    write(dest/"chave_do_coordenador.csv",["item",*KEY],mapping)


def receive(run, dest):
    key = rows(dest/"chave_do_coordenador.csv")
    grades = rows(dest/"para_revisor.csv")
    indexed = {r["item"]:r for r in grades}
    if len(indexed)!=len(grades) or len(key)!=len(indexed) or set(indexed)!={r["item"] for r in key}:
        raise ValueError("Itens duplicados, desconhecidos ou ausentes.")
    records = []
    for item in key:
        g = indexed[item["item"]]
        if g["human_grade"] not in {"pass","fail"} or g["critical_error"] not in {"true","false"} or not g["reviewer"].strip():
            raise ValueError("Cada item exige nota, indicação de erro crítico e pseudônimo.")
        records.append({**{k:item[k] for k in KEY},**{k:g[k] for k in GRADES}})
    existing = rows(run/"human_review.csv")
    if any(row["human_grade"] for row in existing):
        raise ValueError("A execução já contém notas. Preserve o registro original.")
    if sorted(tuple(r[k] for k in KEY) for r in records)!=sorted(tuple(r[k] for k in KEY) for r in existing):
        raise ValueError("A chave pertence a outra execução.")
    tmp=run/("human_review."+secrets.token_hex(8)+".tmp")
    write(tmp,KEY+GRADES,records)
    os.replace(tmp,run/"human_review.csv")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao",choices=["preparar","importar"]); parser.add_argument("run",type=Path); parser.add_argument("pasta",type=Path)
    args=parser.parse_args()
    (prepare if args.acao=="preparar" else receive)(args.run,args.pasta)
