"""Allowlisted repository documentation, escaped before rendering."""
from html import escape
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

DOCUMENTS = ("PRD.md", "architecture.md", "data-contract.md", "feature-dictionary.md",
             "datasets.md", "evaluation-protocol.md", "responsible-ai.md", "limitations.md",
             "backend-api.md", "mcp.md", "local-demo.md", "claims-register.md", "build-status.md")

def router(root: Path) -> APIRouter:
    routes = APIRouter()
    @routes.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def documentation() -> str:
        sections = []
        for name in DOCUMENTS:
            path = root / name
            if path.is_file():
                # Escaping all content avoids executing HTML embedded in Markdown.
                import markdown
                rendered = markdown.markdown(escape(path.read_text(encoding="utf-8")), extensions=["tables", "fenced_code"])
                sections.append(f'<section id="{name[:-3]}"><h2>{escape(name)}</h2>{rendered}</section>')
        return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Agrogami AI — Project Docs</title>'
                '<style>body{max-width:1000px;margin:3rem auto;padding:1rem;font:16px system-ui;line-height:1.6}'
                'table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:.5rem}pre{overflow:auto}'
                'section{border-top:1px solid #ccc;margin-top:3rem}</style><h1>Agrogami AI — Research Prototype</h1>'
                '<p>Sample output is not a validated lending decision. Real underwriting-performance and fairness claims '
                'require representative pre-application records linked to mature repayment outcomes.</p><nav>'
                + ' · '.join(f'<a href="#{n[:-3]}">{escape(n[:-3])}</a>' for n in DOCUMENTS)
                + '</nav>' + ''.join(sections) + '</html>')
    return routes
