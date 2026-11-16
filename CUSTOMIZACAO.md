# CUSTOMIZACAO.md — Identidade visual por cliente (white-label)

Cada cliente roda sua própria instância do CompraFlow e pode ter marca
própria **sem tocar no código**. Tudo se resolve com `.env` + (opcional)
arquivos em `branding/`.

## 1. O que é customizável

| Elemento | Como | Fonte |
|---|---|---|
| Nome do produto | `PRODUTO_NOME` no `.env` | Título da aba, alt do logo, sidebar, e-mails de reset, Swagger |
| Cor primária | `PRODUTO_COR_PRIMARIA` (hex `#RRGGBB`) | Gera toda a paleta: tons claro/400/soft derivados automaticamente |
| Logo | `./branding/logo.svg` montado no container (ou `PRODUTO_LOGO_URL`) | Sidebar (topo e rodapé), login e cadastro |
| Favicon | `./branding/favicon.svg` montado no container | Aba do navegador |
| E-mail institucional | `DOMINIO_EMAIL` no `.env` | Validação de cadastro e placeholders das telas |
| Domínio de negócio | `INSTITUTOS`/`MODALIDADES`/`URGENCIAS`/`STATUS` em `backend/app/config.py` | Seletores e filtros |

O frontend recebe tudo de `/api/config` no boot e aplica a marca **antes da
primeira renderização** — nenhuma tela pisca com a marca errada.

## 2. Checklist de personalização de um cliente

```bash
# 1. Marca em texto/cor (obrigatório)
cp .env.example .env
#   no .env:
#   PRODUTO_NOME=Aquisições ACME
#   PRODUTO_COR_PRIMARIA=#0A5CA8
#   DOMINIO_EMAIL=acme.com.br

# 2. Logo próprio (opcional)
cp logo-do-cliente.svg branding/logo.svg
cp favicon-do-cliente.svg branding/favicon.svg
#   descomente os 2 mounts "branding" no docker-compose.yml (serviço api)

# 3. Subir
docker compose up -d --build
```

## 3. Regras e limites

- **Logo por arquivo** é a via recomendada (mount read-only; sem URL externa,
  sem dependência de terceiros). `PRODUTO_LOGO_URL` existe para o caso do
  logo ficar em CDN/servidor do próprio cliente.
- A **cor primária** precisa de contraste suficiente para texto branco
  (o padrão de UI usa branco sobre `--cor-primaria`).
- Os tons derivados (claro/400/soft) são calculados no navegador misturando
  a cor com branco — se a marca do cliente exigir tons exatos, o ajuste fino
  continua possível sobrescrevendo `tema.css` (monte um override).
- `branding/` **não é versionado** (`.gitignore`): cada instância guarda a
  marca do seu cliente localmente.
- Sem nenhuma configuração, o produto aparece como **CompraFlow** verde
  `#1B7A43` — os defaults de `tema.css` e `js/config.js` valem como fallback
  (a SPA funciona até se `/api/config` não responder).

## 4. Onde está implementado (referência para manutenção)

- Backend: `backend/app/config.py` (seção "white-label") → exposto em
  `agregacoes.api_config` (`/api/config`) e usado em `routers/reset.py`
- Frontend: `frontend/js/config.js` (`CONFIG.PRODUTO`, `aplicarMarca`,
  `srcLogo`) consumido no bootstrap de `app.js`; literais em
  `components/layout.js` e `views/auth.js` foram substituídos
