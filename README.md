# AskCH

An opensource chatbot 
<br />

<br />

## How to Contribute


### Develop the WebUI

Requirements [vp](https://viteplus.dev/)

```
cd web
vp install && vp dev
```


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
