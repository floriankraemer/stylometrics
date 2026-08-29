# Why numpy is pinned to 1.26.4

`requirements.txt` pins `numpy==1.26.4` instead of numpy 2.x.

## Cause

spaCy 3.7's `thinc` dependency ships a Cython-compiled wheel (using `blis`)
built against the numpy 1.x C-ABI.
Loading it under numpy 2.x fails at import time:

```
ValueError: numpy.dtype size changed, may indicate binary incompatibility.
Expected 96 from C header, got 88 from PyObject
```

## Why not just recompile thinc from source against numpy 2?

Not worth it:

- `thinc`'s own `pyproject.toml` build requirements still pin `numpy<2` at
  build time, so a source build would need thinc's build config patched
  before it would even attempt to target numpy 2's ABI.
- Doing so needs a full build toolchain (gcc, Cython) added to the Docker
  image, which slows every build and adds a maintenance surface for no gain.
- Nothing in this pipeline uses any numpy 2-only feature — the pin costs us
  nothing functionally.

## When to revisit

Drop the pin once spaCy/thinc ship a release built against the numpy 2 ABI
(a future `spacy`/`thinc` major or minor bump). Until then, keep
`numpy==1.26.4`.
