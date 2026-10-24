# AskCH

An opensource chatbot 
<br />

<br />

## How to Contribute


### Develop the WebUI

Requirements: [Node.js 24 LTS](https://nodejs.org/) (24.11 or newer) and npm 11.19 or newer. Vite+ is installed locally as a development dependency.

```
cd web
npm ci && npm run dev
```

Use `npm install` when changing dependencies and commit `web/package-lock.json`. Run `npm run lint`, `npm run check`, and `npm run build` from `web/` to validate changes. Docker and CI install the locked dependencies with `npm ci`.


### Develop the API

Requirements [uv](https://docs.astral.sh/uv/getting-started/installation/)

```
cd api
uv sync && uv run uvicorn src.main:create_app --factory --reload
```

### GitHub releases

Push a version tag after committing the project and these files:

```sh
git tag v0.1.0
git push origin v0.1.0
```


---

<div align="center">
LongLink 2026

[License](./LICENSE) &nbsp; - &nbsp; [Contributing](./CONTRIBUTING.md) &nbsp; - &nbsp; [Code of Conduct](./CODE_OF_CONDUCT.md) &nbsp; - &nbsp; [Contact](mailto:info@longlink.dev)

</div>

---
