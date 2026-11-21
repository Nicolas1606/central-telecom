"""Compare os replays pareados e aplique tarifas fornecidas pelo avaliador."""
import argparse
import json
from pathlib import Path

import pandas as pd


def summarize(roots, entrada, saida):
    if any(rate < 0 for rate in (entrada,saida)):
        raise ValueError("Tarifas precisam ser não negativas.")
    result = []
    signatures = set()
    for root in roots:
        for path in sorted(root.glob("*/*/summary.json")):
            data=json.loads(path.read_text(encoding="utf-8"))
            signatures.add((data["casos_sha256"],data["repeticoes"]))
            op=data["operacao_no_replay"]
            observations = pd.read_csv(path.parent/"turns.csv")
            tokens_in,tokens_out = op["tokens_entrada"],op["tokens_saida"]
            cost = None
            if tokens_in is not None and tokens_out is not None and op["conversas"]:
                cost=(tokens_in*entrada+tokens_out*saida)/1_000_000/op["conversas"]
            result.append(dict(braco=path.parents[1].name,conversas=op["conversas"],turnos_planejados=len(observations),
                       turnos_corretos=int(observations.ok.sum()),llm_chamadas=op["chamadas_llm"],tokens_entrada=tokens_in,
                       tokens_saida=tokens_out,p95_ms=op["p95_ms"],transbordo=op["transbordo"],resolucao=op["resolucao"],
                       conversao=op["conversao"],turnos_com_variacao=data["variacao_de_acao"],
                       custo_cenario_usd_por_conversa=cost))
    if len(signatures)!=1 or not result:
        raise ValueError("A comparação exige rodadas disponíveis, com o mesmo corpus e repetições.")
    return pd.DataFrame(result)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pastas",type=Path,nargs="+")
    parser.add_argument("--entrada",type=float,required=True,help="USD hipotético por milhão de tokens")
    parser.add_argument("--saida",type=float,required=True)
    parser.add_argument("--csv",type=Path,required=True)
    args=parser.parse_args()
    summarize(args.pastas,args.entrada,args.saida).to_csv(args.csv,index=False)
