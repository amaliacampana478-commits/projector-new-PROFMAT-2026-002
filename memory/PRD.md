# PRD — ENA PROFMAT 2027 (Inscrições + Painel Admin)

## Problema / Objetivo
Aplicação de inscrição de candidatos ao ENA PROFMAT 2027 (fluxo estático HTML/JS em `/app/frontend/public/`) + painel administrativo React (`/donaspainel`). Backend FastAPI + MongoDB. Idioma: **Portuguese (pt-BR)** — responder sempre em pt-BR.

## Arquitetura
- Backend: `/app/backend/` — `server.py`, `admin_routes.py` (rotas `/api`), `pix_generator.py` (BR Code PIX).
- Frontend candidato: páginas estáticas em `/app/frontend/public/*.html` (vanilla JS + Tailwind inline). NÃO usa React.
- Painel admin: SPA React compilada em `/app/frontend/public/donaspainel/`.
- Fluxo candidato usa `sessionStorage` entre etapas; finalização grava via `POST /api/track/registration`.

## Taxa fixa
- Taxa de inscrição = **R$ 90,00** (constante `TAXA_PROFMAT` em `admin_routes.py`), igual ao valor hardcoded do PIX (`/api/pix/*`).

## Implementado (últimas alterações — jun/2026)
- Seletor "Instituição Associada" (`dados-inscricao.html`): ao selecionar mostra "1 instituição selecionada"; recolhe grade + botão "Limpar seleção".
- Achatamento mobile de `confirmacao.html` (sem caixa externa, barras azuis full-bleed, rodapé compacto, título com respiro).
- Cabeçalho mobile em `inscricao-realizada.html`, `pagamento-pix.html`, `minhas-inscricoes.html`: menu hambúrguer (abre dropdown "Minhas inscrições"), bandeira oculta no mobile, layout achatado + rodapé compacto. Desktop mantém botão + bandeira.
- `minhas-inscricoes.html`: botão "Voltar" agora usa `history.back()` (fallback `/candidato`).
- Modal "Aviso importante" na home (`inicio.html`) com logo PROFMAT, cores do padrão (teal `#0c7c92`), botão "OK, entendi". Reaparece a cada carregamento (pendente decidir once-per-session).
- FIX sincronização painel/valores: `TAXA_PROFMAT=90.00` aplicada em gravação de inscrição, listagem (`/api/admin/inscriptions`) e KPIs (`/api/admin/dashboard/kpis`); backfill de inscrições existentes com valor 0 → 90.

## Endpoints-chave
- `POST /api/track/access|registration|pix-generated|pix-copied|pix-downloaded`
- `GET /api/admin/dashboard/kpis` (retorna valor_total, valor_copiados, etc.)
- `GET /api/admin/inscriptions` (lista com `valor` por linha)
- `POST /api/admin/auth/login`, `POST/GET /api/pix/generate|qr.png|code.txt`

## Credenciais teste
- Admin: `donas` / `Seinao10@@`

## Backlog / próximos
- Decidir exibição do modal de aviso (uma vez por sessão vs. sempre).
- Persistência real da inscrição no banco (hoje depende de sessionStorage no fluxo do candidato).
- Aplicar cabeçalho hambúrguer/consistência mobile também em `termos.html`, `inscricao.html`, `dados-inscricao.html`, `confirmacao.html` (se solicitado).
