// Observable Framework configuration for the companion site.
// Data files in src/data/*.json are produced by `uv run mcreview export`; publication pages are generated
// from publications.json at build time.
import {readFileSync} from "node:fs";

const publications = JSON.parse(readFileSync(new URL("./src/data/publications.json", import.meta.url), "utf-8"));

export default {
  title: "Machine Minds on Substack",
  pages: [
    {name: "Overview", path: "/"},
    {name: "Positions", path: "/positions"},
    {name: "Arguments and sources", path: "/arguments"},
    {name: "Topic map", path: "/topics"},
    {name: "Citation network", path: "/network"},
    {name: "Over time", path: "/timeline"},
    {name: "Browse posts", path: "/posts"},
    {name: "Publications", path: "/publications"},
    {name: "Methods", path: "/methods"}
  ],
  dynamicPaths: publications.map((p) => `/publication/${p.id}`),
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><circle cx=%2250%22 cy=%2250%22 r=%2240%22 fill=%22%232a78d6%22/></svg>">',
  root: "src",
  theme: ["air", "near-midnight"],
  toc: false,
  sidebar: true,
  pager: false,
  footer: "Data and code: mcreview. Posts are linked, never reproduced. Codes are machine-assigned with human spot checks; see Methods.",
  search: false,
  style: "style.css"
};
