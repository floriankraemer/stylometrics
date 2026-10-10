# Examples: seven public-domain authors

The `examples/` folder holds seven public-domain texts and the pipeline's output for each.
They show what the three output files look like on real books, and how very different voices separate on the measured metrics.

```
examples/
├── marcus-aurelius/
│   ├── meditations.txt          input text
│   └── output/                  meditations_report.html, _profile.md, _clone_prompt.md
├── poe/
│   ├── tales.txt                input text
│   └── output/                  tales_report.html, _profile.md, _clone_prompt.md
├── austen/pride-and-prejudice.txt
├── dickens/great-expectations.txt
├── doyle/hound-of-the-baskervilles.txt
├── darwin/origin-of-species.txt
└── thoreau/walden.txt           each with an output/ folder like the ones above
```

Regenerate all outputs with:

```sh
make examples
```

The target runs the normal pipeline once per `examples/<name>/*.txt` and writes into `examples/<name>/output/`.

## Sources and licensing

All texts are in the public domain worldwide: every author died more than 70 years ago, and every text was published before 1929.
They were taken from Project Gutenberg, and everything that is not the author's text was removed: the Project Gutenberg header, footer and license, editors' introductions, appendices, glossaries and endnotes.
What remains is plain public-domain text with no license attached.

| Example | Text | Source | Why it is public domain |
|---|---|---|---|
| `marcus-aurelius/meditations.txt` | *Meditations*, Books I–XII, in the English translation by Meric Casaubon | Project Gutenberg eBook #2680 | Marcus Aurelius died in 180 AD; Casaubon's translation was published in 1634. |
| `poe/tales.txt` | 22 tales from *The Works of Edgar Allan Poe*, Raven Edition, Volume II (from "The Purloined Letter" to "Eleonora") | Project Gutenberg eBook #2148 | Poe died in 1849; the Raven Edition was published in 1903. |
| `austen/pride-and-prejudice.txt` | *Pride and Prejudice* (1813), text of the illustrated 1894 George Allen edition | Project Gutenberg eBook #1342 | Austen died in 1817. |
| `dickens/great-expectations.txt` | *Great Expectations* (1861), text of the 1867 edition | Project Gutenberg eBook #1400 | Dickens died in 1870. |
| `doyle/hound-of-the-baskervilles.txt` | *The Hound of the Baskervilles* (1901–02) | Project Gutenberg eBook #2852 | Doyle died in 1930, so his work has been public domain worldwide since 2001. |
| `darwin/origin-of-species.txt` | *On the Origin of Species*, first edition (1859) | Project Gutenberg eBook #1228 | Darwin died in 1882. |
| `thoreau/walden.txt` | *Walden* (1854) | Project Gutenberg eBook #205 | Thoreau died in 1862. |

Cleanup details:

- **Meditations:** only the twelve books are kept.
  The 1906 introduction by W. H. D. Rouse, the Fronto correspondence appendix, the notes and the glossary are removed.
- **Poe:** only the tales are kept.
  The "Notes to the Second Volume" (partly by Poe's editor Griswold) are removed, as are the inline endnote markers such as `(*1)`.
  Square brackets that remain in the text, such as the stage directions in "Mesmeric Revelation", are Poe's own.
- **Pride and Prejudice:** the Project Gutenberg file is the illustrated 1894 edition.
  The title pages, preface, contents, list of illustrations and the illustration captions are removed, and only the novel is kept.
- **Great Expectations:** the contents and illustration placeholders are removed.
- **The Hound of the Baskervilles:** the dedication letter, contents and the leading indentation of each line are removed.
- **Origin of Species:** the title page, epigraphs, contents and the index are removed, and the text runs from the Introduction to the last paragraph.
- **Walden:** only *Walden* is kept, not the essay on civil disobedience that the Project Gutenberg file adds.
- The wording of every text is unchanged.

## Results at a glance

| Metric | Meditations | Poe tales | Pride and Prejudice | Great Expectations | Hound of the Baskervilles | Origin of Species | Walden |
|---|---:|---:|---:|---:|---:|---:|---:|
| Sentences | 2,161 | 4,018 | 5,579 | 8,605 | 3,355 | 4,020 | 3,787 |
| Tokens | 57,410 | 93,857 | 120,914 | 184,077 | 59,227 | 150,355 | 106,673 |
| Type-token ratio | 0.077 | 0.106 | 0.052 | 0.058 | 0.093 | 0.045 | 0.098 |
| Yule's K | 102.2 | 125.3 | 82.0 | 95.8 | 95.4 | 114.0 | 104.6 |
| Mean sentence length (words) | 26.8 | 23.9 | 21.8 | 21.5 | 17.7 | 37.6 | 28.3 |
| Sentence-length stdev / max | 22.0 / 199 | 18.8 / 157 | 16.7 / 124 | 16.2 / 166 | 11.1 / 73 | 21.7 / 213 | 23.0 / 344 |
| Average parse-tree depth | 5.27 | 5.62 | 5.19 | 5.03 | 5.00 | 7.27 | 5.89 |
| Noun-to-verb ratio | 1.18 | 1.29 | 0.84 | 0.88 | 0.97 | 1.24 | 1.24 |
| Commas per 1000 words | 90.1 | 84.6 | 78.5 | 92.6 | 58.0 | 74.2 | 82.7 |
| Semicolons per 1000 words | 12.8 | 8.5 | 13.7 | 6.8 | 0.8 | 11.3 | 9.1 |
| Colons per 1000 words | 7.2 | 0.8 | 1.7 | 0.6 | 0.3 | 1.7 | 0.2 |
| Em dashes per 1000 words | 0.05 | 15.6 | 3.9 | 6.3 | 2.6 | 2.2 | 4.2 |
| Exclamation marks per 1000 words | 0.6 | 4.0 | 3.5 | 5.4 | 3.1 | 0.3 | 1.4 |
| Question marks per 1000 words | 6.9 | 2.4 | 3.9 | 6.6 | 8.8 | 0.7 | 2.4 |
| Rhetorical questions per 100 sentences | 15.4 | 2.6 | 3.8 | 3.3 | 3.3 | 2.6 | 5.8 |
| Hedging per 1000 words | 1.6 | 4.4 | 7.1 | 4.6 | 6.3 | 4.6 | 3.7 |
| Assertive words per 1000 words | 5.0 | 2.3 | 6.0 | 4.0 | 3.8 | 3.4 | 2.7 |
| Narrative voice | second person | first person | third person | first person | first person | first person | first person |
| Pronouns: 1st / 2nd / 3rd person / "it" | 767 / 1,720 / 2,050 / 1,234 | 4,207 / 297 / 2,222 / 1,540 | 3,806 / 1,886 / 9,168 / 1,642 | 12,178 / 2,750 / 8,502 / 2,938 | 3,193 / 1,041 / 2,543 / 1,074 | 2,838 / 3 / 1,791 / 1,486 | 3,772 / 468 / 3,233 / 1,899 |
| Top sentence openers | for, and, but, as, if | I, the, it, and, in | I, she, but, the, it | I, and, it, the, he | I, the, it, he, but | the, but, in, I, we | I, the, it, but, they |
| Top function words | and, of, the, that, to, is | the, of, and, to, a, I | the, to, of, and, her, I | the, and, I, to, of, a | the, and, of, I, to, a | the, of, and, in, to, a | the, and, of, a, to, in |

The full numbers for every text are in each example's `output/*_profile.md`, and the formatted view is in `output/*_report.html`.

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

## Reading the other five profiles

Each of these reads like its author, with the usual caveat that one book is one register.

- **Pride and Prejudice (third person).**
  It is the only text reported in the third person.
  Its 3,806 first-person pronouns and 1,886 second-person pronouns sit mostly inside quoted dialogue, which the voice rule skips.
  "I" and "but" still rank among the top sentence openers because the characters' speeches start that way.
  It has the highest hedging rate of the seven (7.1 per 1000 words), the lowest noun-to-verb ratio (0.84) and many semicolons (13.7), which fits balanced, qualified, conversational prose.
- **Great Expectations (first person).**
  Pip narrates, and "I" opens 1,287 sentences.
  It has the most commas (92.6 per 1000 words) and exclamation marks (5.4) of the seven, plus 6.3 em dashes per 1000 words.
  The sentences are of ordinary length (mean 21.5 words) but the longest runs to 166 words.
- **The Hound of the Baskervilles (first person).**
  Dr. Watson narrates, and the pipeline reports the voice as first person.
  It has the shortest and most even sentences (mean 17.7 words, longest 73) and the sparsest punctuation: 0.8 semicolons and 58 commas per 1000 words.
  Question marks are the highest of the seven (8.8 per 1000 words), because the story is built from questions and deductions in dialogue.
  Its type-token ratio (0.093) is higher than the novels' mainly because the text is much shorter.
- **On the Origin of Species (first person).**
  It has the longest average sentence (37.6 words) and the deepest parse trees (7.27) of the seven, and a noun-to-verb ratio (1.24) well above the three novels.
  Exclamation and question marks are almost absent (0.3 and 0.7 per 1000 words).
  The first-person pronouns are the authorial "I" and "we" of a scholarly argument, and there are only three second-person pronouns in 150,000 tokens.
- **Walden (first person).**
  Thoreau has the longest single sentence of the seven (344 words) and a high mean (28.3 words).
  He asks questions as a method too, with 5.8 rhetorical questions per 100 sentences, the highest after the *Meditations*.
  Hedging and assertive words are both low (3.7 and 2.7 per 1000 words).

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
