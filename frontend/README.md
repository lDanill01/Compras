# CompraFlow — Frontend (SPA)

Interface web em HTML/CSS/JS puro, **sem build step**: os arquivos desta
pasta são servidos tal como estão (nginx/Caddy na frente, API em `/api`
mesma origem). Nenhum framework, nenhum bundler.

## Arquitetura

```
[Navegador] ──► [SPA frontend/] ──fetch──► [/api/* — backend FastAPI]
                  rotas por hash            REST (Bearer token)
```

## Pastas

| Pasta/arquivo | Papel |
|---|---|
| `index.html` | casca única + carregamento dos scripts |
| `css/tema.css` | **identidade visual (variáveis CSS)** — personalização por cliente |
| `css/app.css` | tema consolidado da SPA (regras de tela/componentes) |
| `verificar_carga.mjs` | guarda estática: tags de script × chamadas sem definição |
| `tests/` | teste do adapter REST contra a API real |
| `js/config.js` | constantes da SPA (sobrescritas em runtime pelo `/api/config`) |
| `js/api.js` | adapter REST (`API.chamar`) + mapa de endpoints |
| `js/sessao.js` · `js/sessao.js` | sessão local (token, expiração) |
| `js/router.js` | roteamento por hash (`#/login`, `#/home`, `#/requisicoes`, ...) |
| `js/app.js` | bootstrap (busca `/api/config` e monta o app) |
| `js/views/` | uma tela por arquivo (auth, dashboard, requisicoes, tramitar, performance, documentos, usuarios, configuracoes) |
| `js/components/` | layout/sidebar, filtros, gráficos |

## Rotas

`#/login` · `#/cadastro` · `#/redefinir/<token>` · `#/sso/<token>` ·
`#/home` · `#/requisicoes` · `#/tramitar/<numero>` · `#/performance` ·
`#/documentos` · `#/usuarios` · `#/configuracoes`

## Tema / white-label

Toda a paleta vive em `css/tema.css` via variáveis (`--cor-primaria`,
`--cor-accent`, ...). Para personalizar um cliente: altere as variáveis
(ou sobrescreva o arquivo). Nome do produto e logo: `index.html`,
`js/components/layout.js` e `img/logo.svg`.
