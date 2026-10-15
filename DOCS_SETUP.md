# Publishing the docs

1. Copy `mkdocs.yml`, `requirements-docs.txt`, `docs/` and `.github/workflows/docs.yml` into the repo root.
2. Preview locally:
   ```bash
   pip install -r requirements-docs.txt
   mkdocs serve
   ```
3. Commit and push:
   ```bash
   git add mkdocs.yml requirements-docs.txt docs .github/workflows/docs.yml
   git commit -m "Add MkDocs documentation site"
   git push
   ```
4. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
5. The workflow publishes to https://mmbellani.github.io/coffee-capsules-production-optimizer-agent/
6. Add `site/` to `.gitignore`.
