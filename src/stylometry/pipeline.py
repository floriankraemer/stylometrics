"""Text -> profile, shared by the CLI and the HTTP server."""
import threading

from stylometry.preprocess import analyze
from stylometry.qualitative import llm as llm_qualitative
from stylometry.report.profile import build

# analyze() resizes the shared spaCy pipeline's max_length
# ponytail: global lock, per-worker processes (uvicorn --workers) if throughput matters
_lock = threading.Lock()


class LLMError(Exception):
    """The LLM provider call failed."""


def run(text: str, source_name: str, llm: bool = False, provider: str = "anthropic") -> dict:
    with _lock:
        analysis = analyze(text)
    llm_result = None
    if llm:
        preliminary = build(analysis, source_name)
        try:
            llm_result = llm_qualitative.compute(text, preliminary["quantitative"], provider)
        except Exception as e:
            raise LLMError(str(e)) from e
    return build(analysis, source_name, llm_result=llm_result)
