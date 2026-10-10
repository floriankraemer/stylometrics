import pytest

from stylometry.preprocess import analyze

TEXT = ("I walked home. It was late, and the night was cold; perhaps it might rain!\n\n"
        "Why did she leave? She must never return. Thou hast spoken, and I heard thee.")


@pytest.fixture(scope="session")
def analysis():
    return analyze(TEXT)
