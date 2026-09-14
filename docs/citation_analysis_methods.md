# Citation analysis: method

Version 3 of the extraction, revised 2 September 2026. Version 2 added the bracket
citations of Sonar Reasoning Pro that version 1 had missed; version 3 added duplicate
detection via document identity and the determination of earlier guideline editions.
The category revision and the restriction to in-text citations were added afterwards
and are described in the last two sections.

Scripts: `analysis/extract_citations.py`, `classify_citations.py`, `build_long_table.py`,
`merge_documents.py`, `document_identity.py`, `validate_extraction.py`,
`revise_categories.py`, `in_text_citations.py`, `table5_citation_sources.py`.

## Citation formats recognised per system

The three systems give their sources in different formats. For each system the
format it uses is recognised; a system may mix several formats.

**Open Evidence** lists a numbered reference list at the end of each response with
title, journal, year and author. The numbered list item at the start of a line is
recognised. Identifiers are not given.

**GPT-5.5** places bibliographic bracket citations in the running text, in the form
`[author, year, title/journal, identifier]`. The square-bracketed expression is
recognised.

**Sonar Reasoning Pro** uses **two** formats side by side: a list of bare URLs at the
end of the response and, in addition, bibliographic bracket citations in the running
text, sometimes with a preceding source-type label (`Guideline: Volkert, 2019, ...`).
Both are captured.

A bracketed expression counts as a bibliographic citation if it contains a
four-digit year and at least two commas and is between 20 and 400 characters long.
References such as `[1]` or labels such as `[Guideline]` thereby drop out. A
preceding source-type label is removed before the test.

## Merging of duplicates

The same document can occur in both formats with Sonar. Merging runs along two paths.

**Via the identifier.** Identity in this order: DOI, then PubMed identifier, then
normalised title. DOI and PubMed identifier are read out of a URL where present.
9 cases.

**Via the document identity.** A guideline document can appear bibliographically and
at the same time as an espen.org link without a shared identifier. For this case an
identity is formed from three parts: family (geriatrics, dementia, polymorbid),
variant (full text or practical guideline) and edition. The espen.org file names carry
the edition only partly; where it is missing, family and variant decide, because
espen.org keeps one file per guideline and updates it. 13 cases.

**Full text and short version are not merged.** In three responses a bracket citation
of the full text stands next to the espen.org URL of the practical guideline. These
are two publications with their own DOIs, and the categories A and A* separate them
deliberately. They count as two documents. Merging them would give 16 instead of 13
merges and 860 instead of 863 citations for Sonar.

A merge produces **one** record. The bibliographic data take precedence, because the
category rule has more information with author, title and journal than with a URL
alone; the URL is kept in `url_also`. `source_format` records where the record came
from: `numbered_list`, `bracket`, `url_list` or `both`.

## Categories

The category rule of version 1 is applied **unchanged** and imported from
`archive/classify_citations_v1.py`. It assigns:

| Code | Meaning |
|---|---|
| A | the ESPEN guideline applicable to the item |
| A* | its short version (practical guideline) |
| B | other guideline or consensus document |
| C | narrative review that summarises the guideline, often by its authors |
| D | independent scientific evidence |
| F | non-scientific source |
| ? | not classifiable |

For bibliographic citations a pattern match over title, journal and author decides;
for bare URL citations the domain. **This is an unequal treatment that has to be
named:** a URL citation carries less information, and its assignment is
correspondingly coarser. Sonar is most affected, because 779 of its 876 extracted
citations exist only as URLs.

## Earlier guideline editions

The marker is a separate feature, not a category, because an earlier edition can be
A or B at the same time.

Versions 1 and 2 flagged every citation with publication year 2015 to 2018. That was
wrong: it also hit primary studies, which do not go out of date, and guidelines of
other societies for which we do not know whether a newer edition exists. For Open
Evidence all nine citations so flagged were ACG, NICE or ASPEN documents from 2016 to
2018.

Version 3 compares instead the **cited edition with the current one**: geriatrics
2019, polymorbidity 2023, dementia 2024. Only what has demonstrably been replaced is
flagged. Documents outside these three families are not judged, because the current
edition there is not known to us. This is a deliberate gap; it produces no false
positives.

Known under-detection: the flag requires that the edition can be read from the
source. For four Sonar citations of the 2018 polymorbidity guideline that are linked
via nespen.nl instead of espen.org this fails. Sonar is thus in fact at 11 rather than
8 of 60 responses; the table value follows the definition.

At response level: Open Evidence 0 of 60, GPT-5.5 38 of 60, Sonar 8 of 60.

## Category revision (Supplementary Material S4)

`revise_categories.py` corrects four constellations in which the domain rule
misfires (BDA Food Fact Sheets, a NICE decision aid, an ESPEN guideline not
applicable to the item, the practical guideline as short version) and resolves the
151 citations of category `?` by an individual assignment per domain, each with
reason and method of verification. In addition it marks manufacturer or provider
content as commercial, independent of the category.

**Reclassification.** The manuscript defines non-scientific sources as content
published outside a scientific process and counts journals, preprints, theses and
institutional reports as independent evidence irrespective of indexing. The original
rule had made the assignment depend on PubMed indexing. Under the manuscript's
definition eighteen domains move from F to D: eleven journals without PubMed index
(13 citations), two institutional research reports (8), two theses (2), one preprint,
one library scan and one society document. 27 citations, all from Sonar Reasoning
Pro. The reason field of these citations carries the note "reclassified: scientific
publication, irrespective of PubMed indexing".

Every domain carries a method of verification, with the labels of Supplementary
Material S4: `PubMed query` where an identifier was checked against PubMed, `Page
content` where the page was opened and its content checked. Cases initially left
open were resolved individually before submission.

## In-text citations (basis of Table 5)

Only citations that the response invokes in its running text are counted.
`in_text_citations.py` decides that per citation: bracket citations are in the text
by construction; entries of a numbered list or a URL list count if their position
occurs in the text as `[n]`; where the position cannot be determined the citation is
counted (conservative). Reason: for Sonar Reasoning Pro the appended URL list does not
come from the model but from the citations field of the Perplexity API. Counting it
measures the hit list of a search engine rather than the citation behaviour.

The rule applies uniformly: Open Evidence 290 of 431 citations invoked, GPT-5.5 168
of 168, Sonar Reasoning Pro 400 of 863. The analysis over all extracted citations is
the sensitivity analysis in Supplementary Material S5.

## Validation

`validate_extraction.py` counts per response, independently of the parser, how many
citations of each format are in the response text and compares that with the number
of extracted citations. Deviations are printed per response.

Against version 1 (`archive/citations_long_v1.csv`) the script reports 32 responses
with deviations, among them 31 from Sonar with missing bracket citations. The three
false alarms it initially raised for Open Evidence were German date strings in the
response text ("12. Juni 2025") that look like numbered list items; the rule now
excludes month names. Against version 3 one deviation remains, and that is not a gap
but a counting convention: in one GPT-5.5 response the same guideline is cited twice,
the parser keeps both, the check counts them as one document.

The script should be run after every change to the parser.
