# GABRIELCRUZ · Hub Vertical Rio com dados da Rezdy

Mesmas telas do [vertical-rio-hub](https://gabrielcruzverticalrio.github.io/vertical-rio-hub/), alimentadas pela API da Rezdy.

Páginas: `index.html`, `tv_sala_espera.html`, `tv_escritorio.html`, `ipad_operacao.html`, `central_avisos.html`, `hub_financeiro.html`.

## Como os dados chegam
`.github/workflows/sync-rezdy.yml` roda `scripts/sync_rezdy.py` a cada 15 min (07h–21h) e grava `assets/rezdy_dados.js`.
A chave fica no secret `REZDY_API_KEY`; nenhum nome, e-mail ou telefone de cliente é gravado. As TVs recarregam a cada 5 min.

- **Voo** = horário de saída com reservas ativas (produtos no mesmo horário viram um voo só).
- **Pax, reservas, order numbers, status da reserva, duração, capacidade/vagas** vêm da Rezdy.
- **Valores financeiros não são publicados** (repositório público): a tela Financeiro mostra "NÃO PUBLICADO".

## O que NÃO vem da Rezdy
- Pulseira: rodízio automático PRETA, BRANCA, AMARELA, VERDE
- Código do voo (VR101…): gerado em ordem de horário
- Status operacional (check-in, briefing, embarque): pelo horário + iPad
- Clima
- Taxas de plataforma/cartão: % fixo estimado
- Horas voadas: estimadas pela duração do produto

Parâmetros: `?hora=HH:MM` simula outro horário.
