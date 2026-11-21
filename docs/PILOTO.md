# Ensaio com pessoas e revisão independente

Produto define o desfecho, operação escreve tarefas inéditas e engenharia congela configuração e prompts antes de ver as respostas. Uma pessoa pode acumular papéis no ensaio do autor. Registre explicitamente quem fez a revisão independente no piloto.

1. Prepare duas variantes equivalentes de cada família de tarefa com contas fictícias. Por exemplo, conciliar uma fatura com e sem adicional, diagnosticar conexão com e sem ocorrência. Evite as frases presentes em evaluation/cases.json. Guarde o arquivo privado fora do Git.
2. Para comparar com o trabalho manual, recrute cinco participantes e distribua duas famílias por pessoa. Cada par contém uma tentativa com documentação e extratos e outra com chat, com variantes diferentes. Alterne a ordem e sorteie a variante para reduzir o efeito de aprendizagem. Dez pares representam vinte tentativas.
3. Cronometre da leitura do enunciado até a entrega da orientação revisada. Inclua esperas e leitura da fonte. Grave um identificador anônimo, tarefa, condição, ordem, segundos e produto entregue. Registre desistências e falhas.
4. Uma pessoa avalia a solução sem ver condição ou tempo. Exija política correta, valores corretos, resolução ou transbordo apropriado e respeito ao consentimento. Desacordos passam por adjudicação. Separe uma planilha com chave de correspondência.
5. Calcule a mediana de 100 × (tempo manual − assistido) / tempo manual nos pares completos. Informe quantidade de pares válidos, acertos e erros críticos por condição. Meta ilustrativa de viabilidade: redução mediana de 20% sem perda de correção. Dez pares constituem um piloto exploratório.
6. Para o teste privado do software, use o esquema do JSON público com split "private". Rode `python main.py evaluate --mode ollama --cases caminho/privado.json --split private --judge`. A avaliação verifica ações e fontes por turno. Na pasta gerada, preencha human_review.csv (pass/fail) de forma cega a turns.csv e rode `python main.py calibrate CAMINHO_DA_EXECUCAO`. Há detalhes da orientação em traces.jsonl. Proteja arquivos locais de estudo.

**Decisão de promoção proposta**: ≥95% de turnos corretos, ≥90% de ações corretas e zero aceitações indevidas observadas na amostra privada, custo conhecido e latência dentro do orçamento acordado. Inspecione cada caso, o denominador e o intervalo de incerteza. Distingua resolução confirmada de resposta emitida. A liberação comercial depende de revisão da operação e do cliente.

## Reunião de demonstração

Produto apresenta uma fatura e pergunta o que uma solução útil precisa entregar. Engenharia demonstra o fluxo e abre o trace correspondente. Operação confere o motivo do transbordo e o resumo recebido. Cada parte registra no PR uma alteração concreta e sua condição de aceite. Os papéis são um roteiro de colaboração para uma execução futura.

## Verificação do candidato

Registre ao menos 20 casos inéditos com `split` igual a `private`, cobrindo orientação, esclarecimento e transbordo. Preencha em human_review.csv as colunas human_grade (pass/fail), critical_error (true/false) e reviewer (pseudônimo do revisor independente). Salve em CSV UTF-8 separado por vírgulas. Para avaliar a concordância do juiz, rode calibrate. Para a decisão técnica, execute `python main.py gate CAMINHO_DA_EXECUCAO` com a mesma AGENT_CONFIG usada na coleta. O comando lista cada critério e retorna código 2 quando faltam evidências. Confere o hash do código, dos prompts, das políticas e da configuração, p95 ≤ 10 s e a presença de preço de inferência. O responsável também compara custo ao orçamento financeiro combinado. A ferramenta não autentica revisores e não consegue comprovar sozinha que as perguntas ficaram reservadas.
