const el = id => document.getElementById(id);
const add = (parent, tag, text) => {
  const node = document.createElement(tag);
  node.textContent = text;
  parent.appendChild(node);
  return node;
};
let session, revision, busy = false, pending = null;
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)
  });
  const value = await response.json();
  if (!response.ok) throw new Error(typeof value.detail === 'string' ? value.detail : 'Confira os dados da solicitação.');
  return value;
}
function controls(loading) {
  busy = loading;
  ['send','new','account','question'].forEach(id => el(id).disabled = loading);
}
async function begin() {
  controls(true);
  try {
    const value = await api('/api/sessions',{account:el('account').value});
    session = value.id; revision = 0; pending = null;
    el('history').replaceChildren(); el('question').value = '';
    el('status').textContent = 'Conversa aberta · ' + (value.mode === 'demo' ? 'demonstração por regras' : 'agentes com Ollama');
    el('composer').hidden = false;
    el('notice').textContent = '';
  } catch(e) { el('notice').textContent = e.message; } finally { controls(false); }
}
el('new').onclick = begin; el('account').onchange = begin;
el('composer').onsubmit = async event => {
  event.preventDefault();
  const text = el('question').value.trim();
  if (!session || !text || busy) return;
  controls(true); el('status').textContent = 'Consultando…';
  if (!pending || pending.text !== text) pending = {text,revision,key:crypto.randomUUID()};
  try {
    const r = await api('/api/sessions/'+session+'/turn',pending);
    revision = r.revision; pending = null;
    const client = add(el('history'),'div',''); client.className = 'bubble client';
    add(client,'small','Você'); add(client,'p',text);
    const box = add(el('history'),'div',''); box.className = 'bubble';
    add(box,'small',r.domains.join(' → ') || 'Atendimento');
    add(box,'p',r.message);
    if (r.ticket) add(box,'small','Protocolo '+r.ticket);
    if (r.sources.length) {
      const detail = add(box,'details',''); add(detail,'summary','Conferir políticas');
      r.sources.forEach(s => add(detail,'p',s.id+' · '+s.text));
    }
    el('question').value = ''; el('composer').hidden = r.status !== 'open';
    el('status').textContent = r.status === 'open' ? 'Em atendimento' : 'Conversa encerrada · '+r.status;
    el('notice').textContent = '';
  } catch(e) { el('notice').textContent = e.message; el('status').textContent = 'Falha no envio'; }
  finally { controls(false); }
};
async function refresh(view) {
  if (view === 'queue') {
    const list = await api('/api/tickets'); const parent = el('tickets'); parent.replaceChildren();
    if (!list.length) add(parent,'p','Nenhum caso encaminhado.');
    list.forEach(t => {
      const box = add(parent,'article',''); add(box,'strong',t.id+' · '+t.reason);
      add(box,'p',t.summary.orientacao);
      for (const p of t.summary.historico) add(box,'small',p.orientacao+' ');
      if (t.status === 'aberto') {
        const btn = add(box,'button','Marcar como revisado');
        btn.onclick = async () => {try {await api('/api/tickets/'+t.id+'/revisar',{}); await refresh(view);} catch(e){el('notice').textContent=e.message;}};
      } else add(box,'small','Revisado');
    });
  }
  if (view === 'metrics') {
    const m = await api('/api/metrics'); const cards = el('cards'); cards.replaceChildren();
    for(const [key,title,unit] of [['conversas','Conversas',''],['resolucao','Resolução confirmada','%'],['transbordo','Transbordo','%'],['conversao','Aceite por oferta','%'],['p95_ms','Latência p95',' ms'],['tokens_entrada','Tokens de entrada',''],['tokens_saida','Tokens de saída',''],['custo_inferencia_usd_por_conversa','USD de inferência / conversa','USD']]){
      const box = add(cards,'article',''); let value = m[key];
      if(value !== null && unit === '%') value = (100*value).toFixed(1);
      if(value !== null && unit === 'USD') value = value.toFixed(6);
      add(box,'small',title); add(box,'strong',value === null ? 'Sem medida' : value+(unit === 'USD' ? '' : unit));
    }
    for(const [id,rows] of [['reasons',Object.entries(m.motivos_transbordo).map(([k,v])=>k+' · '+v)],['alarms',m.alertas]]){
      el(id).replaceChildren(); (rows.length ? rows : ['Nenhum registro.']).forEach(v=>add(el(id),'li',v));
    }
  }
}
document.querySelectorAll('nav button').forEach(btn => btn.onclick = async () => {
  for(const tab of document.querySelectorAll('nav button')){
    const active = tab === btn; el(tab.dataset.view).hidden = !active;
    if(active) tab.setAttribute('aria-current','page'); else tab.removeAttribute('aria-current');
  }
  try {await refresh(btn.dataset.view);} catch(e){el('notice').textContent = e.message;}
});
begin();
