"""Executor opcional LangGraph; o roteamento e as políticas são os mesmos do nativo."""
from typing import TypedDict
from .tools import TOOLS

class Flow(TypedDict):
    remaining: list[str]
    parts: list[dict]

def execute(domains, run_specialist):
    from langgraph.graph import END, START, StateGraph
    graph = StateGraph(Flow)
    def dispatch(state):
        return {}
    def destination(state):
        return state["remaining"][0] if state["remaining"] else END
    def specialist(domain):
        def run(state):
            return {"parts":[*state["parts"],run_specialist(domain)],"remaining":state["remaining"][1:]}
        return run
    graph.add_node("dispatch",dispatch)
    graph.add_edge(START,"dispatch")
    graph.add_conditional_edges("dispatch",destination,{**{d:d for d in TOOLS},END:END})
    for domain in TOOLS:
        graph.add_node(domain,specialist(domain))
        graph.add_edge(domain,"dispatch")
    return graph.compile().invoke({"remaining":domains,"parts":[]})["parts"]
