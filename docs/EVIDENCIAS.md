# Resultados e decisão de produto

**Disponibilizar o chat para demonstrações e um piloto supervisionado.** O modelo consultou dados da conta fictícia e entregou uma orientação que um operador consegue conferir. A primeira execução com frases novas mostrou falhas de interpretação. A correção foi novamente exercitada nos mesmos casos. Uma equipe pode usar esse histórico para decidir quais tarefas merecem teste com usuários.

## O que mudou no atendimento

| Execução | Amostra | Resultado e decisão |
|---|---|---|
| Generalista e multiagente com chamada nativa | 5 diálogos, 7 turnos, duas execuções de cada | Ambos obtiveram 0/14 turnos integralmente corretos. A inspeção dos traces revelou seleção simultânea de áreas irrelevantes, chamadas de ferramenta inválidas e falha segura para a fila. Um segundo turno bloqueado após fechamento também conta como erro. |
| Roteamento ancorado e plano JSON | Os mesmos 14 turnos por braço | 6/14 quando o LLM também selecionou a passagem. 14/14 quando a primeira passagem compatível pôde ser verificada pelo servidor. A comparação isola a mudança na seleção de fonte entre esses dois braços. |
| Expansão para todas as conversas conhecidas | 34 conversas, 40 turnos | A configuração enxuta acertou 34/40. O modelo roteou assunto externo para encerramento e transferiu um pedido incompleto antes de dar ao cliente chance de esclarecer. |
| Controle de escopo | Mesmos 40 turnos | 39/40 após fazer a triagem inicial por escopo explícito. O único desacordo restante, V08, pede esclarecimento onde o gabarito presume uma consulta de fatura. O gabarito original foi conservado. |
| Doze novas formulações congeladas no Git | 12 conversas novas, um turno por conversa | **8/12 no primeiro contato**, 9/12 ações corretas. Houve falha de fonte em cobrança “duas vezes”, encerramento por uma hipótese, e encaminhamentos ao pedir para “pagar menos” ou “dar uma força”. |
| Correção e regressão | As mesmas 12 formulações | **12/12** após reconhecer as paráfrases, conferir intenção condicional e selecionar a política esperada entre as efetivamente recuperadas. Os 12 casos agora fazem parte da regressão pública. |

Na candidata final, o replay das 34 conversas também manteve **39/40**, 33 conversas integralmente corretas, p95 de **1,45 s**, 31 chamadas e 5.431 tokens. Duas conversas tiveram confirmação de resolução, 14 foram encaminhadas e duas das três ofertas foram aceitas. São desfechos definidos pelas mensagens do replay.

Os tempos são da CPU local e incluem variação de carga e carregamento dos pesos. Dois replays de um mesmo diálogo compartilham o enunciado. Os 14 turnos do experimento pareado correspondem a sete posições de turno distintas. A decisão automática exige ação, domínio, fonte, conteúdo solicitado e motivo quando especificado. A verificação textual por fragmentos cobre apenas os fatos do gabarito.

## FinOps e seleção de modelo

| Medida em dez sessões reproduzidas | Plano estruturado | Verificação da primeira passagem compatível |
|---|---:|---:|
| Chamadas ao LLM | 24 | 12 |
| Tokens de entrada | 5.414 | 1.972 |
| Tokens de saída | 324 | 124 |
| Turnos aprovados | 6/14 | 14/14 |
| p95 do motor | 3,38 s | 1,34 s |
| Cenário ilustrativo de USD por conversa | 0,000639 | 0,000234 |

O consumo observado caiu de 5.738 para 2.096 tokens, aproximadamente 63,5%. O cenário usa USD 1 por milhão de tokens de entrada e USD 3 por milhão de saída, escolhidos para ilustrar o cálculo. A máquina local também consome energia e tempo de computação. A fatura real e o custo total de operação não foram medidos. O script preserva valores desconhecidos nas rodadas com telemetria incompleta.

```powershell
python scripts/finops.py reports/validacao_llm reports/correcao_llm --entrada 1 --saida 3 --csv runtime/meus_custos.csv
```

No piloto, o roteador usa regras de escopo e de consentimento. Os três especialistas usam Qwen3 0.6b, temperatura zero, think desativado e teto de 96 tokens para tomar uma decisão estruturada curta. A seleção de ferramenta só produz efeito após verificação do domínio e da conta pelo servidor. A candidata final busca a política determinada pelos fatos entre os resultados da recuperação. O juiz Qwen3 1.7b fica fora da conversa do cliente, temperatura zero e até 128 tokens para o parecer.

Os braços single, multi, prompt, economico, temperatura, maior e esforco registram as opções de cada papel e os resultados originais. Trocar apenas o prompt do roteador ou aumentar a temperatura não recuperou o fluxo inicial. O braço de maior esforço altera think e o teto de tokens. Rodadas com erros de inferência têm custos ausentes. Seria incorreto atribuir a esses testes uma superioridade geral de modelos menores ou maiores.

## Quando confiar no juiz

Na avaliação de sete turnos do braço enxuto, o contrato automático aprovou os sete. O juiz aprovou três e reprovou quatro, incluindo uma confirmação de resolução. Nas três sondas controladas adicionais, aceitou a fatura correta, reprovou o valor alterado e reprovou o aceite inventado. São dois testes diferentes. Acertar erros explícitos não autoriza o juiz a decidir a qualidade geral da operação. Use sua justificativa para priorizar revisão e calibre com parecer humano antes de usá-lo como critério de promoção.

## Auditar ou reproduzir

- [Rastreio das variantes iniciais](../reports/validacao_llm), [ablação de fonte](../reports/correcao_llm) e [CSV comparativo](../reports/finops.csv).
- [Replays anteriores no conjunto completo](../reports/amostra_completa) e [controle de escopo](../reports/candidato).
- [Primeira execução das novas perguntas](../reports/novas), [nova execução após a correção](../reports/regressao_novas) e [candidata final nas 34 conversas](../reports/final).
- [Juiz por turno](../reports/juiz_llm), [sondas do juiz](../reports/controles_juiz.json), [resultado do estudo com participantes](../reports/estudo_pendente.json).
- [Chat HTTP integrado com o modelo](../reports/chat_final.json), [dados de campo](CAMPO.md) e [desenho da revisão humana](PILOTO.md).

Cada pasta de benchmark contém manifest.json com versão do Ollama e digests dos modelos. Cada rodada preserva configuração, decisões por etapa, resultados por turno, matriz de ações e motivos dos erros. Diretórios públicos de regressão registram evidência de engenharia. O próximo teste de generalização exige casos privados inéditos e revisão cega.
