from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = os.environ.get("OPENAPI_SOURCE", "https://api.sovable.ai/openapi.json")
ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "docs" / "api"
SPEC_PATH = API_DIR / "openapi.json"
REFERENCE_PATH = API_DIR / "reference.md"

request = Request(SOURCE, headers={"Accept": "application/json", "User-Agent": "sovable-docs-builder/1.0"})
with urlopen(request, timeout=30) as response:
    spec = json.load(response)

if not spec.get("openapi") or not isinstance(spec.get("paths"), dict):
    raise SystemExit("Fetched document is not a valid OpenAPI document")

API_DIR.mkdir(parents=True, exist_ok=True)
SPEC_PATH.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

lines = [
    "---",
    "title: API reference",
    "sidebar_label: Generated API reference",
    "---",
    "",
    f"# {spec.get('info', {}).get('title', 'Solvable API')}",
    "",
    "This page is generated from the gateway OpenAPI contract during every documentation build. The source specification is available as [openapi.json](./openapi.json).",
    "",
    f"**OpenAPI version:** `{spec.get('openapi')}`",
    f"**API version:** `{spec.get('info', {}).get('version', 'unknown')}`",
    "",
]

for path, methods in sorted(spec["paths"].items()):
    for method, operation in sorted(methods.items()):
        if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
            continue
        op = operation or {}
        lines.extend([
            f"## `{method.upper()} {path}`",
            "",
            op.get("summary") or op.get("description") or "No summary provided.",
            "",
        ])
        tags = op.get("tags") or []
        if tags:
            lines.extend([f"**Tags:** {', '.join(f'`{tag}`' for tag in tags)}", ""])
        params = op.get("parameters") or []
        if params:
            lines.extend(["### Parameters", "", "| Name | In | Required | Type | Description |", "|---|---|---:|---|---|"])
            for parameter in params:
                schema = parameter.get("schema") or {}
                schema_type = schema.get("type") or schema.get("$ref", "object").split("/")[-1]
                description = (parameter.get("description") or "").replace("|", "\\|").replace("\n", " ")
                lines.append(f"| `{parameter.get('name', '')}` | `{parameter.get('in', '')}` | {'yes' if parameter.get('required') else 'no'} | `{schema_type}` | {description} |")
            lines.append("")
        request_body = op.get("requestBody")
        if request_body:
            lines.extend(["### Request body", "", "```json", json.dumps(request_body, indent=2), "```", ""])
        responses = op.get("responses") or {}
        if responses:
            lines.extend(["### Responses", "", "| Status | Description |", "|---:|---|"])
            for status, response in responses.items():
                description = (response.get("description") or "").replace("|", "\\|").replace("\n", " ")
                lines.append(f"| `{status}` | {description} |")
            lines.append("")
        examples = op.get("x-codeSamples") or []
        if examples:
            for example in examples:
                lang = example.get("lang", "text")
                lines.extend([f"### Example: {example.get('label', lang)}", "", f"```{lang}", example.get("source", ""), "```", ""])

REFERENCE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Generated {REFERENCE_PATH} from {len(spec['paths'])} OpenAPI paths")
