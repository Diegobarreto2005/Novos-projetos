# Disparador de WhatsApp (CLI + painel web)

Script em Python que dispara mensagens via WhatsApp Web e agora conta com um backend Flask + painel web integrado.

## Como executar o painel

1. Instale dependencias:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Deixe o WhatsApp Web autenticado no navegador padrao.
3. Inicie o backend/servidor web:

```bash
python app.py
```

4. Abra `http://localhost:5000` e use o painel:
   - Cole numeros manualmente ou carregue um CSV (coluna `numero`).
   - Ajuste espera/intervalo entre envios.
   - Envie um teste unico ou dispare a lista inteira.

Observacao: cada envio abre o WhatsApp Web no navegador, espera o tempo configurado e fecha a aba automaticamente. Mantenha a maquina desbloqueada.

## Endpoints rapidos

- `GET /api/defaults`: traz mensagem padrao (de `mensagens/mensagem_padrao.txt` se existir) e tempos configurados.
- `POST /api/send`: corpo JSON `{ numero, mensagem, espera?, intervalo?, ignorar_log? }` envia uma unica mensagem.
- `POST /api/send-batch`: corpo JSON `{ numeros: [], mensagem, espera?, intervalo?, ignorar_log?, ignorar_pywhatkit? }` dispara em lote.

## Uso em linha de comando (script original)

Mantivemos o fluxo antigo para rodar direto no terminal:

```bash
python enviar_whatsapp.py \
  --arquivo dados/clientes.csv \
  --mensagem-arquivo mensagens/mensagem_padrao.txt \
  --espera 12 \
  --intervalo 8
```

Dicas:
- `--numero-teste +5511999999999` faz um envio rapido so para esse numero.
- Ajuste `--espera` (tempo para abrir a conversa) e `--intervalo` (pausa entre disparos) conforme velocidade da maquina.

## Estrutura
- `enviar_whatsapp.py`: funcoes de normalizacao e disparo via pywhatkit.
- `app.py`: backend Flask que chama o script e registra envios.
- `templates/index.html`: painel web.
- `logs/enviados.jsonl`: log local com historico.
- `PyWhatKit_DB.txt`: log criado pela biblioteca pywhatkit.

Envie mensagens somente para contatos que autorizaram recebimento e respeite os termos de uso do WhatsApp.
