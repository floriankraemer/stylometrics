"""Run inside the image: make test"""
import tempfile
import unittest
from pathlib import Path

from stylometry.preprocess import analyze
from stylometry.qualitative import heuristics
from stylometry.report import html_report
from stylometry.report.profile import build


def run(text):
    a = analyze(text)
    return heuristics.compute(a.sentences, a.words)


class HeuristicsTest(unittest.TestCase):
    def test_archaic_second_person(self):
        dist = run("Thou hast well said, for thy life is short. Know thyself, and I tell thee so.")["pronoun_distribution"]
        self.assertEqual(dist["second_person"], 4)
        self.assertEqual(dist["first_person"], 1)
        self.assertNotIn("third_person", dist)

    def test_relative_pronouns_ignored(self):
        dist = run("I saw the man who knew what that was.")["pronoun_distribution"]
        self.assertEqual(dist, {"first_person": 1})

    def test_anaphora_skips_leading_quotes(self):
        openers = run('"True, I was nervous." "True, I am mad." "True!" said he.')["anaphora_patterns"]
        self.assertEqual(openers[0], {"opener": "true", "count": 3})


    def test_it_counted_as_impersonal(self):
        dist = run("He saw it, and it was his.")["pronoun_distribution"]
        self.assertEqual(dist, {"third_person": 2, "impersonal": 2})

    def test_voice_first_person(self):
        self.assertEqual(run("I heard it. My heart beat, and I could not sleep.")["narrative_voice"], "first_person")

    def test_voice_second_person_archaic(self):
        self.assertEqual(run("Thou hast well said, for thy life is short and it passes.")["narrative_voice"], "second_person")

    def test_voice_ignores_dialogue(self):
        text = ("The prince rode out at dawn. “I will find you,” he said, “and you will know me.”\n\n"
                "The castle stood silent behind him, and the guards watched the road.")
        self.assertEqual(run(text)["narrative_voice"], "third_person")

    def test_voice_multi_paragraph_quote(self):
        text = ("The old man spoke at length.\n\n"
                "“I was young then, and I loved the sea.\n\n"
                "“I sailed every day of my life.”\n\n"
                "The listeners nodded, and the fire burned low in the hearth of the inn.")
        self.assertEqual(run(text)["narrative_voice"], "third_person")


class HtmlReportTest(unittest.TestCase):
    def test_untrusted_source_is_escaped(self):
        profile = build(analyze("I walked home. It was late."), "<img src=x onerror=alert(1)>.txt")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.html"
            html_report.write(profile, out)
            html = out.read_text()
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;.txt", html)


if __name__ == "__main__":
    unittest.main()
