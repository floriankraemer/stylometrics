from jinja2 import Template

# autoescape: source names, LLM output and quoted text all come from untrusted input
_TEMPLATE = Template(autoescape=True, source="""\
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Style Report — {{ profile.source }}</title>
<style>
  body { font-family: Georgia, serif; max-width: 820px; margin: 2rem auto; padding: 0 1rem; color: #222; }
  h1 { border-bottom: 2px solid #222; padding-bottom: .3rem; }
  h2 { margin-top: 2.5rem; border-bottom: 1px solid #ccc; padding-bottom: .2rem; }
  table { border-collapse: collapse; width: 100%; margin: .5rem 0 1.5rem; }
  th, td { text-align: left; padding: .3rem .6rem; border-bottom: 1px solid #eee; }
  th { background: #f5f5f0; }
  .metric-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .5rem 1.5rem; }
  .metric { display: flex; justify-content: space-between; align-items: baseline; gap: .75rem; border-bottom: 1px dotted #ddd; padding: .2rem 0; }
  .metric .label { color: #555; min-width: 0; overflow-wrap: break-word; }
  .metric .value { font-weight: bold; flex-shrink: 0; }
  p.note { color: #666; font-size: .9rem; }
</style>
</head>
<body>
<h1>Style Report</h1>
<p class="note">Source: {{ profile.source }} — {{ profile.sentence_count }} sentences, {{ profile.quantitative.lexical.token_count }} tokens.</p>

<h2>1. Mechanics &amp; Lexical Diversity</h2>
<div class="metric-grid">
{% for k, v in profile.quantitative.lexical.items() %}
  <div class="metric"><span class="label">{{ k }}</span><span class="value">{{ v }}</span></div>
{% endfor %}
</div>

<h2>2. Vocabulary — Top Function Words (per 1000 tokens)</h2>
<table>
<tr><th>Word</th><th>Per 1000 tokens</th></tr>
{% for fw in profile.quantitative.function_words %}
<tr><td>{{ fw.word }}</td><td>{{ fw.per_1000 }}</td></tr>
{% endfor %}
</table>

<h2>3. Syntax</h2>
<div class="metric-grid">
{% for k, v in profile.quantitative.syntax.items() %}
  <div class="metric"><span class="label">{{ k }}</span><span class="value">{{ v }}</span></div>
{% endfor %}
</div>

<h2>4. Punctuation Profile (per 1000 words)</h2>
<div class="metric-grid">
{% for k, v in profile.quantitative.punctuation.items() %}
  <div class="metric"><span class="label">{{ k }}</span><span class="value">{{ v }}</span></div>
{% endfor %}
</div>

<h2>5. Burstiness (Sentence-Length Rhythm)</h2>
<div class="metric-grid">
{% for k, v in profile.quantitative.burstiness.items() %}
  <div class="metric"><span class="label">{{ k }}</span><span class="value">{{ v }}</span></div>
{% endfor %}
</div>

<h2>6. Perspective &amp; Stance (heuristic)</h2>
<div class="metric-grid">
<div class="metric"><span class="label">rhetorical_<wbr>question_<wbr>rate_<wbr>per_<wbr>100_<wbr>sentences</span><span class="value">{{ profile.qualitative.heuristics.rhetorical_question_rate_per_100_sentences }}</span></div>
<div class="metric"><span class="label">hedging_<wbr>rate_<wbr>per_<wbr>1000_<wbr>words</span><span class="value">{{ profile.qualitative.heuristics.hedging_rate_per_1000_words }}</span></div>
<div class="metric"><span class="label">assertiveness_<wbr>rate_<wbr>per_<wbr>1000_<wbr>words</span><span class="value">{{ profile.qualitative.heuristics.assertiveness_rate_per_1000_words }}</span></div>
<div class="metric"><span class="label">rule_<wbr>of_<wbr>three_<wbr>occurrences</span><span class="value">{{ profile.qualitative.heuristics.rule_of_three_occurrences }}</span></div>
<div class="metric"><span class="label">narrative_<wbr>voice</span><span class="value">{{ profile.qualitative.heuristics.narrative_voice }}</span></div>
</div>
<p><strong>Pronoun distribution:</strong>
{% for k, v in profile.qualitative.heuristics.pronoun_distribution.items() %}{{ k }}: {{ v }}&nbsp;&nbsp;{% endfor %}
</p>
<p><strong>Anaphora (repeated sentence openers):</strong>
{% for a in profile.qualitative.heuristics.anaphora_patterns %}"{{ a.opener }}" ({{ a.count }}x)&nbsp;&nbsp;{% endfor %}
{% if not profile.qualitative.heuristics.anaphora_patterns %}none detected{% endif %}
</p>

{% if profile.qualitative.llm %}
<h2>7. Rhetoric (LLM-assisted)</h2>
{% if profile.qualitative.llm.raw_response %}
<pre>{{ profile.qualitative.llm.raw_response }}</pre>
{% else %}
<p><strong>Tone &amp; Register:</strong> {{ profile.qualitative.llm.tone_and_register }}</p>
<p><strong>Cadence &amp; Rhythm:</strong> {{ profile.qualitative.llm.cadence_and_rhythm }}</p>
<p><strong>Persuasion Style:</strong> {{ profile.qualitative.llm.persuasion_style }}</p>
<p><strong>Rhetorical Devices:</strong></p>
<ul>
{% for d in profile.qualitative.llm.rhetorical_devices %}
<li>{{ d.device }} — "{{ d.example }}"</li>
{% endfor %}
</ul>
{% endif %}
{% endif %}

</body>
</html>
""")


def write(profile: dict, out_path):
    out_path.write_text(_TEMPLATE.render(profile=profile), encoding="utf-8")
