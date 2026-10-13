# PyInstaller spec: `pyinstaller packaging/stylometry.spec` -> dist/stylometry/
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("spacy", "en_core_web_sm", "thinc", "srsly", "blis", "cymem", "preshed", "murmurhash",
            "ebooklib", "docx", "anthropic", "openai", "uvicorn", "fastapi", "starlette", "mangum",
            "multipart", "pydantic", "anyio", "mcp", "mcp_types", "httpx2", "opentelemetry", "sse_starlette",
            "jsonschema", "jsonschema_specifications", "referencing", "jwt"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

import os
src = os.path.join(SPECPATH, "..", "src")
a = Analysis([os.path.join(SPECPATH, "entry.py")], pathex=[src], datas=datas, binaries=binaries, hiddenimports=hiddenimports)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="stylometry", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="stylometry")
