# Como auditar o projeto para a vaga

| Competência | O que inspecionar | Alcance comprovado |
|---|---|---|
| Construir agentes e definir orquestrador, especialistas, roteamento e handoff | Chat; central/engine.py e graph.py; reports/chat_http_ollama.json | Três especialistas, intenções compostas, passagem entre turnos e fila humana com histórico. |
| Manter system prompts com histórico e validação antes da promoção | prompts/; scripts/benchmark.py; central/release.py; template de PR e histórico Git | Versões por papel, hashes por chamada, comparação e comando gate que reprova candidatas sem evidência. |
| Testar ponta a ponta, bordas, regressões e usar LLM como juiz | tests/; evaluation/; reports/juiz_llm e controles_juiz.json | Testes HTTP e de contrato, replays com pesos reais e sondas positivas/negativas do juiz. |
| Instrumentar resolução, motivos de transbordo, conversão, custo, latência e tokens | Aba Indicadores; central/storage.py; scripts/finops.py | Métricas calculadas no próprio chat e replays. Resolução exige confirmação e conversão exige aceite. |
| Modelo, esforço e temperatura por agente | config/piloto.json, configs nos summaries, reports/validacao_llm e correcao_llm | Comparações de configuração com pesos reais; erros do provedor preservados. Escolha explícita por função. |
| Traduzir resultados para produto e cliente | docs/EVIDENCIAS.md e CAMPO.md | Recomendação operacional, falhas conhecidas, comparação de qualidade e consumo com denominadores. |
| Trabalhar com produto, engenharia e operação | docs/PILOTO.md, RUNBOOK.md, scripts/revisao_cega.py e estudo.py | Papéis, tarefas, coleta, decisão e reversão executáveis. Participação externa depende de um piloto. |
| Python e uso prático de LLM com ferramentas, saída estruturada e contexto | central/provider.py, tools.py, engine.py; traces das variantes multi e escopo | Tool calling nativo exercitado; na candidata, plano JSON validado e executado contra a conta vinculada no servidor. |
| RAG, embeddings, chunking e recuperação | central/knowledge.py, knowledge/ e retrieval.csv | Segmentação por política, busca lexical, embeddings LSA e híbrida, recall@3. A fala final combina fatos e fontes controlados. |
| Git e revisão | Bundle Git, histórico de commits, template e workflow Windows/Linux | Histórico local restaurável e protocolo de revisão. Aprovação de outra pessoa exige revisão real. |
| Investigar não determinismo com método | docs/EVIDENCIAS.md, falhas.csv, traces e configurações | Hipóteses, ablações e reexecuções. Resultados de testes repetidos têm dependência entre observações. |
| Canal conversacional e transbordo humano | Chat web, FastAPI, fila e revisão de ticket | Canal chat exercitado por HTTP com serviço local e pesos reais. Uso comercial por clientes ainda aberto. |
| Guardrails e contenção | Escopo, confirmação de intenção e aceite, ferramentas delimitadas, teste de troca de conta | Regressões sobre dados fictícios, bloqueio de recurso de operador sem credencial no modo piloto. |
| Observabilidade e avaliação de LLM | Trace estruturado por turno, modelo, prompt, fonte, tokens, duração, alertas e SQLite | Instrumentação própria acessível via API, CSV e inspeção do trace; runbook vincula sinal a decisão. |
| Framework e MCP | LangGraph e MCP SDK; central/graph.py, mcp_client.py, mcp_server.py | Replays em LangGraph e teste do servidor MCP em processo separado. |
| Pandas e visualização de dados conversacionais reais | central/field_data.py e reports/campo/ | Corpus externo real em volume. Estatísticas descritivas e sugestões para investigação operacional. |
| FinOps sem sacrificar qualidade | scripts/finops.py, reports/finops.csv | Mudança pareada com menos chamadas e tokens e maior acerto no mesmo conjunto. Tarifas podem ser substituídas. |
| IA aplicada a produto e automação | Jornada demonstrável de consulta, orientação, confirmação e atendimento humano | Protótipo de produto com CRM fictício e documentação para teste de campo. |
