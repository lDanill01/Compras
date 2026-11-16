/* Configuração global da SPA.
 *
 * API_URL vazio = mesma origem (o nginx faz proxy de /api para o container
 * FastAPI). Para desenvolvimento fora do Docker, aponte ao uvicorn direto:
 *   API_URL: "http://localhost:8000/api"
 */
const CONFIG = {
  API_URL: "",

  /* Expiração da sessão (ms) — deve bater com SESSAO_MINUTOS do backend */
  SESSAO_MS: 8 * 60 * 60 * 1000,

  /* Domínio institucional obrigatório (sobrescrito pelo /api/config no boot) */
  DOMINIO_EMAIL: "@compraflow.com.br",

  /* Tamanho máximo de anexo (bytes) — deve bater com a validação server-side */
  ANEXO_MAX_BYTES: 10 * 1024 * 1024,

  /* Extensões aceitas para anexos (validação client-side espelha a do server) */
  ANEXO_EXTENSOES: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".png", ".jpg", ".jpeg", ".txt", ".zip"],

  /* Unidades/locais (cadastro e gráfico por unidade) — vem do backend */
  INSTITUTOS: [
    "Unidade Central - Capital",
    "Unidade Industrial - Distrito",
    "Unidade Logística - Porto",
    "Departamento Corporativo",
  ],

  /* Modalidades de compra (fonte de verdade: backend /api/config) */
  MODALIDADES: {
    selecao_com_disputa_aberta: "Seleção com Disputa (Aberta)",
    selecao_com_disputa_fechada: "Seleção com Disputa (Fechada)",
    selecao_sem_disputa_dispensa: "Seleção sem Disputa (Dispensa)",
    selecao_sem_disputa_inexigibilidade: "Seleção sem Disputa (Inexigibilidade)",
    credenciamento: "Credenciamento",
    pre_qualificacao: "Pré-qualificação",
    dialogo_previo: "Diálogo Prévio",
    registro_preco: "Registro de Preço",
  },

  /* Níveis de urgência (fonte de verdade: backend /api/config) */
  URGENCIAS: {
    baixa: "Baixa",
    media: "Média",
    alta: "Alta",
    critica: "Crítica",
  },

  /* Status do fluxo (fonte de verdade: backend /api/config) */
  STATUS: {
    aberta: "Aberta",
    enviada: "Enviada",
    em_analise: "Em Análise",
    concluida: "Concluída",
    cancelada: "Cancelada",
  },

  /* Marca (white-label) — sobrescrita pelo /api/config no boot (app.js) */
  PRODUTO: {
    nome: "CompraFlow",
    cor_primaria: "#1B7A43",
    logo_url: "",
  },
};

/* ------------------------------ marca (white-label) ----------------------- */

const HEX_RE = /^#?[0-9a-fA-F]{6}$/;

function _hexParaRgb(hex) {
  const v = hex.replace("#", "");
  return [0, 2, 4].map((i) => parseInt(v.slice(i, i + 2), 16));
}

/** Mistura o canal com branco (fator 0 = cor, 1 = branco). */
function _clarear(hex, fator) {
  return "#" + _hexParaRgb(hex)
    .map((c) => Math.round(c + (255 - c) * fator))
    .map((c) => c.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Aplica a marca em runtime, antes da primeira renderização:
 * título da página + paleta derivada da cor primária (sobrescreve tema.css).
 * Tons derivados: clara +18% · 400 +40% · soft +85% de mistura com branco.
 */
function aplicarMarca() {
  const p = CONFIG.PRODUTO;
  const cor = HEX_RE.test(p.cor_primaria) ? p.cor_primaria.toUpperCase() : "#1B7A43";
  const st = document.createElement("style");
  st.id = "tema-marca";
  st.textContent =
    `:root{--cor-primaria:${cor};` +
    `--cor-primaria-clara:${_clarear(cor, 0.18)};` +
    `--cor-primaria-400:${_clarear(cor, 0.40)};` +
    `--cor-primaria-soft:${_clarear(cor, 0.85)};}`;
  document.head.appendChild(st);

  document.title = p.nome + " — Gestão de Requisições de Compra";
  const fav = document.querySelector('link[rel="icon"]');
  if (fav && p.logo_url) fav.href = p.logo_url;
}

/** Src do logo: URL do cliente ou o arquivo padrão (substituível por mount). */
function srcLogo() {
  return CONFIG.PRODUTO.logo_url || "img/logo.svg";
}
