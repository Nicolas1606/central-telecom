# Central Telecom

**Uma central de atendimento multiagente em português para explicar faturas, diagnosticar falhas de conexão e encaminhar pedidos de cancelamento.** O projeto acompanha a conversa desde a mensagem do cliente até a consulta às ferramentas, a política que sustenta a resposta, o protocolo recebido pela operação e os indicadores utilizados para avaliar a solução.

Imagine que um cliente diga **“Minha fatura veio mais cara e, se isso continuar, quero cancelar.”** No perfil A, o extrato fictício mostra R$ 79,00 de mensalidade e R$ 15,00 de adicionais. A aplicação explica os R$ 94,00 e pergunta se o cliente quer efetivamente encerrar o contrato. Um pedido explícito abre um protocolo com o histórico necessário para um atendente.

## Abrir no Windows

**Visual Studio.** Extraia o ZIP. No Visual Studio Installer, habilite a carga de trabalho **Desenvolvimento em Python**. Abra `CentralTelecom.sln`. No terminal da solução, a pasta correta contém `main.py` e `requirements.txt`. A primeira instalação precisa de internet. O ambiente de referência usa Python 3.12 de 64 bits.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py serve
```

Se o seu Python estiver em `$env:LOCALAPPDATA\Programs\Python\Python314\python.exe`, você também pode usar `& "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe" -m venv .venv`. As dependências declaram faixas de versões. A combinação testada nesta entrega está em [docs/AMBIENTE.md](docs/AMBIENTE.md). Outra opção no PowerShell é executar `.\Iniciar.ps1` na raiz. Ele cria o ambiente quando necessário, instala os pacotes e inicia o chat.

Abra **http://127.0.0.1:8000**. Para depurar pelo Visual Studio, selecione o interpretador de `.venv` em **Python Environments** e pressione **F5**. No **VS Code**, abra a pasta extraída, selecione esse mesmo interpretador com **Python: Select Interpreter**, abra **Executar e Depurar** e escolha **Central Telecom · demonstração**. O terminal da aplicação fica aberto enquanto o chat está em uso. A documentação HTTP interativa está em `/docs`. [Suporte a projetos Python no Visual Studio](https://learn.microsoft.com/en-us/visualstudio/python/quickstart-01-python-in-visual-studio-project-from-existing-code?view=visualstudio)

## Roteiro de demonstração

1. No perfil **A · Centro**, envie a pergunta da introdução. Expanda **Conferir políticas**. Envie **Quero cancelar agora**, abra **Fila humana** e confira o resumo antes de marcar o protocolo como revisado.
2. Inicie outra conversa no perfil **B · Norte** e pergunte **Minha internet está sem sinal. Há alguma ocorrência?** A ferramenta informa a região e o protocolo NET-08. Envie **Resolveu** para registrar a confirmação da resolução.
3. No perfil A, pergunte **Existe desconto?**. A oferta só conta como conversão depois da mensagem **ACEITO A OFERTA**. Visite **Indicadores** e confira os denominadores descritos abaixo.

## Dois modos de execução

| Modo | Decisões e ferramentas | Uso |
|---|---|---|
| `demo`, padrão | Regras de intenção, ferramentas locais, índice de políticas e respostas controladas | Explorar o produto e reproduzir contratos em qualquer computador após instalar as dependências |
| `ollama` | LLM local escolhe domínios, chama ferramentas e seleciona fonte com saída estruturada. O servidor verifica a decisão e compõe a orientação | Medir comportamento do modelo, comparar prompts, registrar tokens, custo e latência |

Para testar os agentes com pesos reais, mantenha o serviço Ollama em execução. Se `ollama list` já mostrar `qwen3:4b`, o modelo está disponível no seu computador. Caso precise baixar, use `ollama pull qwen3:4b`. Comece pelo caso curto D01.

```powershell
.\.venv\Scripts\python.exe main.py doctor
.\.venv\Scripts\python.exe main.py evaluate --mode ollama --case D01 --judge
```

O caso D01 pede o valor da fatura e depois confirma a solução. Abra `turns.csv` e `traces.jsonl` no diretório impresso pelo comando. Confira `ok`, o veredito do juiz, as fontes, os tokens e a ferramenta `invoice`. Em seguida, encerre o servidor anterior com Ctrl+C e inicie o chat generativo em banco separado.

```powershell
$env:AGENT_MODE = "ollama"
$env:TELECOM_DB = "runtime/ollama.sqlite3"
.\.venv\Scripts\python.exe main.py serve
```

Queda do modelo, chamada de ferramenta inválida ou fonte incompatível resultam em transbordo com motivo visível no trace. O modelo recebe contexto limitado a pergunta atual, última área, fatos da ferramenta e passagens recuperadas. A máquina de estados também conserva a revisão e a proposta pendente. [API de chat do Ollama](https://docs.ollama.com/api/chat)

## Arquitetura

```mermaid
flowchart TD
  A["Chat web"] --> B["API e sessão"]
  B --> R["Roteador e regras de atendimento"]
  R --> C["Cobrança"]
  R --> T["Suporte técnico"]
  R --> E["Cancelamento e alternativas"]
  C --> F["Ferramentas de consulta e políticas RAG"]
  T --> F
  E --> F
  F --> V["Verificação de fonte e estado"]
  V --> H["Fila humana"]
  V --> S["Resposta ou pedido de contexto"]
  H --> O["SQLite · tickets, eventos e métricas"]
  S --> O
```

O chat usa HTTP, FastAPI e SQLite. O índice combina TF-IDF e embeddings locais de semântica latente (LSA). Cada política tem identificador e hash. O modo Ollama implementa RAG com escolha de evidência estruturada. O texto final segue fatos e regras de negócio verificados. O cliente não pode trocar o perfil usando argumentos da ferramenta. O generalista de referência compartilha o mesmo CRM e catálogo.

**LangGraph e MCP.** O executor nativo e o grafo opcional usam os mesmos especialistas. Para executar o framework e o servidor MCP de políticas no fluxo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-graph.txt
$env:ORCHESTRATOR = "langgraph"
$env:POLICY_TRANSPORT = "mcp"
.\.venv\Scripts\python.exe main.py evaluate --case D01
```

MCP abre um subprocesso Python por consulta nesta demonstração. Esse desenho facilita a inspeção do protocolo e aumenta a latência. O comando `python main.py mcp` inicia o servidor stdio para clientes MCP externos. Para voltar ao caminho nativo no PowerShell, use `Remove-Item Env:ORCHESTRATOR,Env:POLICY_TRANSPORT -ErrorAction SilentlyContinue`. [LangGraph](https://docs.langchain.com/oss/python/langgraph/graph-api) · [Python SDK do MCP](https://github.com/modelcontextprotocol/python-sdk)

## Evidências e resultados

O primeiro replay verificou 20/20 turnos de desenvolvimento e 9/12 turnos de desafio. Detectou três falhas, incluindo uma cobrança descrita como “duas vezes” que deveria gerar contestação. As correções elevaram o desafio a 12/12. A primeira execução de oito perguntas adicionais atingiu 6/8. Após corrigir um pedido de atendente negado e tratar um valor ambíguo por esclarecimento, o mesmo conjunto atingiu 7/8.

| Conjunto público da entrega | Conversas | Turnos corretos no modo demo |
|---|---:|---:|
| Desenvolvimento | 16 | 20/20 |
| Desafio incorporado à regressão | 10 | 12/12 |
| Verificação reutilizada após diagnóstico | 8 | 7/8 |

**39 de 40 turnos** atenderam ao gabarito na rodada final. A busca lexical atingiu recall@3 médio de 0,911. A busca densa e a híbrida chegaram a 0,929 nessa amostra. Há resultado por pergunta e registro do erro restante em [reports/example](reports/example). O ensaio é público, sintético e executado por regras. Para afirmar desempenho do LLM e impacto com clientes, use o piloto e a revisão independente.

![Matriz de ações e acerto nos conjuntos públicos](reports/example/avaliacao.png)

### Reproduzir

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py profile
.\.venv\Scripts\python.exe main.py evaluate
.\.venv\Scripts\python.exe main.py analyze --db runtime/telecom.sqlite3
```

Nesta entrega, 29 testes automatizados passaram e um teste opcional de LangGraph ficou pendente. [Lista de testes e estados](reports/testes.md).

O benchmark cria banco temporário e salva cada execução separadamente em `reports/runs/`. O painel lê apenas o banco do chat. Para investigar o comportamento não determinístico do LLM, rode o mesmo conjunto ao menos três vezes com cada configuração:

```powershell
.\scripts\experimento.ps1 -Repeticoes 3 -Grupo verification -Juiz
```

O experimento compara **generalista**, **multiagente padrão** e **multiagente candidato**. Gera comparações pareadas e registra ganhos, perdas, tokens e p95. A candidata altera mais de uma variável. Para atribuir causalidade a temperatura, esforço ou orçamento, varie uma configuração por rodada mantendo as demais fixas. A escolha de modelo é independente por papel em `config/agents.json`. As configurações comparadas ficam gravadas em `summary.json`.

### Interpretar os indicadores

| Indicador | Como ler |
|---|---|
| Resolução confirmada | Conversas com confirmação explícita após orientação / conversas com ao menos um turno. Conversas abertas permanecem no denominador. |
| Transbordo | Conversas encaminhadas / conversas com turno. A fila separa cancelamento legítimo, falha técnica, contestação e outros motivos. |
| Conversão de oferta | Sessões com aceite confirmado / sessões em que uma oferta foi apresentada. É uma conversão simulada e pode ficar indefinida quando não há ofertas. |
| Latência p95 | 95º percentil da duração do motor por turno. O tempo humano de concluir a tarefa é medido no piloto. |
| Tokens e custo | Somatório reportado pelo provedor. Tarifas configuradas permitem estimar USD de inferência por conversa. Valores ausentes aparecem como “Sem medida”. |
| Qualidade | Ação, domínio, fonte e fatos por turno e sucesso integral por conversa. O juiz de linguagem é avaliado à parte, com calibração humana. |

## Como o projeto atende à vaga

| Competência | Onde verificar |
|---|---|
| Orquestração, especialistas, intenção, contexto e transbordo | `central/engine.py`, `central/graph.py`, chat, fila e resumo por ticket |
| System prompts e revisão antes de promover | `prompts/`, impressão digital do candidato, template de PR, `python main.py gate` e CI |
| Tool calling e saída estruturada | `central/provider.py`, `central/tools.py`, testes de protocolo HTTP com Ollama controlado |
| RAG, embeddings, chunking e qualidade da recuperação | `central/knowledge.py`, `knowledge/`, `retrieval.csv` |
| MCP e framework de agentes | Servidor e cliente MCP stdio. Executor LangGraph opcional com teste de paridade |
| Regressão, bordas, juiz LLM e investigação | `tests/`, `evaluation/cases.json`, `central/evaluation.py`, relatórios antes/depois |
| FinOps, esforço, temperatura e compromisso entre qualidade e custo | Configurações por agente, traces de execução, experimento pareado |
| Observabilidade e análise conversacional | `central/storage.py`, `central/analysis.py`, painel, alertas, CSV e gráfico de eventos |
| Colaboração com produto, operação e engenharia | Roteiro de piloto, critério de aceite, protocolo de revisão e runbook |
| Operação em canal conversacional | Chat web implantável localmente, endpoint de saúde e teste HTTP em processo separado. Dados de uma operação comercial dependem de piloto autorizado. |

## Mapa do repositório

| Caminho | Conteúdo |
|---|---|
| `CentralTelecom.sln`, `CentralTelecom.pyproj`, `.vscode/` | Solução Visual Studio, projeto Python e configurações do VS Code |
| `main.py`, `Iniciar.ps1` | Comandos e inicialização no Windows |
| `central/web.py`, `ui/` | API, página, estilos e interação do navegador |
| `central/engine.py`, `graph.py`, `provider.py`, `tools.py` dentro de central | Coordenação, controles de negócio, adaptador de LLM e consultas |
| `central/knowledge.py`, `mcp_client.py`, `mcp_server.py` | Índice, embeddings e transporte das políticas |
| `central/storage.py` | Transações, sessões, tickets, eventos e métricas |
| `central/analysis.py`, `evaluation.py`, `comparison.py`, `release.py` | Perfil de dados, avaliação, comparação entre versões e decisão de promoção |
| `data/`, `knowledge/`, `config/`, `prompts/` | Dados públicos agregados, perfis fictícios, políticas autorais, parâmetros e instruções versionadas |
| `evaluation/`, `tests/`, `scripts/` | Gabaritos, testes de unidade/integração e experimentos executáveis |
| `reports/` | Perfil de dados, avaliação exportada, gráfico, histórico de iterações e resultados reproduzíveis |
| `docs/` | Metodologia, evidências, ambiente, operação e piloto |
| `requirements*.txt`, `Dockerfile`, `.dockerignore`, `.github/` | Dependências, contêiner, integração contínua e revisão de mudanças |
| `runtime/` | Criado ao executar. Banco local e arquivos de análise, ignorados pelo Git |

**Leitura guiada.** [As oito etapas do CRISP-AI](docs/CRISP-AI.md) · [Diagnóstico dos erros e decisão técnica](docs/RESULTADOS.md) · [Piloto e revisão independente](docs/PILOTO.md) · [Implantação, alertas e reversão](docs/RUNBOOK.md) · [Ambiente de validação](docs/AMBIENTE.md).
