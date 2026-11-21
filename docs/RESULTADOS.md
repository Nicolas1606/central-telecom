# Histórico do desenvolvimento do modo por regras

Os experimentos posteriores com o modelo real estão em [EVIDENCIAS.md](EVIDENCIAS.md).

A unidade avaliada é um turno de atendimento. Para acertar um turno, a aplicação precisa emitir a ação, selecionar as áreas na ordem esperada, citar o conjunto de políticas do gabarito, incluir os fatos numéricos ou trechos de referência e acertar o motivo quando especificado. Algumas verificações textuais por substring deixam passar outras frases indevidas. A revisão humana avalia a orientação completa.

| Observação | Hipótese | Alteração e verificação |
|---|---|---|
| C06 informou apenas o valor quando o cliente relatou cobrança “duas vezes”. | A detecção de contestação cobria “duplicada” e perdia a paráfrase. | Ampliada a regra. O mesmo caso passou a gerar ticket e política FAT-02. |
| C07 encaminhou a expressão “fiquei offline”. | A palavra utilizada pelo cliente faltava no roteamento de suporte. | A ampliação de vocabulário levou à passagem NET-02 e ao teste inicial da conexão. |
| C10 ativou cobrança em “mais em conta”. | O termo “conta” tinha significado ambíguo no contexto de preço. | Normalizada a expressão antes da identificação de domínios. A orientação preservou somente a oferta. |
| V06 encaminhou “não preciso de atendente”. | A regra de preferência humana verificava apenas a presença do substantivo. | O pedido negado perdeu prioridade na triagem. A repetição explicou o valor do boleto. |
| V08 diz apenas que “o valor de sempre mudou”. | O gabarito pressupõe fatura. O cliente também pode estar se referindo ao plano ou à oferta. | A versão entregue pede contexto. O gabarito original foi preservado e o caso continua contado como erro. Produto e operação devem arbitrar o desfecho desejado antes de outra rodada privada. |

### Leitura de negócio

Os dados públicos da Anatel motivam os três domínios. O experimento mostra se a central segue as regras definidas para esses domínios em condições controladas. O encaminhamento de um pedido inequívoco de cancelamento é acerto de atendimento. A redução indiscriminada do transbordo incentivaria o comportamento contrário ao interesse do cliente.

No replay de 34 conversas, três sessões receberam oferta e duas registraram aceite. Apenas duas confirmaram resolução depois de receber orientação. Outras conversas encerram seu roteiro imediatamente após uma resposta. Esses números refletem o desenho dos casos e ilustram o cálculo dos indicadores. Economia financeira, aumento de conversão e redução no tempo dos usuários dependem de observação no campo.

### Onde auditar

- `reports/iterations/inicial.csv` preserva o primeiro replay de desenvolvimento/desafio.
- `reports/iterations/primeira_verificacao.csv` preserva o primeiro contato da central com as oito perguntas adicionais.
- `reports/example/turns.csv`, `falhas.csv` e `traces.jsonl` permitem reconstruir os resultados finais. O desafio e a verificação reutilizados são públicos e orientaram correções.
- `reports/example/retrieval.csv` contém a recuperação para perguntas que têm fonte esperada. Recall@3 é a proporção das referências esperadas presente nos três primeiros resultados, com média por turno.
- `reports/example/summary.json`, `confusao.csv` e `avaliacao.png` descrevem a rodada. `gate.json` registra a decisão sobre promoção.
- `human_review.csv` inicia vazio. O estudo com participantes e o teste com perguntas privadas podem ser executados pelo roteiro do piloto.

### Decisões de engenharia

A resposta catalogada depende de fatos consultados no momento do atendimento. O modelo pode escolher uma ferramenta e recuperar evidência sem adquirir permissão para alterar contratos. O histórico persistido conserva contexto operacional suficiente para um atendente entender a orientação anterior. A entrada livre dos usuários foi excluída dos eventos persistidos para minimizar exposição.

O arquivo router.v1.txt preserva a estratégia inicial de assunto dominante. router.v2.txt inclui intenções compostas e saídas de triagem exclusivas. Essa é uma hipótese de melhoria de prompt. Os resultados antes/depois observados acima são do motor por regras. Para atribuir um ganho ao prompt, copie a configuração, mude apenas prompt_version do roteador, execute a mesma amostra com Ollama e use compare. Registre digest do modelo, temperatura, orçamento, repetições e custos observados no PR.
