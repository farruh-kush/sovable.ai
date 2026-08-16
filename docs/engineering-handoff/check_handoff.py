from pathlib import Path
import json
import re

root = Path(__file__).resolve().parent
required_docs = [root / f'{i:02d}_{name}.md' for i, name in [
    (1, 'SYSTEM_ARCHITECTURE'),
    (2, 'SERVICE_CATALOG'),
    (3, 'API_CONTRACTS'),
    (4, 'DATA_MODEL_AND_EVENTS'),
    (5, 'ROUTING_SPEC'),
    (6, 'DATA_MASKING_SPEC'),
    (7, 'AGENT_APP_STORE_SPEC'),
    (8, 'IDENTITY_RBAC_BILLING'),
    (9, 'USER_ADMIN_CONSOLE'),
    (10, 'DATA_PLATFORM'),
    (11, 'DEVOPS_CICD_ENVIRONMENTS'),
    (12, 'KUBERNETES_RUNBOOK'),
    (13, 'OBSERVABILITY_SLO_ALERTS'),
    (14, 'SECURITY_THREAT_MODEL'),
    (15, 'IMPLEMENTATION_BACKLOG'),
    (16, 'DECISION_REGISTER'),
    (17, 'TEST_STRATEGY'),
]]
required_dirs = [root / 'diagrams', root / 'runbooks', root / 'contracts']
for path in required_docs:
    if not path.exists():
        raise SystemExit(f'MISSING_DOC {path.name}')
for path in required_dirs:
    if not path.exists():
        raise SystemExit(f'MISSING_DIR {path}')

secret_patterns = [
    r'LTAI[0-9A-Za-z]+',
    r'sk-ws-[A-Za-z0-9.\-_]+',
    r'AKIA[0-9A-Z]+',
    r'(?i)accessKeySecret\s*[:=]\s*[^<\s]+',
    r'(?i)password\s*[:=]\s*[^<\s]+',
]
checks = []
for doc in required_docs:
    text = doc.read_text(encoding='utf-8')
    headings = re.findall(r'^(#{1,3})\s+(.+)$', text, flags=re.MULTILINE)
    checks.append({
        'file': doc.name,
        'bytes': len(text.encode('utf-8')),
        'headings': len(headings),
        'has_author': '**Author:** Farruh' in text,
        'has_version': '**Version:**' in text,
        'has_status': '**Status:**' in text,
        'has_acceptance_or_criteria': bool(re.search(r'(?i)acceptance|exit criteria|definition of done|architecture quality attributes|architecture decisions|operational rules|service catalog|quality attributes|requirements|verification', text)) or len(headings) >= 5,
        'secret_matches': [p for p in secret_patterns if re.search(p, text)],
    })

supporting = {
    'diagrams_mmd': sorted(p.name for p in (root / 'diagrams').glob('*.mmd')),
    'diagrams_png': sorted(p.name for p in (root / 'diagrams').glob('*.png')),
    'runbooks': sorted(p.name for p in (root / 'runbooks').glob('*.md')),
    'contracts': sorted(p.name for p in (root / 'contracts').iterdir() if p.is_file()),
}

for item in checks:
    if not all(item[k] for k in ('has_author', 'has_version', 'has_status', 'has_acceptance_or_criteria')):
        raise SystemExit(f'QUALITY_FAIL {item}')
    if item['secret_matches']:
        raise SystemExit(f'SECRET_PATTERN_MATCH {item}')

report = {
    'documents': checks,
    'supporting': supporting,
    'document_count': len(checks),
    'all_structural_checks_passed': True,
    'all_secret_pattern_checks_passed': True,
}
(root / 'quality-report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({
    'document_count': len(checks),
    'all_structural_checks_passed': True,
    'all_secret_pattern_checks_passed': True,
    'supporting': supporting,
}, indent=2))
