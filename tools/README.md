# Tools

## Visualizer

`visualizer.html` is a standalone HTML visualizer for AtCoder-style graph, tree, and grid inputs.

You can open it directly in a browser, or serve it locally:

```bash
cd tools
python3 -m http.server 8000
```

On Windows PowerShell:

```powershell
cd tools
python -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000/visualizer.html
```

You can also use the helper script on Unix-like shells:

```bash
chmod +x tools/serve.sh
./tools/serve.sh
```

## `ERR_BLOCKED_BY_CLIENT`

If the browser shows `ERR_BLOCKED_BY_CLIENT`, it is often caused by an ad blocker, browser extension, sandbox restriction, or local file policy. It does not necessarily mean `visualizer.html` has a syntax error.

Try these:

- Temporarily disable browser extensions such as ad blockers.
- Open the page through `http://127.0.0.1:8000/visualizer.html` instead of `file://`.
- In Codex environments, local browser preview may be blocked even when the HTML itself works.
