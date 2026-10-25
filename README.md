
<div align="center">


<img src="banner.png" alt="AskCH banner" />

<h3 >
Made in Switerland · Hosted in Switerland · Use Only Swiss Models
</h3 >


[![Release](https://img.shields.io/github/v/release/xLongLink/askch)](https://github.com/xLongLink/askch/releases/latest)
[![Release workflow](https://github.com/xLongLink/askch/actions/workflows/release.yaml/badge.svg)](https://github.com/xLongLink/askch/actions/workflows/release.yaml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)


</div>

<br />

## Features

- 🇨🇭 **Swiss hosting:** Hosted in Switzerland on Infomaniak.
- 🤖 **Swiss AI:** Powered by [Apertus 1.5](https://www.apertus-ai.org/articles/2026-07-apertus-1-5/).
- 🔌 **Connected to Swiss services:** Access Swiss data through an MCP server.
- 💬 **Natural language:** Explore Swiss data by asking questions in your own words.
- 📖 **Open source:** Free to use, inspect, and extend under the MIT license.


<br />

## How to Contribute
- TODO

<br />

### Develop the WebUI

Requirements: [Node.js 24 LTS](https://nodejs.org/). Vite+ is installed locally as a development dependency.

```
cd web
npm ci && npm run dev
```

### Develop the API

Requirements [uv](https://docs.astral.sh/uv/getting-started/installation/)

```
cd api
uv sync && uv run python main.py
```


### GitHub releases

Push a version tag after committing the project and these files:

```sh
git tag v0.1.0
git push origin v0.1.0
```

<br />

---

<div align="center">
LongLink 2026

[License](./LICENSE) &nbsp; - &nbsp; [Contributing](./CONTRIBUTING.md) &nbsp; - &nbsp; [Code of Conduct](./CODE_OF_CONDUCT.md) &nbsp; - &nbsp; [Contact](mailto:info@longlink.dev)

</div>

---
