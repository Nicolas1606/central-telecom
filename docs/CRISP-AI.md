# CRISP-AI aplicado ao atendimento de telecom

Adotamos as oito fases da formulação de Sergio Gaiotto (2024), uma adaptação do CRISP-DM para projetos de IA. A implementação itera entre avaliação, diagnóstico e modelagem. Os resultados do laboratório, a implantação local e as tarefas de campo têm evidências próprias. [Referência metodológica](https://falagaiotto.com.br/coluna/Metodo-para-Desenvolvimento-com-IA-Introducao-ao-CRISP-AI.html)

## 1. Compreensão do negócio e do problema

Um cliente que pergunta por que a fatura subiu e diz que talvez cancele tem duas necessidades. Consultar a fatura exige dados atuais. Iniciar um encerramento exige entender se há um pedido definitivo. Uma única taxa de retenção incentiva decisões ruins se o cliente precisa insistir para chegar a um atendente.

Hipótese de produto: especialistas com ferramentas delimitadas conseguem orientar, pedir esclarecimento e encaminhar com contexto. Hipótese experimental: a separação em especialistas pode reduzir erros de ferramenta o suficiente para justificar o custo de coordenação. O experimento compara essa arquitetura a um generalista com as mesmas contas, políticas e critérios. O resultado dessa comparação com LLM real precisa ser coletado.

A operação brasileira de telecom fornece contexto para a escolha. Em 2025, cobrança, qualidade/funcionamento/reparo e cancelamento somaram 849.094 das 1.354.791 reclamações registradas na Anatel, cerca de 62,7%. O recorte descreve reclamações na agência. A prevalência em uma central específica depende de seus próprios dados. Arquivo de origem e cálculo em data/anatel_reclamacoes.csv e reports/data_profile.json. [Panorama Anatel 2025, tabela Reclamações por assunto](https://www.gov.br/anatel/pt-br/assuntos/noticias/anatel-registra-aumento-nas-reclamacoes-de-servicos-de-telecomunicacoes-em-2025/panorama_de_reclamacoes_2025.pdf)

Produto acompanha resolução confirmada e erros críticos. Operação revisa os casos encaminhados. Engenharia mantém contrato das ferramentas, rastreabilidade e regressão. O roteiro do piloto descreve a coleta com participantes.

## 2. Compreensão dos dados e do conhecimento

Há três granularidades. A série pública cobre três anos agregados. O CRM fictício contém dois perfis operacionais com valores em centavos, uma região, estado da rede e elegibilidade. A base de conhecimento contém seis políticas autorais. A avaliação usa 34 conversas com 40 turnos rotulados e inclui confirmações, retornos e pedidos compostos.

`python main.py profile` confere referências, IDs, integridade das contas e valores de fatura. Gera distribuição de ações, contagem de fontes, presença de nulos e participação dos três assuntos por ano. O simulador cobre duas regiões e poucos perfis linguísticos. O corpus de avaliação reflete decisões de projeto. Para estimar frequência operacional de falhas, meça sessões do próprio canal durante um piloto.

## 3. Preparação dos dados e do conhecimento

O índice separa o Markdown por seção de política. Cada passagem preserva documento, ID e hash SHA-256. Um trecho contém a regra completa, o que permite ao analista verificar sua aplicação. Texto e aliases passam por normalização de caixa e acentos.

A busca lexical usa TF-IDF com termos simples e pares de palavras. A representação densa usa decomposição SVD de quatro dimensões, ajustada exclusivamente nas políticas. São embeddings de semântica latente adequados a uma demonstração pequena. A busca híbrida soma 70% da similaridade lexical e 30% da similaridade densa. Os pesos são uma hipótese de engenharia. O relatório mede as três alternativas com a pergunta original.

O especialista também recebe o estado da ferramenta ao buscar uma política. O benchmark de busca usa a pergunta pura para evitar atribuir ao recuperador informações já conhecidas pelo motor. Os perfis são vinculados no servidor. Dados do texto da conversa ficam fora dos logs de operação, que preservam respostas controladas e metadados. Os textos em traces.jsonl no benchmark pertencem aos casos de avaliação fornecidos.

## 4. Desenvolvimento e modelagem

O roteador determina os domínios a tratar. Uma intenção composta gera uma execução por domínio e uma decisão final com precedência de transbordo, esclarecimento, oferta e orientação. O generalista experimental recebe todas as ferramentas permitidas da demonstração e conduz as mesmas etapas com um único papel. O comparativo mantém o número de etapas controlado para estudar a especialização de prompts e permissões.

No modo Ollama, o modelo recebe o contrato de ferramentas, faz a chamada, recebe o resultado como mensagem de ferramenta e seleciona uma passagem sob um esquema. Python valida fonte, domínio, parâmetros e política aplicável. A resposta final é renderizada a partir dos fatos verificados. Nenhum agente tem permissão para modificar a fatura ou efetivar cancelamento. Um aceite exato, na presença de uma oferta pendente, grava conversão simulada uma única vez.

| Papel | Configuração inicial | Justificativa e experimento |
|---|---|---|
| Roteador | qwen3:4b, temperatura 0, think desligado, 256 tokens | JSON curto, orçamento pequeno. Testar 128 tokens e medir perda de intenções compostas. |
| Cobrança | Mesmo modelo, temperatura 0, 256 tokens | Valores vêm da ferramenta em centavos. Variação textual acrescenta pouco ao contrato. |
| Suporte | Mesmo modelo, temperatura 0, 256 tokens | A comparação candidata usa 0,1 para verificar variação na seleção de fonte e transbordo. |
| Cancelamento | Mesmo modelo, temperatura 0, 256 tokens | A candidata habilita think e permite 768 tokens. Medir se resolve ambiguidades sem atrasar pedidos diretos. |
| Juiz offline | Mesmo modelo inicialmente, temperatura 0,1, think ligado, 1.024 tokens | Avalia tarefa, fatos, ação e fonte. Um segundo avaliador e a revisão humana medem viés compartilhado. |

Ollama já fazia parte do ambiente informado pelo autor. Um único modelo inicial reduz download e troca de pesos. Cada papel aceita outro modelo em config/agents.json. Substitua por um modelo local com suporte às capacidades utilizadas e registre o nome e o digest observado em `ollama list`. Think controla a opção de raciocínio do modelo e num_predict limita os tokens de saída.

O executor nativo favorece a leitura do fluxo no depurador. O adaptador LangGraph representa despacho e especialistas como nós e arestas condicionais. O transporte MCP opcional publica e consulta as mesmas políticas via stdio. O isolamento das ferramentas de negócio é aplicado em ambos os executores.

## 5. Avaliação e validação

O gabarito exige ação, ordem dos domínios, fontes, fatos esperados e motivo, quando especificado. O conjunto de desenvolvimento tem 16 conversas. Os dez desafios públicos foram usados para diagnóstico e viraram regressão. Oito novos casos formaram a primeira verificação da implementação ajustada. Os resultados da repetição após inspecionar esses oito casos são identificados no relatório.

Os testes cobrem fluxo HTTP, estado entre turnos, concorrência, idempotência, saída inválida, ferramenta fora de escopo, fonte inventada e protocolo MCP em processo separado. A inferência de contrato usa um provedor HTTP controlado. A avaliação com pesos reais é executada via Ollama e grava consumo e latência observados. Critérios humanos e calibração do juiz estão em PILOTO.md. A comparação pareada exige os mesmos casos e repetições.

## 6. Implementação e implantação

FastAPI oferece sessão, turno, fila, revisão, métricas e documentação interativa. Uvicorn serve o chat e a API no mesmo processo. SQLite confirma a transição e o ticket na mesma transação. Revisão otimista evita aplicar simultaneamente dois turnos sobre a mesma versão da sessão. As chaves de envio permitem repetir uma requisição após perda da resposta.

O teste de implantação inicia um processo Uvicorn, envia mensagens pela porta HTTP, revisa o ticket, consulta métricas e gera uma análise com pandas. O pacote inclui um Dockerfile, CI com Windows e Linux e configurações das duas IDEs. O alvo validado nesta entrega é a implantação local em Linux com Python 3.12. A esteira é fornecida para execução no GitHub.

## 7. Monitoramento pós-implantação e manutenção

Cada turno registra ID, ação, motivo, duração e passagens. Cada chamada ao modelo registra papel, modelo, versão e hash do prompt, duração, sucesso, tokens e custo imputado, quando disponível. A fila mantém orientações anteriores para reduzir repetição no atendimento. A marca de revisão permite acompanhar se a operação recebeu o encaminhamento.

O painel calcula taxas com denominadores documentados no README. A análise exporta volume por dia e domínio e distribuição de motivos. O runbook orienta investigação de aumento em falhas, latência e aceites indevidos. A revisão de uma política envolve atualizar texto, reconstruir o índice no início da aplicação, conferir a mudança de hash e repetir regressão e avaliação reservada.

## 8. Documentação e compartilhamento de conhecimento

O README inicia pela demonstração e leva à arquitetura, às métricas e aos comandos. O relatório técnico aponta casos individuais e o conflito entre gabarito e esclarecimento no caso V08. O roteiro do piloto estabelece papéis de produto, operação e engenharia, coleta cega e critério de promoção. O template de PR pede hipótese, evidência, regressão e reversão. Uma pessoa nova no projeto pode reproduzir os casos sem dados privados.
