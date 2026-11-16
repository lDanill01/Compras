/**
 * verificar_carga.mjs — guarda estática da SPA (sem navegador).
 *
 * 1. Todo <script src> do index.html deve existir no disco.
 * 2. Toda função chamada nos scripts carregados deve ter definição
 *    (global, no próprio arquivo, parâmetro de callback ou global do
 *    navegador).
 *
 * Pega a classe de bug do refactor órfão: função movida de arquivo e o
 * <script> tag esquecido — quebra só no navegador, depois do login.
 *
 * Rodar: node frontend/verificar_carga.mjs   (exit 1 em falha)
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const raiz = path.dirname(fileURLToPath(import.meta.url));
const html = fs.readFileSync(path.join(raiz, "index.html"), "utf8");

/* Globais do navegador/Chart.js usáveis pela SPA. */
const NAVEGADOR = new Set([
  "document", "window", "location", "localStorage", "navigator", "history",
  "fetch", "XMLHttpRequest", "Chart", "CustomEvent", "Event", "FormData",
  "AbortController", "Blob", "URL", "URLSearchParams", "FileReader",
  "alert", "confirm", "prompt", "console", "setTimeout", "clearTimeout",
  "setInterval", "clearInterval", "requestAnimationFrame",
  "atob", "btoa", "structuredClone", "queueMicrotask",
  "Math", "JSON", "Date", "Object", "Array", "String", "Number", "Boolean",
  "RegExp", "Map", "Set", "Promise", "Error", "Intl", "TextEncoder",
  "encodeURIComponent", "decodeURIComponent", "parseInt", "parseFloat",
  "isNaN", "escape", "unescape",
]);

/* Palavras-chave que precedem "(" sem serem chamadas. */
const KEYWORDS = new Set([
  "if", "for", "while", "switch", "catch", "return", "typeof", "new",
  "await", "async", "function", "delete", "void", "in", "of", "do", "else",
]);

let falhas = 0;
const check = (nome, ok, extra = "") => {
  console.log(`${ok ? "✅" : "❌"} ${nome} ${extra}`);
  if (!ok) falhas++;
};

/* ---- 1. tags de script ---- */
const srcs = [...html.matchAll(/<script src="([^"]+)"><\/script>/g)]
  .map(m => m[1])
  .filter(s => s.startsWith("js/")); /* CDN (Chart.js) não é verificado aqui */
check("index.html declara scripts locais", srcs.length > 0, `(${srcs.length})`);
for (const s of srcs) {
  check(`arquivo carregado existe: ${s}`, fs.existsSync(path.join(raiz, s)));
}

/* ---- 2. mini-scanner: só sobra código escaneável ----------------------- */

function pularString(cod, i) { /* i no abre-aspas; volta depois do fecha */
  const q = cod[i];
  let j = i + 1;
  while (j < cod.length) {
    if (cod[j] === "\\") { j += 2; continue; }
    if (cod[j] === q) return j + 1;
    j++;
  }
  return cod.length;
}

function pularTemplate(cod, i) { /* i depois do backtick; volta depois do fecha */
  while (i < cod.length) {
    const c = cod[i];
    if (c === "\\") { i += 2; continue; }
    if (c === "`") return i + 1;
    if (c === "$" && cod[i + 1] === "{") { i = pularChaves(cod, i + 2); continue; }
    i++;
  }
  return cod.length;
}

function pularChaves(cod, i) { /* i depois do "{"; volta depois do "}" que casa */
  let prof = 1;
  while (i < cod.length && prof > 0) {
    const c = cod[i];
    if (c === "'" || c === '"') { i = pularString(cod, i); continue; }
    if (c === "`") { i = pularTemplate(cod, i + 1); continue; }
    if (c === "/" && cod[i + 1] === "/") {
      const fim = cod.indexOf("\n", i + 2);
      i = fim === -1 ? cod.length : fim; continue;
    }
    if (c === "/" && cod[i + 1] === "*") {
      const fim = cod.indexOf("*/", i + 2);
      i = fim === -1 ? cod.length : fim + 2; continue;
    }
    if (c === "{") prof++;
    else if (c === "}") prof--;
    i++;
  }
  return i;
}

function semComentarios(cod) {
  let out = "", i = 0, prev = "", prevW = "";
  /* regex literal pode começar aqui? (evita confundir divisão `/` com regex) */
  const regexPode = () =>
    !prev || "([{,;=:!&|?+-*%^~<>".includes(prev) ||
    /\b(return|typeof|case|in|of|instanceof|new|delete|void|do|else)$/.test(prevW);
  while (i < cod.length) {
    const c = cod[i];
    if (c === "/" && cod[i + 1] === "*") {
      const fim = cod.indexOf("*/", i + 2); out += " ";
      i = fim === -1 ? cod.length : fim + 2; continue;
    }
    if (c === "/" && cod[i + 1] === "/") {
      const fim = cod.indexOf("\n", i + 2);
      i = fim === -1 ? cod.length : fim; continue;
    }
    if (c === "/" && regexPode()) {
      i++;
      let emClasse = false;
      while (i < cod.length) {
        const r = cod[i];
        if (r === "\\") { i += 2; continue; }
        if (r === "[") emClasse = true;
        else if (r === "]") emClasse = false;
        else if (r === "/" && !emClasse) { i++; break; }
        i++;
      }
      while (i < cod.length && /[a-z]/.test(cod[i])) i++; /* flags */
      out += "0 "; prev = "0"; prevW = "";
      continue;
    }
    if (c === '"' || c === "'") {
      i = pularString(cod, i); out += '" '; prev = '"'; prevW = "";
      continue;
    }
    if (c === "`") {
      i = pularTemplate(cod, i + 1); out += '" '; prev = '"'; prevW = "";
      continue;
    }
    out += c;
    if (!/\s/.test(c)) { prev = c; prevW = /\w/.test(c) ? prevW + c : ""; }
    i++;
  }
  return out;
}

/* ---- 3. definições (globais + por arquivo) ---- */
const arquivos = srcs.map(s => ({
  nome: s,
  cod: semComentarios(fs.readFileSync(path.join(raiz, s), "utf8")),
}));
const globais = new Set();
const porArquivo = new Map();
for (const { nome, cod } of arquivos) {
  const fns = new Set();
  for (const m of cod.matchAll(/\bfunction\s+([A-Za-z_$][\w$]*)\s*\(/g)) fns.add(m[1]);
  for (const m of cod.matchAll(/\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=/g)) fns.add(m[1]);
  /* parâmetros de callbacks: (a, b) => e function(a, b) */
  for (const m of cod.matchAll(/\(\s*([A-Za-z_$][\w$]*(?:\s*,\s*[A-Za-z_$][\w$]*)*)\s*\)\s*=>/g)) {
    for (const p of m[1].split(",")) fns.add(p.trim());
  }
  for (const m of cod.matchAll(/\bfunction\s*[^(\s]*\s*\(([^)]*)\)/g)) {
    for (const p of m[1].split(",")) {
      const n = p.trim().replace(/=.*$/, "").trim();
      if (/^[A-Za-z_$][\w$]*$/.test(n)) fns.add(n);
    }
  }
  porArquivo.set(nome, fns);
  for (const f of fns) globais.add(f);
}

/* ---- 4. chamadas resolvem? ---- */
for (const { nome, cod } of arquivos) {
  const locais = porArquivo.get(nome);
  for (const m of cod.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(/g)) {
    const id = m[1];
    if (KEYWORDS.has(id) || NAVEGADOR.has(id) || globais.has(id) || locais.has(id)) continue;
    console.log(`❌ ${nome}: chamada a '${id}()' sem definição encontrada`);
    falhas++;
  }
}

console.log();
if (falhas) {
  console.log(`CARGA: ${falhas} FALHA(S)`);
  process.exit(1);
}
console.log("CARGA: SPA INTEGRA ✔ (scripts existem e todas as chamadas resolvem)");
