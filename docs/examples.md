# Examples: Marcus Aurelius and Edgar Allan Poe

The `examples/` folder holds two public-domain corpora and the pipeline's output for each.
They show what the three output files look like on real books, and how two very different voices separate on the measured metrics.

```
examples/
├── marcus-aurelius/
│   ├── meditations.txt          input text
│   └── output/                  meditations_report.html, _profile.md, _clone_prompt.md
└── poe/
    ├── tales.txt                input text
    └── output/                  tales_report.html, _profile.md, _clone_prompt.md
```

Regenerate all outputs with:

```sh
make examples
```

The target runs the normal pipeline once per `examples/<name>/*.txt` and writes into `examples/<name>/output/`.

## Sources and licensing

Both texts are in the public domain worldwide.
They were taken from Project Gutenberg, and everything that is not the author's text was removed: the Project Gutenberg header, footer and license, editors' introductions, appendices, glossaries and endnotes.
What remains is plain public-domain text with no license attached.

| Example | Text | Source | Why it is public domain |
|---|---|---|---|
| `marcus-aurelius/meditations.txt` | *Meditations*, Books I–XII, in the English translation by Meric Casaubon | Project Gutenberg eBook #2680 | Marcus Aurelius died in 180 AD; Casaubon's translation was published in 1634. |
| `poe/tales.txt` | 22 tales from *The Works of Edgar Allan Poe*, Raven Edition, Volume II (from "The Purloined Letter" to "Eleonora") | Project Gutenberg eBook #2148 | Poe died in 1849; the Raven Edition was published in 1903. |

Cleanup details:

- **Meditations:** only the twelve books are kept.
  The 1906 introduction by W. H. D. Rouse, the Fronto correspondence appendix, the notes and the glossary are removed.
- **Poe:** only the tales are kept.
  The "Notes to the Second Volume" (partly by Poe's editor Griswold) are removed, as are the inline endnote markers such as `(*1)`.
  Square brackets that remain in the text, such as the stage directions in "Mesmeric Revelation", are Poe's own.

## Results at a glance

| Metric | Meditations | Poe tales |
|---|---:|---:|
| Sentences / tokens | 2,161 / 57,410 | 4,018 / 93,857 |
| Type-token ratio | 0.077 | 0.106 |
| Yule's K | 102.2 | 125.3 |
| Mean sentence length (words) | 26.8 | 23.9 |
| Sentence-length stdev / max | 22.0 / 199 | 18.8 / 157 |
| Average parse-tree depth | 5.27 | 5.62 |
| Noun-to-verb ratio | 1.18 | 1.29 |
| Commas per 1000 words | 90.1 | 84.6 |
| Semicolons per 1000 words | 12.8 | 8.5 |
| Colons per 1000 words | 7.2 | 0.8 |
| Em dashes per 1000 words | 0.05 | 15.6 |
| Exclamation marks per 1000 words | 0.6 | 4.0 |
| Question marks per 1000 words | 6.9 | 2.4 |
| Rhetorical questions per 100 sentences | 15.4 | 2.6 |
| Hedging per 1000 words | 1.6 | 4.4 |
| Assertive words per 1000 words | 5.0 | 2.3 |
| Narrative voice | second person | first person |
| Pronouns: 1st / 2nd / 3rd person / "it" | 767 / 1,720 / 2,050 / 1,234 | 4,207 / 297 / 2,222 / 1,540 |
| Top sentence openers | for, and, but, as, if | I, the, it, and, in |
| Top function words | and, of, the, that, to, is | the, of, and, to, a, I |

The full numbers are in each example's `output/*_profile.md`, and the formatted view is in `output/*_report.html`.

## Reading the Meditations profile

The *Meditations* are private notes Marcus Aurelius wrote to himself, and the metrics reflect a man arguing with himself.

- **Reasoning chains.**
  The most frequent sentence openers are "for", "and", "but", "as" and "if".
  These are the words of justification ("For he that is angry…"), concession and condition.
  "That" and "is" rank in the top six function words because the text keeps defining things: "that which is…", "it is…".
- **Self-address.**
  Second-person pronouns appear 1,720 times, almost all of them "thou", "thee", "thy" and "thyself".
  The book speaks to its own author, and the pipeline reports its narrative voice as second person.
  Third-person pronouns ("he", "they", "them") are still more frequent, because the argument keeps talking about other people and things.
- **Questions as method.**
  15 in every 100 sentences are questions, six times the rate in the Poe tales.
  Many are rhetorical: Marcus asks and answers in the same breath.
- **Firm, not tentative.**
  Hedging is low (1.6 per 1000 words) and assertive words ("must", "never", "always") are more than twice as frequent as in Poe.
- **Seventeenth-century punctuation.**
  The many colons (7.2 per 1000 words, against 0.8 in Poe) and semicolons, the near-absence of em dashes, and a longest sentence of 199 words are Casaubon's.
  His English chains clauses where a modern writer would start a new sentence.

Keep in mind that this is a translation.
The vocabulary, punctuation and archaic pronouns measure Casaubon's 1634 English as much as Marcus's Greek.
The structural habits (argument from cause, self-questioning, address to "thou") survive translation, which is why they still dominate the profile.

## Reading the Poe profile

The 22 tales mix detective stories, horror and prose poems, but most share one voice: a narrator who tells what happened to him.

- **First-person narration.**
  "I" is the most frequent sentence opener (536 times) and the sixth most frequent function word, and first-person pronouns outnumber every other group.
  This is the voice of "The Tell-Tale Heart", "The Black Cat" and "The Pit and the Pendulum".
- **The dash.**
  Poe uses 15.6 em dashes per 1000 words, the clearest single fingerprint in either example.
  They mark interruption and agitation: "True!—nervous—very, very dreadfully nervous".
  Exclamation marks (4.0 per 1000 words) point the same way.
- **Hedging needs a closer look.**
  The hedging rate (4.4 per 1000 words) is almost three times that of the *Meditations*, but over half of it is "could" (214 times).
  In these tales "could" mostly expresses past ability ("I could not see"), not doubt.
  The real hedges, "perhaps" (50 times) and "might" (94 times), still occur more often than in the *Meditations*, so the narrators are somewhat less certain, but not by the full factor of three.
- **Description over argument.**
  "The" and "of" lead the function words ("the fall of the house", "the depth of the pit"), a sign of dense noun phrases.
  The noun-to-verb ratio and parse depth are both higher than in the *Meditations*.
- **Vocabulary.**
  The type-token ratio is higher than for the *Meditations* even though the text is longer, which shows a genuinely broader vocabulary across many settings and subjects.
  Yule's K is higher too, which means the most frequent words ("the", "of") take a larger share of the text.
  The two metrics measure different things and do not contradict each other.

## Caveats

- **Type-token ratio depends on text length.**
  It falls as a text gets longer, so compare it only across texts of similar size.
  Yule's K and Honoré's R are more stable across lengths.
- **The stance metrics are word-list heuristics.**
  "Could" counts as a hedge and "never" as an assertion regardless of context, as the Poe hedging figure shows.
  Treat them as a rough signal and compare them between texts rather than reading them in isolation.
- **A collection gives an average voice.**
  The Poe profile blends comic, analytical and Gothic tales.
  Analyze a single tale to see one register on its own.
- **Narrative voice is a threshold rule.**
  Third-person pronouns occur in any text, so they cannot show who is speaking to whom.
  The pipeline therefore reports first or second person once either reaches 10 per 1000 words of narration, and third person otherwise.
  Text inside quotation marks is left out, so dialogue does not turn a third-person novel into a first-person one.
  The threshold was calibrated on these examples: the third-person "Masque of the Red Death" scores 2.5, the first-person Poe tales 12 to 80, and the *Meditations* 30 in the second person.
  A text that scores close to 10 may get the wrong label, so check the pronoun distribution in the profile.
- **"It" is counted separately.**
  "It", "its" and "itself" are grammatically third person but refer to things, not people, so the pronoun distribution lists them as `impersonal`.
