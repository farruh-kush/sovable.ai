# Solvable.ai Static Website

The public website is available in the `site/` directory as a credential-free static export of the Solvable.ai landing page and console shell. It can be served by any static web host, object-storage website endpoint, CDN, or GitHub Pages configuration.

To preview the generated site locally, run `python3 -m http.server 4173 --directory site` and open `http://localhost:4173`. The interactive console pages intentionally remain safe when no gateway is configured; they show an unavailable state until an operator supplies a runtime API base URL and API key through the browser interface.

The full source application remains in `web/dashboard/`, with backend services, provider adapters, routing configuration, Docker Compose, observability, and Kubernetes manifests in their respective directories. Cloud provisioning and production credentials are intentionally not included in this public repository and remain deferred until the owner provides them.

## Rebuilding the static export

```bash
cd web/dashboard
npm ci
NEXT_TELEMETRY_DISABLED=1 npm run build
rm -rf ../../site
cp -R out ../../site
```

The static artifact is generated from source and is safe to publish because provider credentials, database passwords, API keys, and cloud credentials are supplied only at runtime or through secret-management systems.
