"""Orquestração por domínio. O LLM decide dentro de ferramentas e políticas verificáveis."""
import json
import os
import re
from .knowledge import Index, norm
from .provider import Choice, Ollama, ToolPlan, Route, Unavailable, user
from .tools import DESCRIPTIONS, TOOLS, lookup, schema

KEYS = {
    "cobranca":r"\b(fatura|conta|boleto|mensalidade|cobranca|extrato|cobraram|estorno|reembolso|cobrado)\b",
    "suporte":r"\b(internet|conexao|sinal|wifi|roteador|modem|rede|wi fi|offline)\b",
    "cancelamento":r"\b(cancel\w*|encerr\w*|desconto|oferta|alternativa\w*|mais barato|sair do plano)\b"
}
def has(pattern, text):
    return bool(re.search(pattern,text))

def result(action, message, reason="", sources=None):
    return dict(action=action, message=message, reason=reason, sources=sources or [])

def money(n):
    return f"R$ {n//100},{n%100:02d}"

def rules_route(q,last):
    clean = re.sub(r"\b(?:nao (?:quero |vou |desejo )?(?:cancelar|encerrar)(?: o contrato)?|sem cancelar)\b","",q)
    clean = re.sub(r"\bmais em conta\b","mais barato",clean)
    domains = [d for d,p in KEYS.items() if has(p,clean)]
    if domains:
        return domains
    if last and has(r"\b(e agora|quanto|continua|ainda|ja reiniciei|continua igual|esse valor|por que)\b",q):
        return [last]
    if has(r"\bvalor\b",q) and has(r"mudou|diferenca",q):
        return ["esclarecer"]
    if len(q.split()) < 3 or has(r"\b(ajuda|problema|duvida)\b",q):
        return ["esclarecer"]
    return ["outras"]

class Engine:
    def __init__(self, mode="demo", design="multi", index=None, llm=None, search="hybrid"):
        if mode not in {"demo","ollama"} or design not in {"multi","single"}:
            raise ValueError("Modo ou arquitetura inválida")
        self.mode,self.design,self.search = mode,design,search
        self.index = index or Index()
        self.llm = llm or Ollama()

    def route(self, text, state, trace):
        q = norm(text)
        if self.mode == "demo":
            return rules_route(q,state.get("last"))
        role = "router" if self.design == "multi" else "generalista"
        strategy = self.llm.config[role].get("routing")
        if strategy in {"anchored", "scope_gate"}:
            candidates = rules_route(q,state.get("last"))
            if strategy == "scope_gate" or all(d in TOOLS for d in candidates):
                trace.append({"agent":role,"routing":strategy,"domains":candidates})
                return candidates
        route = self.llm.chat(role,[user({"etapa":"rotear todas as intenções no esquema","pergunta":text,
                                          "ultimo_dominio":state.get("last")})],trace,contract=Route)
        domains = route.domains
        if len(set(domains)) != len(domains) or len(domains)>1 and any(x not in TOOLS for x in domains):
            raise Unavailable("Roteamento ambíguo")
        return domains

    def specialist(self, domain, text, state, trace):
        q = norm(text)
        account = state["account"]
        tool = TOOLS[domain]
        role = domain if self.design == "multi" else "generalista"
        question = user({"dominio":domain,"pergunta":text,"ultimo_dominio":state.get("last")})
        structured = self.mode == "ollama" and self.llm.config[role].get("tool_protocol") == "plan"
        if structured:
            task = user({"operation":"select read-only tool","domain":domain,"customer_question":text,
                         "tools":{"invoice":"billing","network":"technical support","eligibility":"contract or discount","handoff":"cannot serve"}})
            proposal = self.llm.chat(role,[task],trace,contract=ToolPlan)
            if proposal.name != tool:
                raise Unavailable("Plano estruturado incompatível com o domínio")
        elif self.mode == "ollama":
            allowed = [tool] if self.design=="multi" else list(DESCRIPTIONS)
            msg = self.llm.chat(role,[question],trace,tools=[schema(n) for n in allowed])
            calls = msg.get("tool_calls") or []
            if len(calls)!=1 or not isinstance(calls[0],dict):
                raise Unavailable("Chamada de ferramenta ausente")
            call = calls[0].get("function",{})
            if not isinstance(call,dict) or call.get("name")!=tool or call.get("arguments")!={}:
                raise Unavailable("Ferramenta fora do escopo")
        fact = lookup(tool,account)
        trace.append({"tool":tool,"agent":role,"ok":True})
        if domain=="cobranca":
            dispute = has(r"duas vezes|duplicad|indevid|contestar|nao reconheco|estorno|reembolso",q)
            policy = "FAT-02" if dispute else "FAT-01"
            msg_text = (f"Mensalidade de {money(fact['mensalidade'])} e adicionais de {money(fact['adicional'])}. "
                        f"Total de {money(fact['total'])}.")
            action,reason = ("handoff","contestacao") if dispute else ("answer","")
            if dispute:
                msg_text += " Encaminhei a contestação para conferência do extrato."
        elif domain=="suporte":
            policy = "NET-01" if fact["incidente"] else "NET-02"
            if fact["incidente"]:
                action,reason = "answer",""
                msg_text = f"Há interrupção na região {fact['regiao']}, protocolo {fact['protocolo']}. Ainda sem previsão confirmada."
            elif has(r"ja reiniciei|apos reiniciar|continua (?:sem|igual)|persiste",q):
                action,reason,msg_text = "handoff","teste_esgotado","O teste inicial já foi feito. Encaminhei o diagnóstico ao suporte."
            else:
                action,reason,msg_text = "answer","","A região está sem ocorrência aberta. Confira os cabos e reinicie o roteador uma vez. A conexão voltou?"
        else:
            offer = has(r"desconto|oferta|alternativa|mais barato",q)
            firm_cancel = has(r"quero cancelar|cancele|encerre|quero encerrar|cancelar agora",q) and not has(r"nao quero cancelar|sem cancelar|se (?:isso|continuar)",q)
            if firm_cancel or not offer:
                policy = "CAN-01"
                if has(r"\bse\b|talvez|pensando|como funciona",q) and not firm_cancel:
                    action,reason,msg_text = "clarify","confirmar_intencao","Você quer solicitar o encerramento agora ou apenas entender as opções?"
                else:
                    action,reason,msg_text = "handoff","encerramento","Uma pessoa vai acompanhar seu pedido de encerramento. O contrato permanece ativo até a conclusão."
            elif fact["elegivel"]:
                policy,action,reason = "OFE-01","offer","elegivel"
                msg_text = "A oferta simulada reduz uma fatura em R$ 10,00. Para registrar sua escolha, envie exatamente ACEITO A OFERTA."
            else:
                policy,action,reason = "OFE-01","handoff","sem_oferta"
                msg_text = "A conta está sem oferta elegível. Encaminhei o pedido à equipe."
        # A consulta traz o estado operacional resolvido pela ferramenta, além do texto do usuário.
        cue = {"FAT-01":"composição fatura","FAT-02":"contestação lançamento","NET-01":"interrupção regional",
               "NET-02":"teste inicial conexão","CAN-01":"pedido encerramento","OFE-01":"condição oferta"}
        query = text+" "+cue[policy]
        if os.getenv("POLICY_TRANSPORT")=="mcp":
            from .mcp_client import retrieve
            hits = retrieve(query,domain,self.search)
        else:
            hits = self.index.search(query,domain,self.search)
        trace.append({"agent":role,"retrieval":[r["id"] for r in hits],"expected_policy":policy})
        # Para a variante econômica, um trecho único compatível com a política de negócio
        # pode ser confirmado pelo servidor após uma chamada real de ferramenta.
        direct = self.llm.config[role].get("source_selection") == "validated_top1" and hits and hits[0]["id"] == policy
        if self.mode == "ollama" and direct:
            trace.append({"agent":role,"selection":"validated_top1","source_id":policy})
        if self.mode=="ollama" and not direct:
            if structured:
                messages = [question, user({"ferramenta_executada":tool,"fatos":fact})]
            else:
                messages = [question,{"role":"assistant","content":"","tool_calls":calls},
                            {"role":"tool","tool_name":tool,"content":json.dumps(fact,ensure_ascii=False)}]
            messages.append(user({"etapa":"escolher fonte pertinente","fontes":[[r["id"],r["text"]] for r in hits]}))
            choice = self.llm.chat(role,messages,trace,contract=Choice)
            if choice.source_id != policy:
                raise Unavailable("Fonte escolhida não sustenta a regra aplicável")
        source = next((r for r in hits if r["id"]==policy),None)
        if source is None:
            raise Unavailable("Política não recuperada")
        return result(action,msg_text,reason,[{k:source[k] for k in ("id","title","text","source","sha256")}])

    def turn(self, text, state):
        q = norm(text)
        trace,domains = [],[]
        def finish(out):
            return dict(**out,domains=domains,trace=trace)
        human_request = re.sub(
            r"\b(?:nao (?:preciso|quero|necessito)(?: (?:falar|conversar))?(?: de| com)?|sem)"
            r" (?:um |uma )?(?:humano|atendente|pessoa de verdade)\b", "", q)
        if has(r"\b(humano|atendente|pessoa de verdade)\b",human_request):
            return finish(result("handoff","Encaminhei seu atendimento a uma pessoa.","pedido_humano"))
        if has(r"ignore (?:todas |as )*(?:regras|instrucoes)|system prompt|outr[oa] (?:conta|cliente)|\bcpf\b|\bsenha\b",q):
            return finish(result("handoff","A equipe vai revisar a solicitação. Use somente os perfis fictícios da demonstração.","limite_de_acesso"))
        if q=="aceito a oferta":
            if state.get("pending"):
                return finish(result("converted","Aceite da oferta fictícia registrado para esta sessão.","aceite_explicito"))
            return finish(result("clarify","Qual oferta deseja consultar? O aceite exige uma proposta aberta.","sem_proposta"))
        if q in {"resolveu","problema resolvido","deu certo"} and state.get("answerable"):
            return finish(result("resolved","Obrigada por confirmar a resolução.","confirmacao_usuario"))
        try:
            domains.extend(self.route(text,state,trace))
            # O pedido de saída tem precedência mesmo que o classificador do modelo erre.
            explicit_exit = has(r"\b(quero cancelar agora|cancele meu contrato|encerre meu contrato)\b",q)
            if explicit_exit and not has(r"\b(nao|se)\b",q) and "cancelamento" not in domains:
                return finish(result("handoff","Encaminhei o pedido de encerramento para uma pessoa.","encerramento"))
            if domains==["esclarecer"]:
                return finish(result("clarify","Sua dúvida é sobre fatura, conexão ou encerramento?","contexto"))
            if domains in (["humano"],["outras"]):
                return finish(result("handoff","Encaminhei a solicitação à equipe de atendimento.","pedido_humano" if domains==["humano"] else "fora_escopo"))
            def execute_one(domain):
                return self.specialist(domain,text,state,trace)
            if os.getenv("ORCHESTRATOR")=="langgraph":
                from .graph import execute
                parts = execute(domains,execute_one)
            else:
                parts = [execute_one(d) for d in domains]
            priority = {"answer":0,"offer":1,"clarify":2,"handoff":3}
            decisive = max(parts,key=lambda r:priority[r["action"]])
            if decisive["action"] in {"handoff","clarify"}:
                for part in parts:
                    if part["action"]=="offer":
                        part["message"]="A conta é elegível para uma alternativa. O atendimento atual segue para tratar a solicitação prioritária."
            return finish(result(decisive["action"]," ".join(p["message"] for p in parts),decisive["reason"],
                                 [s for p in parts for s in p["sources"]]))
        except Unavailable as exc:
            trace.append({"failure":str(exc)})
            return finish(result("handoff","O sistema não conseguiu validar a orientação. A equipe recebeu o caso.","falha_validacao"))
