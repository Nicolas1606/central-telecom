"""SQLite. Persistência atômica por turno, com revisão otimista e idempotência."""
from contextlib import contextmanager
from pathlib import Path
import json
import secrets
import sqlite3
import time
import uuid
from .tools import ACCOUNTS

class Conflict(Exception):
    pass

class Store:
    def __init__(self,path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, account TEXT, rev INTEGER, status TEXT,
                last TEXT, pending INTEGER, answerable INTEGER, offered INTEGER, mode TEXT, design TEXT);
            CREATE TABLE IF NOT EXISTS turns(sid TEXT, key TEXT, payload TEXT, fingerprint TEXT, ts REAL,
                PRIMARY KEY(sid,key));
            CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY, sid TEXT UNIQUE, reason TEXT, summary TEXT,
                status TEXT, created REAL);
            """)

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path,timeout=10)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    def new(self,account,engine):
        if account not in ACCOUNTS:
            raise ValueError("Perfil de demonstração inválido")
        sid = secrets.token_urlsafe(24)
        with self.db() as db:
            db.execute("INSERT INTO sessions VALUES(?,?,0,'open','',0,0,0,?,?)",(sid,account,engine.mode,engine.design))
        return sid

    def chat(self,sid,key,text,engine,rev):
        import hashlib
        fp = hashlib.sha256(text.encode()).hexdigest()
        def replay(row):
            if row["fingerprint"] != fp:
                raise Conflict("A chave de envio já foi usada com outro conteúdo.")
            return json.loads(row["payload"])
        with self.db() as db:
            existing = db.execute("SELECT * FROM turns WHERE sid=? AND key=?",(sid,key)).fetchone()
            if existing:
                return replay(existing)
            state = db.execute("SELECT * FROM sessions WHERE id=?",(sid,)).fetchone()
        if state is None:
            raise KeyError("Sessão inexistente")
        state = dict(state)
        if state["status"]!="open" or rev!=state["rev"]:
            raise Conflict("Sessão encerrada ou desatualizada. Abra outra conversa.")
        if (state["mode"],state["design"]) != (engine.mode,engine.design):
            raise Conflict("Configuração da sessão mudou. Inicie outra conversa.")
        start = time.perf_counter()
        out = engine.turn(text,state)
        elapsed = (time.perf_counter()-start)*1000
        action = out["action"]
        status = action if action in {"handoff","resolved","converted"} else "open"
        last = next((d for d in reversed(out["domains"]) if d in {"cobranca","suporte","cancelamento"}),state["last"])
        out.update(revision=rev+1,status=status,latency_ms=round(elapsed,3),trace_id=uuid.uuid4().hex)
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM turns WHERE sid=? AND key=?",(sid,key)).fetchone()
            if existing:
                return replay(existing)
            cur = db.execute("""UPDATE sessions SET rev=rev+1,status=?,last=?,pending=?,answerable=?,
                          offered=max(offered,?) WHERE id=? AND rev=? AND status='open'""",
                       (status,last,action=="offer",action=="answer",action=="offer",sid,rev))
            if cur.rowcount!=1:
                raise Conflict("Outro turno alterou a conversa.")
            if action=="handoff":
                tid = uuid.uuid4().hex[:12]
                out["ticket"] = tid
                previous = [json.loads(r[0]) for r in db.execute("SELECT payload FROM turns WHERE sid=? ORDER BY ts DESC LIMIT 2",(sid,))]
                summary = {"ultima_area":last,"dominios":out["domains"],"motivo":out["reason"],"orientacao":out["message"],
                           "fontes":[s["id"] for s in out["sources"]],"historico":[{"acao":p["action"],"orientacao":p["message"]} for p in reversed(previous)]}
                db.execute("INSERT INTO tickets VALUES(?,?,?,?,?,?)",(tid,sid,out["reason"],json.dumps(summary,ensure_ascii=False),"aberto",time.time()))
            db.execute("INSERT INTO turns VALUES(?,?,?,?,?)",(sid,key,json.dumps(out,ensure_ascii=False),fp,time.time()))
        return out

    def tickets(self):
        with self.db() as db:
            return [dict(id=r["id"],reason=r["reason"],status=r["status"],summary=json.loads(r["summary"]))
                    for r in db.execute("SELECT * FROM tickets ORDER BY created DESC LIMIT 100")]

    def close(self,tid):
        with self.db() as db:
            if db.execute("UPDATE tickets SET status='revisado' WHERE id=?",(tid,)).rowcount!=1:
                raise KeyError("Ticket inexistente")

    def metrics(self):
        import math
        from collections import Counter
        with self.db() as db:
            sessions = [dict(r) for r in db.execute("SELECT * FROM sessions WHERE rev>0")]
            turns = [json.loads(r[0]) for r in db.execute("SELECT payload FROM turns")]
        n = len(sessions)
        states = Counter(s["status"] for s in sessions)
        offered = sum(s["offered"] for s in sessions)
        spans = [span for t in turns for span in t["trace"] if "model" in span]
        def complete_sum(key):
            return None if any(s[key] is None for s in spans) else sum(s[key] for s in spans)
        cost = complete_sum("cost_usd")
        durations = sorted(t["latency_ms"] for t in turns)
        reasons = Counter(t["reason"] for t in turns if t["action"]=="handoff")
        alarms = []
        if len(turns)>=10 and sum(t["reason"]=="falha_validacao" for t in turns)/len(turns)>0.1:
            alarms.append("Falhas de validação acima de 10% dos turnos.")
        if durations and durations[math.ceil(len(durations)*.95)-1]>10000:
            alarms.append("Latência p95 acima de 10 s.")
        return {"conversas":n,"turnos":len(turns),"abertas":states["open"],"resolvidas_confirmadas":states["resolved"],
                "resolucao":states["resolved"]/n if n else None,"motivos_transbordo":dict(reasons),
                "transbordo":states["handoff"]/n if n else None,"ofertas":offered,"aceites":states["converted"],
                "conversao":states["converted"]/offered if offered else None,
                "p95_ms":durations[math.ceil(len(durations)*.95)-1] if durations else None,
                "chamadas_llm":len(spans),"tokens_entrada":complete_sum("tokens_in"),"tokens_saida":complete_sum("tokens_out"),
                "custo_inferencia_usd_por_conversa":cost/n if n and cost is not None else None,"alertas":alarms}
