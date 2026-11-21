"""F5 inicia o chat. Rode python main.py --help para os experimentos."""
import argparse
import json
import os
from pathlib import Path
from central.knowledge import ROOT

def main():
    cli=argparse.ArgumentParser(description="Central Telecom · laboratório CRISP-AI")
    sub=cli.add_subparsers(dest="command")
    sub.add_parser("serve",help="iniciar chat web local")
    sub.add_parser("doctor",help="inspecionar índice, ambiente e modelos locais")
    sub.add_parser("profile",help="auditar dados e exportar perfil")
    ev=sub.add_parser("evaluate",help="reproduzir conversas com resultados por turno")
    ev.add_argument("--mode",choices=["demo","ollama"],default="demo")
    ev.add_argument("--design",choices=["multi","single"],default="multi")
    ev.add_argument("--cases",type=Path,default=ROOT/"evaluation/cases.json")
    ev.add_argument("--split",default="all")
    ev.add_argument("--case",help="executar apenas um ID, por exemplo D01")
    ev.add_argument("--repeat",type=int,choices=range(1,21),default=1)
    ev.add_argument("--judge",action="store_true")
    ev.add_argument("--output",type=Path)
    cmp=sub.add_parser("compare",help="comparação pareada entre duas execuções")
    cmp.add_argument("primeira",type=Path)
    cmp.add_argument("segunda",type=Path)
    sub.add_parser("mcp",help="expor busca de políticas por MCP stdio")
    cal=sub.add_parser("calibrate",help="comparar juiz e avaliação humana")
    cal.add_argument("run",type=Path)
    gate=sub.add_parser("gate",help="validar candidato com avaliação privada e revisão humana")
    gate.add_argument("run",type=Path)
    ops=sub.add_parser("analyze",help="analisar eventos reais desta instalação")
    ops.add_argument("--db",type=Path,default=ROOT/"runtime/telecom.sqlite3")
    ops.add_argument("--output",type=Path)
    args=cli.parse_args()
    if args.command in (None,"serve"):
        import uvicorn
        from central.web import create_app
        print(f"Abra http://127.0.0.1:{os.getenv('PORT','8000')}  •  Ctrl+C encerra.",flush=True)
        uvicorn.run(create_app(),host=os.getenv("TELECOM_BIND","127.0.0.1"),port=int(os.getenv("PORT","8000")))
    elif args.command=="compare":
        from central.comparison import compare
        print(json.dumps(compare(args.primeira,args.segunda),indent=2,ensure_ascii=False))
    elif args.command=="mcp":
        from central.mcp_server import server
        server.run(transport="stdio")
    elif args.command=="doctor":
        import httpx,platform
        from central.engine import Engine
        e=Engine()
        try:
            with httpx.Client(trust_env=False,timeout=3) as client:
                r=client.get(e.llm.url+"/api/tags")
                r.raise_for_status()
            models=[x["name"] for x in r.json()["models"]]
        except (httpx.HTTPError,KeyError,ValueError):
            models=[]
        print(json.dumps({"python":platform.python_version(),"políticas":len(e.index.docs),
                    "ollama_modelos_listados":models,"modo":os.getenv("AGENT_MODE","demo"),
                    "modelo_roteador":e.llm.config["router"]["model"]},indent=2,ensure_ascii=False))
    elif args.command=="profile":
        from central.analysis import profile
        print(profile())
    elif args.command=="analyze":
        from central.analysis import analyze
        print(analyze(args.db,args.output))
    elif args.command=="gate":
        from central.provider import Ollama
        from central.release import assess
        decision=assess(args.run,Ollama().config)
        print(json.dumps(decision,ensure_ascii=False,indent=2))
        if not decision["promover"]:
            raise SystemExit(2)
    elif args.command=="calibrate":
        from central.evaluation import calibrate
        print(json.dumps(calibrate(args.run),ensure_ascii=False,indent=2))
    elif args.command=="evaluate":
        from central.engine import Engine
        from central.evaluation import evaluate,report
        cases=json.loads(args.cases.read_text(encoding="utf-8"))
        if args.split!="all":
            cases=[c for c in cases if c["split"]==args.split]
        if args.case:
            cases = [c for c in cases if c["id"]==args.case]
        if not cases:
            cli.error("Nenhum caso selecionado")
        out,s=evaluate(Engine(args.mode,args.design),cases,args.repeat,args.judge,args.output)
        report(out)
        print(json.dumps(s["por_grupo"],indent=2,ensure_ascii=False))
        print(out)
        if any(not r.get("ok",True) for line in (out/"traces.jsonl").read_text(encoding="utf-8").splitlines()
               for r in json.loads(line)["trace"] if "model" in r) or (args.judge and "unavailable" in (out/"turns.csv").read_text(encoding="utf-8")):
            raise SystemExit("Falha em chamada ao modelo. Resultados diagnósticos gravados.")
        if args.split=="dev" and s["por_grupo"]["dev"]["acerto_turnos"]<0.95:
            raise SystemExit("Regressão: acerto de desenvolvimento abaixo de 95%.")

if __name__=="__main__":
    main()
