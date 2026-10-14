# Formación anyformat × IBM Consulting

Repo de una formación de 2 horas: workflows de anyformat (facturas, calas y canalizaciones), ground truth,
mejora con Annie y una app Next.js sobre `@anyformat/sdk`. Lee `README.md` y la guía del bloque en `docs/`.

- La app está en `app/` (su propio `CLAUDE.md`). Solo `app/src/lib/anyformat.ts` toca el SDK.
- Workflows en formato de la API (`POST /v3/workflows/`) en `workflows/`. Editar el JSON no cambia el
  workflow de la cuenta: se cambia en Studio, con Annie o con `PATCH /v3/workflows/{id}/`.
- El MCP de anyformat está en `.mcp.json`; necesita `ANYFORMAT_API_KEY` exportada antes de abrir `claude`.
- Ground truth de calas en `ground_truth/calas/`; puntuar con `python3 tools/score_calas.py <carpeta de runs>`.
- Los PDFs de `samples/` son documentos reales o anonimizados: no los subas a ningún sitio fuera de anyformat.
- Nunca escribas una API key en un fichero versionado (`.env.local` está en `.gitignore`).
