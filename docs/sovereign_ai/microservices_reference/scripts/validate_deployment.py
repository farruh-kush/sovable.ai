from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is not installed; skipped Compose parse validation.")
    raise SystemExit(0)

compose = yaml.safe_load(Path(__file__).resolve().parents[1].joinpath("docker-compose.yml").read_text(encoding="utf-8"))
services = compose.get("services", {})
expected = {"auth", "router", "provider", "billing", "gateway"}
assert set(services) == expected, services.keys()
assert services["gateway"]["ports"] == ["8100:8100"]
for name in ("router", "provider", "billing", "gateway"):
    assert services[name]["environment"]
assert set(services["gateway"]["depends_on"]) == {"auth", "router", "provider", "billing"}
print("Compose structure valid")
