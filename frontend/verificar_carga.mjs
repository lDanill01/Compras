/**
 * verificar_carga.mjs — guarda estática da SPA (sem navegador).
 *
 * 1. Todo <script src> do index.html deve existir no disco.
 * 2. Toda função chamada nos scripts carregados deve ter definição
 *    (global, no próprio arquivo ou global do navegador).
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
  "Math", "JSON", "Date", "Object", "Array", "String", "Number", "Boolean",
  "RegExp", "Map", "Set", "Promise", "Error", "Intl", "TextEncoder",
  "encodeURIComponent", "decodeURIComponent", "parseInt", "parseFloat",
  "isNaN", "isNaN", "escape", "unescape",
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

/* ---- 2. definições (globais + por arquivo) ---- */

/** Remove comentários e "apaga" strings — só sobra código escaneável. */
function semComentarios(cod) {
  let out = "", i = 0;
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
    if (c === '"' || c === "'" || c === "`") {
      const fim = cod.indexOf(c, i + 1); out += c + " ";
      i = fim === -1 ? cod.length : fim + 1; continue;
    }
    out += c; i++;
  }
  return out;
}

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
  porArquivo.set(nome, fns);
  for (const f of fns) globais.add(f);
}

/* ---- 3. chamadas resolvem? ---- */
for (const { nome, cod } of arquivos) {
  const locais = porArquivo.get(nome);
  for (const m of cod.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(/g)) {
    const id = m[1];
    if (NAVEGADOR.has(id) || globais.has(id) || locais.has(id)) continue;
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
