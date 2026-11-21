"""Mede demora de resposta e sinais linguísticos em atendimentos públicos históricos."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

import pandas as pd

BRANDS = {"sprintcare", "TMobileHelp", "VerizonSupport", "ATTCares"}
PATTERNS = {
    "cobranca": r"\b(?:bill(?:ing)?|charged?|fees?|refund)\b",
    "conexao": r"\b(?:outage|network|signal|disconnected|no service|connection)\b",
    "cancelamento": r"\b(?:cancel(?:led|ing|lation)?|terminate|disconnect my)\b",
    "recorrencia": r"\b(?:still|again|third time|second time)\b",
}
SOURCE = "https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter"

def chunks(archive):
    with zipfile.ZipFile(archive) as zipped, zipped.open("twcs/twcs.csv") as raw:
        yield from pd.read_csv(raw, chunksize=100_000, usecols=["tweet_id","author_id","inbound","created_at","text","in_response_to_tweet_id"],
                               dtype={"tweet_id":"Int64","in_response_to_tweet_id":"Int64","author_id":"string"})

def analyze(archive, destination):
    output = Path(destination)
    output.mkdir(parents=True, exist_ok=True)
    n = 0
    replies = []
    for batch in chunks(archive):
        n += len(batch)
        select = (~batch.inbound) & batch.author_id.isin(BRANDS) & batch.in_response_to_tweet_id.notna()
        replies.append(batch.loc[select,["author_id","in_response_to_tweet_id","created_at"]])
    reply = pd.concat(replies,ignore_index=True).rename(columns={"author_id":"brand","in_response_to_tweet_id":"parent","created_at":"reply_at"})
    ids = set(reply.parent)
    inbound = []
    for batch in chunks(archive):
        subset = batch.loc[batch.inbound & batch.tweet_id.isin(ids),["tweet_id","text","created_at"]].copy()
        for name, pattern in PATTERNS.items():
            subset[name] = subset.text.str.contains(pattern,case=False,na=False,regex=True)
        inbound.append(subset.drop(columns="text"))
    customers = pd.concat(inbound,ignore_index=True).rename(columns={"tweet_id":"parent","created_at":"entry_at"})
    paired = reply.merge(customers,on="parent",validate="many_to_one")
    fmt = "%a %b %d %H:%M:%S %z %Y"
    for col in ("entry_at","reply_at"):
        paired[col] = pd.to_datetime(paired[col],format=fmt,utc=True,errors="coerce")
    paired["minutes"]=(paired.reply_at-paired.entry_at).dt.total_seconds()/60
    paired=paired.loc[paired.minutes.ge(0)].sort_values("minutes").drop_duplicates(["brand","parent"])
    if paired.empty:
        raise ValueError("Sem pares válidos para as marcas configuradas.")
    summary=paired.groupby("brand").agg(mensagens=("parent","size"),mediana_min=("minutes","median"),
                                        p90_min=("minutes",lambda s:s.quantile(.9)),**{k:(k,"sum") for k in PATTERNS})
    summary.to_csv(output/"por_marca.csv")
    with open(archive,"rb") as raw:
        origin_hash=hashlib.file_digest(raw,"sha256").hexdigest()
    observed={"origem":SOURCE,"licenca_fonte":"CC BY-NC-SA 4.0","linhas_lidas":n,"mensagens_pareadas":len(paired),
              "marcas_observadas":sorted(paired.brand.unique()),"mediana_minutos":float(paired.minutes.median()),
              "p90_minutos":float(paired.minutes.quantile(.9)),
              "sinais":{k:int(paired[k].sum()) for k in PATTERNS},
              "sha256_arquivo_origem":origin_hash}
    (output/"resultado.json").write_text(json.dumps(observed,ensure_ascii=False,indent=2),encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    axes=summary[["mediana_min","p90_min"]].rename(columns={"mediana_min":"Mediana","p90_min":"Percentil 90"}).plot.bar(color=["#087761","#d7a45d"],rot=12)
    axes.set_title("Tempo até a primeira resposta direta observada")
    axes.set_ylabel("Minutos"); axes.set_xlabel("Conta pública de suporte")
    axes.figure.tight_layout();axes.figure.savefig(output/"tempo_resposta.png",dpi=150);plt.close(axes.figure)
    return observed

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("arquivo",type=Path);p.add_argument("--output",type=Path,default=Path("reports/campo"))
    args=p.parse_args()
    print(json.dumps(analyze(args.arquivo,args.output),ensure_ascii=False,indent=2))
