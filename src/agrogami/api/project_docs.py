"""Allowlisted repository documentation, escaped before rendering."""
from html import escape
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

DOCUMENTS = ("PRD.md", "architecture.md", "data-contract.md", "feature-dictionary.md",
             "datasets.md", "evaluation-protocol.md", "responsible-ai.md", "limitations.md",
             "backend-api.md", "mcp.md", "local-demo.md", "claims-register.md")
# Images referenced by relative path in the Markdown; served by name only, never by caller path.
ASSETS = {"architecture-diagram.svg": "image/svg+xml"}

def router(root: Path) -> APIRouter:
    routes = APIRouter()
    @routes.get("/docs/assets/{name}", include_in_schema=False)
    def asset(name: str) -> FileResponse:
        if name not in ASSETS or not (root / name).is_file():
            raise HTTPException(404, "Not found")
        return FileResponse(root / name, media_type=ASSETS[name],
                            headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"})

    @routes.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def documentation() -> str:
        sections = []
        for name in DOCUMENTS:
            path = root / name
            if path.is_file():
                # Escaping all content avoids executing HTML embedded in Markdown.
                import markdown
                rendered = markdown.markdown(escape(path.read_text(encoding="utf-8")), extensions=["tables", "fenced_code"])
                for asset_name in ASSETS:
                    # The modification time versions the URL so edge caches never serve a stale diagram.
                    version = int((root / asset_name).stat().st_mtime) if (root / asset_name).is_file() else 0
                    rendered = rendered.replace(f'src="{asset_name}"', f'src="/docs/assets/{asset_name}?v={version}"')
                sections.append(f'<section id="{name[:-3]}"><h2>{escape(name)}</h2>{rendered}</section>')
        return ('<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>Agrogami AI — Documentation</title>'
                '<style>body{max-width:1000px;margin:3rem auto;padding:1rem;font:16px system-ui;line-height:1.6}'
                'img{max-width:100%;height:auto}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.5rem}pre{overflow:auto}'
                'h1{font-size:2.8rem;line-height:1.15;margin-bottom:.75rem}'
                '.tagline{font-size:1.4rem;line-height:1.4;max-width:48rem}'
                '.supporting-copy{color:#475569;max-width:52rem}.positioning{font-size:.95rem}'
                '.demo-notice{background:#fff8db;border-left:3px solid #ca9b20;padding:.75rem 1rem;'
                'font-size:.9rem;margin:1.5rem 0}.demo-notice p{margin:.25rem 0}'
                'section{border-top:1px solid #ccc;margin-top:3rem}</style><header><h1>Agrogami AI</h1>'
                '<p class="tagline">Traceable underwriting from financial records traditional credit systems ignore</p>'
                '<p class="supporting-copy">Turn mobile-money messages, informal ledger records, receipts, and bills '
                'into traceable financial evidence for thin-file credit assessment.</p>'
                '<p class="supporting-copy positioning">An explainable underwriting evidence and risk-audit '
                'workbench for thin-file credit.</p></header>'
                '<aside class="demo-notice" aria-label="Demo environment"><strong>Demo environment</strong>'
                '<p>This demonstration uses synthetic financial records only. Assessment '
                'outputs shown here are illustrative and are not lending decisions or validated individual creditworthiness.</p>'
                '<p>Agrogami does not represent sample outputs as validated lending decisions. Real underwriting-performance '
                'and fairness claims require representative pre-application records linked to mature repayment outcomes.</p>'
                '</aside><nav aria-label="Documentation sections">'
                + ' · '.join(f'<a href="#{n[:-3]}">{escape(n[:-3])}</a>' for n in DOCUMENTS)
                + '</nav>' + ''.join(sections) + '</html>')
    return routes
