# Design — Correções críticas de segurança (Compras/CompraFlow)

Data: 2026-11-17 · Status: aprovado pelo parceiro humano

## Intenção e porquê

A avaliação técnica do projeto apontou 4 riscos críticos de segurança que podem
ser explorados ou quebrar o sistema hoje: SSO quebrado na imagem Docker
(dependência ausente), brute force no login com senha admin padrão, fluxo de
reset de senha com injeção de URL/token em log, e token de sessão em
`localStorage`. Este design cobre a correção dos quatro.

## Abordagens consideradas (por item)

1. **`cryptography` ausente** — única via: adicionar ao `requirements.txt`.
   Aproveita-se para persistir `SECRET_KEY` em `/data` quando não informada
   (hoje gera aleatória por boot e invalida states OAuth a cada restart).
2. **Rate limiting** — (a) middleware próprio em memória (~40 linhas, sem deps)
   vs (b) `slowapi` (dependência extra, mesmo efeito neste porte). Escolhido: (a).
   **Senha admin padrão** — (a) bloqueio imediato (risco de lockout sem SMTP)
   vs (b) janela de carência pós-seed. Escolhido: (b) — env
   `ADMIN_SENHA_VALIDADE_DIAS` (default 7); após a janela, login com a senha
   padrão é recusado.
3. **Reset de senha** — (a) `base_url` do servidor via env `APP_BASE_URL`
   (valor do cliente só aceito se igual a uma origem permitida); (b) token no
   log apenas com `RESET_TOKEN_EM_LOG=true` (default `false`); (c) invalidar
   sessões do e-mail ao redefinir/alterar senha (`reset.py`, `usuarios.py:174`).
4. **Sessão** — (a) cookie `httpOnly` + `SameSite=Strict` vs (b) endurecer
   `localStorage`. Escolhido pelo parceiro: **(a)** — backend seta o cookie no
   login/callback SSO; `api.js` envia `credentials: "include"`; `deps.py` lê o
   cookie **mantendo Bearer aceito** (testes do adapter e CLI); `sessao.js`
   guarda só os metadados (email/nome/grupo/expiração), não o token; logout
   apaga cookie + sessão no banco.

## Metas

- Fechar os 4 riscos sem regressão dos fluxos existentes (login, SSO, reset,
  adapter REST, CI verde).
- Cada atividade = 1 commit Conventional Commits, com push para `origin/main`.

## Não-metas / anti-metas

- Não migrar para Postgres, não reescrever storage, não introduzir migrations
  (Alembic) neste pacote.
- Não mudar o domínio de negócio nem a UI além do necessário para a sessão.

## Restrições

- SQLite single-file; sem múltiplos workers; container único.
- Testes existentes (script-style) devem continuar passando; comportamento
  novo deve ter cobertura nos testes quando couber.
- Compatibilidade do adapter REST do frontend (`frontend/js/api.js`) com a
  superfície REST de `backend/app/rest.py` deve ser preservada.

## Decisões já tomadas (pelo parceiro)

- Pacote completo aprovado (itens 1–4); item 4 via cookie httpOnly.
- Versionamento garantido: commit por atividade + push.

## O que fica para o executor

- Detalhes de implementação (nome de variáveis internas, ordem dos checks,
  mensagens de erro em pt-BR no estilo existente).
- Ajuste fino dos testes para cobrir os novos comportamentos.
- Atualizar `.env.example`, `DEPLOY.md` e `README` quando envs novas
  forem introduzidas (`APP_BASE_URL`, `RESET_TOKEN_EM_LOG`,
  `ADMIN_SENHA_VALIDADE_DIAS`, `SECRET_KEY` persistida).
