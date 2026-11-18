# Correções Críticas de Segurança — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar os 4 riscos críticos de segurança do CompraFlow (SSO quebrado na imagem, brute force no login, reset de senha inseguro, token em localStorage) com um commit por atividade e push para `origin/main`.

**Architecture:** Backend FastAPI + SQLite; frontend SPA vanilla sem build. Todas as mudanças seguem o padrão existente: lógica em `routers/`, superfície REST em `rest.py` (envelope `{ok, data|erro}` → HTTP), testes script-style em `backend/tests/`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, bcrypt, authlib; JS vanilla; Docker Compose + Caddy.

**Spec:** `docs/superpowers/specs/2026-11-17-correcoes-criticas-seguranca-design.md`

## Global Constraints

- Sem mudança de schema do banco (sem Alembic neste pacote) — nada de colunas novas em `models.py`.
- Commits Conventional Commits em pt-BR, um por task, com push para `origin/main` ao fim de cada task.
- Suítes existentes (`test_rest.py`, `test_sso.py`, `test_import.py`) devem continuar passando.
- Mensagens de usuário em pt-BR, no estilo dos routers existentes.
- Compatibilidade do adapter REST (`frontend/js/api.js`) com `rest.py` deve ser preservada (Bearer continua aceito).

## Review Focus

- Escritório atrás de NAT compartilhado: limite de 10 tentativas/15min por **IP+rota** (configurável via `RATE_LIMIT_TENTATIVAS`) — comportamento esperado: 429 com mensagem clara. Teste: Task 2.
- Mensagem de bloqueio da senha admin **não** pode casar com a regex `MSG_SESSAO` ("sessão expirada") de `rest.py:27`, senão vira 401 e apaga sessão. Teste: Task 2.
- Deploy sobre banco existente: sessões antigas em `localStorage` (com token) continuam funcionando via Bearer — compatibilidade regressiva. Teste: Task 4.
- `#/sso-ok` precisa entrar na whitelist de rotas públicas em `frontend/js/router.js` e `frontend/js/app.js`, senão o callback SSO vira redirect infinito pro login. Verificação: Task 4.
- Rate limit **não** deve derrubar `test_rest.py` (que faz vários logins seguidos): default 10 tentativas e o novo suíte fixa o próprio valor via env antes do import. Teste: Task 2.

---

### Task 1: Dependência `cryptography` + `SECRET_KEY` persistida

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/config.py` (bloco SSO, linha ~49)
- Test: `backend/tests/test_seguranca.py` (novo — reutilizado pelas Tasks 2–4)

**Interfaces:**
- Consumes: nada.
- Produces: `config.SECRET_KEY: str` nunca mais vazio (lida de `SECRET_KEY` env ou de `<DATA_DIR>/secret_key`, criando-o se preciso). Tasks 2–4 só consomem `config`.

- [ ] **Step 1: Commit do design doc (separado, docs)**

```bash
git add docs/superpowers/
git commit -m "docs: design e plano das correções críticas de segurança"
```

- [ ] **Step 2: Adicionar `cryptography==44.0.0` a `backend/requirements.txt`** (ordenada alfabeticamente após `bcrypt`). Rodar `pip install -r backend/requirements.txt` para validar a resolução.

- [ ] **Step 3: `config.py` — `_carregar_secret_key()` chamada no import no lugar de `os.environ.get("SECRET_KEY", "")`:** se env `SECRET_KEY` setada, usar; senão ler `<DATA_DIR>/secret_key`; se não existir, `os.makedirs(DATA_DIR, exist_ok=True)` e gravar `os.urandom(32).hex()` com permissão 0600 (`os.open` com `mode=0o600`). Assinatura: `_carregar_secret_key() -> str`.

- [ ] **Step 4: Teste em `backend/tests/test_seguranca.py`** (estilo do repo: env antes do import, `check()`/print). Casos: (a) com `SECRET_KEY` env vazia e `DATA_DIR` temporário, `config.SECRET_KEY` é string de 64 hex; (b) recarregar o módulo (`importlib.reload`) devolve **a mesma** chave (lida do arquivo); (c) arquivo criado não é world-readable. Comando do suíte: `python backend/tests/test_seguranca.py`.

- [ ] **Step 5: Rodar `python backend/tests/test_seguranca.py` — PASS; depois `python backend/tests/test_rest.py` — PASS.**

- [ ] **Step 6: Commit + push**

```bash
git add backend/requirements.txt backend/app/config.py backend/tests/test_seguranca.py
git commit -m "fix: adiciona cryptography à imagem Docker e persiste SECRET_KEY em /data"
git push
```

### Task 2: Rate limiting + janela de carência da senha admin

**Files:**
- Create: `backend/app/rate_limit.py`
- Modify: `backend/app/config.py` (novas envs), `backend/app/main.py` (middleware), `backend/app/routers/auth.py:24-63` (bloqueio da senha padrão), `backend/app/seed.py:12-29` (arquivo-sentinel)
- Modify: `docker-compose.yml` + `.env.example` (novas envs)
- Test: `backend/tests/test_seguranca.py`

**Interfaces:**
- Produces (`rate_limit.py`):
  - `LIMITADAS: set[str]` — paths protegidos (`"/api/auth/login"`, `"/api/auth/cadastro"`, `"/api/auth/reset/solicitar"`, `"/api/auth/reset/redefinir"`)
  - `def chave(request) -> str` — `ip:rota`
  - `def verificar(chave: str) -> None` — lança `ErroNegocio("Muitas tentativas. Aguarde alguns minutos e tente novamente.")` ao exceder; registro com janela deslizante em memória (`dict[chave, list[timestamp]]`).
- Produces (`config.py`): `RATE_LIMIT_TENTATIVAS: int` (default `10`), `RATE_LIMIT_JANELA_MIN: int` (default `15`), `ADMIN_SENHA_VALIDADE_DIAS: int` (default `7`; `0` desativa o bloqueio).
- Produces (`seed.py`): arquivo `<DATA_DIR>/admin_seed_em` com timestamp ISO — criado no seed **e** na 1ª execução sobre instalação existente sem o arquivo (para não bloquear deployments antigos de imediato).
- Consumes (auth.py): `rate_limit` não é usado lá; o bloqueio usa `config.ADMIN_SENHA_VALIDADE_DIAS` + arquivo sentinel + `security.verificar_senha(config.ADMIN_SENHA_PADRAO, ...)` (já existe em `auth.py:50-52`).

- [ ] **Step 1: Teste que falha primeiro (acrescentar ao `test_seguranca.py`, suíte própria com env `RATE_LIMIT_TENTATIVAS=3` e `ADMIN_SENHA_VALIDADE_DIAS=1` setadas ANTES de importar `app.main`; usa `TestClient` e DATA_DIR temporário):**
  - 3 logins errados seguidos em `/api/auth/login` → 4ª tentativa responde `429` com "Muitas tentativas".
  - Com sentinel `<DATA_DIR>/admin_seed_em` datado de `agora - 2 dias`, login admin/senha padrão → `400`, mensagem contém "senha provisória" e **não** contém "sessão expirada".
  - `ADMIN_SENHA_VALIDADE_DIAS` fixa em 1 no env do suíte; para o caso "dentro da janela", `httpx`-free: mock simples não necessário — o 429 já cobre o middleware; o caso dentro-da-janela fica implícito no `test_rest.py` (login admin123 → 200).
  Rodar: `python backend/tests/test_seguranca.py` → os casos novos FALHAM (429 não existe; bloqueio não existe).

- [ ] **Step 2: Implementar `rate_limit.py`** (limpador lazily a cada `verificar`: descarta timestamps fora da janela; guarda apenas `config.RATE_LIMIT_TENTATIVAS` últimos). Sem dependências.

- [ ] **Step 3: Middleware em `main.py`** (antes de incluir o router): para `request.url.path` em `rate_limit.LIMITADAS` e método POST, `rate_limit.verificar(chave(request))`; captura `ErroNegocio` → `HTTPException(429, e.mensagem)`. IP: `request.client.host` (protegido pelo proxy).

- [ ] **Step 4: Bloqueio em `auth.py`** — no bloco que hoje só sinaliza `troca_senha_obrigatoria` (linhas 50-52), **antes** de criar a sessão: se `verificar_senha(ADMIN_SENHA_PADRAO)` e `config.ADMIN_SENHA_VALIDADE_DIAS > 0`, ler sentinel `<DATA_DIR>/admin_seed_em` (ausente → tratar como agora); se `security.agora() > sentinel + validade_dias`, retornar `{"ok": False, "erro": "A senha provisória do administrador expirou. Redefina a senha em 'Esqueci minha senha'."}`. Mensagem não contém "sessão".

- [ ] **Step 5: Sentinel em `seed.py`** — em `garantir_admin`, após o early-return de conta existente, se o arquivo não existe, criá-lo com `security.agora().isoformat()`.

- [ ] **Step 6: Env no `docker-compose.yml` (bloco api) e `.env.example`**: `RATE_LIMIT_TENTATIVAS`, `RATE_LIMIT_JANELA_MIN`, `ADMIN_SENHA_VALIDADE_DIAS` (com os defaults acima e comentário de uma linha cada).

- [ ] **Step 7: Rodar `test_seguranca.py` (PASS) e depois `test_rest.py`, `test_sso.py`, `test_import.py` (PASS — atenção: `test_rest.py` faz ~5 logins; default 10 não deve disparar 429).**

- [ ] **Step 8: Commit + push**

```bash
git add backend/app/rate_limit.py backend/app/config.py backend/app/main.py backend/app/routers/auth.py backend/app/seed.py backend/tests/test_seguranca.py docker-compose.yml .env.example
git commit -m "feat: adiciona rate limiting ao login/reset e janela de carência para a senha admin padrão"
git push
```

### Task 3: Fluxo de reset de senha

**Files:**
- Modify: `backend/app/config.py` (envs novas), `backend/app/routers/reset.py:33-108`
- Modify: `docker-compose.yml` + `.env.example` + `DEPLOY.md` (seção curta sobre SMTP/APP_BASE_URL)
- Test: `backend/tests/test_seguranca.py`

**Interfaces:**
- Consumes: `config.CORS_ORIGINS: list[str]` (já existe).
- Produces (`config.py`): `APP_BASE_URL: str` (default `""`), `RESET_TOKEN_EM_LOG: bool` (default `False`).
- Produces (`reset.py`): `def _base_permitido(cliente: str) -> str` — devolve a base a usar: `APP_BASE_URL` tem prioridade; senão o valor do cliente se sua origem (scheme://netloc) constar em `APP_BASE_URL` ∪ `CORS_ORIGINS`; senão `""` (corpo do e-mail traz só o código).

- [ ] **Step 1: Testes que falham primeiro (acrescentar ao `test_seguranca.py`, suíte com env `APP_BASE_URL=https://compras.ms.senai.br`, `SMTP_HOST=""`, `RESET_TOKEN_EM_LOG=false` antes do import):**
  - Solicitar reset com `base_url="https://evil.com"` no payload → o link registrado (capturado com `unittest.mock.patch.object(logging.getLogger("compraflow"), "warning")` e verificação de que **nenhum** log contém "evil.com" nem o token — pois `RESET_TOKEN_EM_LOG=false` e SMTP vazio).
  - Com `RESET_TOKEN_EM_LOG=true` via `importlib.reload(config)` + recarga do router (ou monkeypatch de `config.RESET_TOKEN_EM_LOG = True` antes da chamada), o log contém o token.
  - Redefinir senha com token válido → sessões anteriores do e-mail morrem: login, pedir reset, redefinir, chamar `/me` com o Bearer antigo → `401`.
  Rodar: `python backend/tests/test_seguranca.py` → novos casos FALHAM.

- [ ] **Step 2: Implementar em `reset.py`:** `_base_permitido()` conforme a interface; `link = (base + "#/redefinir/" + token) if base else token`; bloco de envio: se `SMTP_HOST` → `_enviar_email`; senão, se `RESET_TOKEN_EM_LOG` → `log.info(...link...)` (comportamento de dev/homolog, atual); senão → `log.warning("SMTP não configurado e RESET_TOKEN_EM_LOG=false — o e-mail de redefinição não pode ser enviado. Configure SMTP_HOST (produção) ou RESET_TOKEN_EM_LOG=true (apenas dev/homolog).")` **sem** registrar o token.

- [ ] **Step 3: Invalidar sessões em `api_redefinir_senha`** (reset.py:103-106): após trocar o hash, `db.execute(delete(Sessao).where(Sessao.email == email))` antes do `commit` (import de `Sessao` de `..models`; `delete` já importado).

- [ ] **Step 4: Env no `docker-compose.yml`/`.env.example`** (`APP_BASE_URL`, `RESET_TOKEN_EM_LOG`) e seção curta em `DEPLOY.md`: "SMTP e reset de senha" (SMTP_HOST obrigatório em produção; `APP_BASE_URL` fixa a base dos links; `RESET_TOKEN_EM_LOG` apenas dev/homolog).

- [ ] **Step 5: Rodar `test_seguranca.py` (PASS) + `test_rest.py` (PASS — o suíte atual testa reset? garantir que fluxo existente não quebra).**

- [ ] **Step 6: Commit + push**

```bash
git add backend/app/config.py backend/app/routers/reset.py backend/tests/test_seguranca.py docker-compose.yml .env.example DEPLOY.md
git commit -m "fix: protege fluxo de reset de senha (base_url do servidor, token em log opt-in e invalidação de sessões)"
git push
```

### Task 4: Sessão via cookie httpOnly (backend + frontend)

**Files:**
- Modify: `backend/app/rest.py` (`COOKIE_SESSAO`, `_token`, `rest_login`, `rest_logout`, `rest_sso_callback`), `backend/app/main.py` (CORS `allow_credentials`)
- Modify: `frontend/js/api.js:142-156,194-222` (`credentials`), `frontend/js/sessao.js`, `frontend/js/views/auth.js:76-122` (login + rota SSO), `frontend/js/router.js`, `frontend/js/app.js` (whitelists)
- Modify: `docker-compose.yml` + `.env.example` (COOKIE_SECURE) + `DEPLOY.md` (nota sobre TLS)
- Test: `backend/tests/test_seguranca.py` + smoke via `frontend/tests/test_frontend_adapter.mjs`

**Interfaces:**
- Consumes: `security.novo_token()`, `Sessao`, `usuario_autenticado` (existem); resposta do login `{token, email, nome, grupo, expira_em, troca_senha_obrigatoria}` — **token continua vindo no JSON** (compat: adapter e CLI), mas o browser não o guarda.
- Produces:
  - `rest.py`: `COOKIE_SESSAO = "cf_sessao"`; `_token(request)` → Bearer **ou** `request.cookies.get(COOKIE_SESSAO)`; login/logout/callback setam/apagam o cookie (`httponly=True, samesite="strict", max_age=SESSAO_MINUTOS*60, secure=config.COOKIE_SECURE, path="/"`.
  - `config.py`: `COOKIE_SECURE: bool` (default `False`; `true` em produção atrás do Caddy com TLS).
  - SSO: callback responde 302 para `base_spa() + "#/sso-ok"` **com cookie setado** (sem token no fragmento). Rota `#/sso/<token>` do frontend sai; entra `#/sso-ok` (busca `/me` com `credentials: "include"` e grava sessão sem token).
  - `sessao.js`: `ler()` aceita sessão sem `token` (`!s || !s.email`); `gravar()` guarda o que vier (token é opcional).

- [ ] **Step 1: Testes que falham primeiro (acrescentar ao `test_seguranca.py`, mesmo TestClient do suíte):**
  - Login → `Set-Cookie: cf_sessao=...` presente com `HttpOnly` e `SameSite=strict`.
  - `/me` **sem** Bearer, só com o cookie (o `TestClient` persiste cookies) → `200`.
  - Logout (sem Bearer, com cookie) → `/me` → `401` e cookie apagado.
  - Bearer antigo continua aceito (login puro via JSON devolve token; chamar `/me` com `Authorization: Bearer`) → `200` (compat).
  Rodar: `python backend/tests/test_seguranca.py` → novos casos FALHAM.

- [ ] **Step 2: Backend:** `config.COOKIE_SECURE`; `rest.py` — `_token` com fallback ao cookie; `rest_login`/`rest_logout` recebem `response: Response` e setam/apagam o cookie; `rest_sso_callback` usa a `RedirectResponse` para `set_cookie` e redireciona a `#/sso-ok`. `main.py`: `allow_credentials=True` no CORS quando `CORS_ORIGINS` setado.

- [ ] **Step 3: Rodar backend: `test_seguranca.py` (PASS) + `test_rest.py`, `test_sso.py` (PASS — Bearer segue funcionando).**

- [ ] **Step 4: Frontend:** `api.js` — `credentials: "include"` nas options de `fetchComTimeout` (cobre `chamarRest` e `baixarArquivoRest`); `sessao.js` — `ler()`/`gravar()` sem exigir `token`; `views/auth.js` login — `Sessao.gravar(r.data)` passa a gravar `{email, nome, grupo}` (token não é persistido); rota `#/sso/<token>` → `#/sso-ok` (fetch `/me` com `credentials: "include"`); whitelists de `#/sso-ok` em `router.js:20,29,45` e `app.js:6`.

- [ ] **Step 5: Verificar carga e sintaxe: `node --check` nos .js alterados + `node frontend/verificar_carga.mjs` (PASS). E2E do adapter: `node frontend/tests/test_frontend_adapter.mjs` contra API local (PASS — usa Bearer, continua compatível).**

- [ ] **Step 6: Env no `docker-compose.yml`/`.env.example` (`COOKIE_SECURE`) e nota em `DEPLOY.md`: com TLS no Caddy, defina `COOKIE_SECURE=true`.**

- [ ] **Step 7: Commit + push**

```bash
git add backend/app/rest.py backend/app/config.py backend/app/main.py frontend/js/api.js frontend/js/sessao.js frontend/js/views/auth.js frontend/js/router.js frontend/js/app.js backend/tests/test_seguranca.py docker-compose.yml .env.example DEPLOY.md
git commit -m "feat: migra a sessão do navegador para cookie httpOnly (SameSite=Strict), sem token no fragmento do SSO"
git push
```

---

## Pós-execução

- Rodar as 4 suítes de uma vez + `verificar_carga.mjs` e conferir o CI (`gh run watch` ou o status do push).
- Revisar se alguma mensagem nova de erro conflita com a regex `MSG_SESSAO` (nenhuma deve conter "sessão expirada").
