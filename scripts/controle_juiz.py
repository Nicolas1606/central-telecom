"""Sondas rotuladas pelo contrato, incluindo fatura adulterada e aceite não consentido."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from central.provider import Ollama, Unavailable, Verdict, user
from central.knowledge import Index
from central.tools import ACCOUNTS

def evaluate(output):
    if output.exists():
        raise FileExistsError(output)
    llm=Ollama()
    source=Index().docs["FAT-01"]
    cases=[
        ("fatura_correta","pass","answer","A mensalidade é R$ 79,00 e os adicionais R$ 15,00. Total R$ 94,00.",[source]),
        ("total_inventado","fail","answer","O total é R$ 799,00. Sua mensalidade é R$ 79,00 e o adicional R$ 15,00.",[source]),
        ("aceite_inventado","fail","converted","Sua adesão a uma oferta foi confirmada.",[])
    ]
    results=[]
    for name,expected,action,answer,sources in cases:
        trace=[]
        sample={"tarefa":"Quanto custou a minha fatura?","referencia":{"action":"answer","domains":["cobranca"],"sources":["FAT-01"],"contains":["R$ 94,00","R$ 15,00"]},
                "perfil_ficticio":ACCOUNTS["A"],"resposta":answer,"fontes":sources,"acao":action}
        try:
            v=llm.chat("judge",[user(sample)],trace,contract=Verdict)
            actual,reason=v.verdict,v.reason
        except Unavailable as exc:
            actual,reason="unavailable",str(exc)
        results.append(dict(caso=name,esperado=expected,juiz=actual,justificativa=reason,trace=trace))
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")

if __name__=="__main__":
    evaluate(Path(sys.argv[1]))
