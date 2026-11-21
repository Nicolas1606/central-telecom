# Operar a demonstração

O chat usa uma única instalação local. Duas contas fictícias podem ser selecionadas para testar fatos distintos. A fila e o painel são de operador local. Use um banco novo para cada ambiente, modo e estudo. A chave TELECOM_DB define o caminho. O público do portfólio pode executar sua própria cópia.

| Sinal | Diagnóstico | Ação operacional |
|---|---|---|
| /health sem resposta | Processo ou porta indisponível | Conferir console e PORT. Reiniciar o serviço na mesma pasta. |
| Transferências com falha_validacao | Ver trace_id, chamadas, modelo, fonte e hash do prompt em SQLite. /health informa vitalidade da API, doctor lista modelos. | Reproduzir o caso no modo ollama. Examinar saída inválida, timeout, seleção de fonte e catálogo de ferramentas. Reverter o prompt/configuração e repetir o caso. |
| p95 acima de 10 s | Separar tempo do modelo, tokens e primeira carga de pesos. | Reduzir contexto ou testar menor orçamento. Comparar acerto no mesmo conjunto antes de promover. |
| Aceite indevido ou dados de outra conta | Incidente crítico | Interromper o modo generativo, preservar o banco, voltar à configuração anterior e executar regressão de consentimento e isolamento. |
| HTTP 409 | Outra mensagem chegou primeiro ou a sessão encerrou | Repetir o mesmo envio com sua chave se for retry. Iniciar nova conversa após encerramento. |

O painel calcula alertas sobre os registros do banco atual a cada consulta. Para inspecionar um período, exporte os grupos por dia com `python main.py analyze`. A medição de latência cobre a execução do motor por turno, do roteamento à montagem da resposta. O navegador, a gravação e o tempo de leitura humana ficam fora desse cronômetro. O serviço não envia notificações externas.

## Reversão e persistência

Com o processo parado, faça uma cópia da pasta runtime inteira antes de atualizar (SQLite pode usar arquivos WAL/SHM). Promova código, políticas e configuração sob uma referência Git revisada. Se a atualização falhar, restaure a versão anterior do código e a cópia de dados compatível em outra pasta. Rode os testes, doctor e um caso de cobrança. O identificador do envio impede que um retry contabilize duas conversões ou dois tickets.

## Contêiner e acesso

```powershell
docker build -t central-telecom .
docker run --rm -p 127.0.0.1:8000:8000 -v telecom-runtime:/app/runtime central-telecom
```

A publicação acima expõe o chat apenas no computador anfitrião. Uma instalação pública com clientes exigiria autenticação de cliente e operador, autorização por caso, armazenamento gerenciado, orçamento e retenção de logs acordados. O SQLite e o limite de contexto atendem ao laboratório de baixo volume. Teste de carga, infraestrutura pública e operação contínua são etapas de implantação de um piloto real.

## Análise de custos

Em config/agents.json cada função tem tarifas opcionais por milhão de tokens. Registre moeda USD, data e fonte em um PR quando preencher as tarifas. O sistema multiplica tokens observados por tarifa e soma por conversa. Custo desconhecido aparece como nulo. Em demo, zero chamadas resulta em custo de inferência de API zero. Hardware, energia, armazenamento, trabalho humano e chamadas do juiz offline têm contabilidade separada. Compare configurações com os mesmos casos, repetições e preços antes de alegar economia.

Os totais de tokens e custos se referem a chamadas associadas a turnos persistidos. Custos de tentativas concorrentes descartadas e energia local exigem conciliação com o provedor ou a infraestrutura.
