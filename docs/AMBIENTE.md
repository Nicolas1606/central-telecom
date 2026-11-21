# Ambiente e reprodução

A execução de referência usou Linux x86-64 e Python 3.12.14. Versões observadas dos principais pacotes:

| Pacote | Versão do ambiente testado |
|---|---|
| FastAPI | 0.141.1 |
| Uvicorn | 0.52.1 |
| Pydantic | 2.13.4 |
| HTTPX | 0.28.1 |
| MCP Python SDK | 1.29.0 |
| scikit-learn | 1.8.0 |
| NumPy | 2.3.5 |
| pandas | 2.2.3 |
| Matplotlib | 3.10.8 |

requirements.txt declara faixas compatíveis para instalação e resolução de dependências no sistema utilizado. A primeira instalação precisa acessar o índice de pacotes. O Visual Studio no Windows deve ter o workload Python habilitado. O projeto abre por CentralTelecom.sln no Visual Studio e por pasta no VS Code. A validação desta entrega foi feita pela CLI; a interface do IDE no Windows e o build do contêiner aguardam execução no ambiente de destino.

### Execuções verificadas

- Perfil de dados e inventário de seis passagens, suíte pública com 34 conversas e 40 turnos, geração de CSV, JSONL, matriz de confusão e gráfico.
- Servidor Uvicorn real em porta local, navegador cliente substituído por cliente HTTP no teste de implantação. Verificados HTML, JS, CSS, API, fluxo com duas intenções, ticket, revisão, métricas e exportação de eventos com pandas.
- Servidor e cliente MCP reais em processos distintos para listar e invocar a ferramenta. O cliente opcional do motor também recuperou a fonte durante uma orientação de cobrança.
- Ollama 0.11.10 executou modelos Qwen3 em CPU, com hashes registrados em cada manifest.json. Os traces incluem uso do modelo, chamadas nativas, ferramenta proposta, passagem recuperada e motivos de falha.
- LangGraph 1.2.24 executou as rotas e a suíte de integração. O teste HTTP também iniciou o servidor com Ollama e fila protegida. O arquivo reports/ambiente.json registra as versões efetivamente vistas na reconstrução e tem precedência sobre a tabela histórica acima. Os testes automatizados desta entrega estão em reports/testes.md. O pipeline de GitHub Actions foi fornecido para o repositório de destino.
- O JavaScript passou pela verificação de sintaxe. O Chromium local não conseguiu iniciar o processo de renderização neste ambiente. Para reproduzir a navegação visual, instale `playwright`, execute `python -m playwright install chromium`, inicie o servidor demo em banco separado e rode `python scripts/browser_smoke.py`. O teste cria uma conversa e marca o ticket criado como revisado, portanto use um banco de teste.

### Reproduzir com o mesmo ambiente de referência

Em uma instalação Python 3.12 na arquitetura suportada, `python -m pip install -r requirements.txt -c constraints-reference.txt` reproduz as versões diretas observadas. Dependências transitivas são resolvidas pelo pip. Para Python 3.14 use o requirements.txt sem essas restrições. O script Windows reutiliza o ambiente .venv desta pasta.
