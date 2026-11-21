"""Ferramentas somente leitura. A conta vem da sessão criada pelo servidor."""
import json
from .knowledge import ROOT

ACCOUNTS = json.loads((ROOT / "data/accounts.json").read_text(encoding="utf-8"))
TOOLS = {"cobranca":"invoice", "suporte":"network", "cancelamento":"eligibility"}
DESCRIPTIONS = {"invoice":"Consulta os itens da fatura em centavos.", "network":"Consulta incidente na região.", "eligibility":"Consulta elegibilidade para oferta fictícia."}

def lookup(name, account):
    row = ACCOUNTS[account]
    if name == "invoice":
        return {"mensalidade":row["base"], "adicional":row["extra"], "total":row["base"]+row["extra"]}
    if name == "network":
        return {"regiao":row["region"], "incidente":row["incident"], "protocolo":"NET-08" if row["incident"] else None}
    if name == "eligibility":
        return {"elegivel":row["eligible"]}
    raise ValueError("Ferramenta desconhecida")

def schema(name):
    return {"type":"function","function":{"name":name,"description":DESCRIPTIONS[name],
            "parameters":{"type":"object","properties":{},"additionalProperties":False}}}
