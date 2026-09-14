# -*- coding: utf-8 -*-
"""Check of the text completeness of the stored model responses (basis of Supplementary Material S6).

Checks two independent things:

  1. Checksum. The unblinding key holds a SHA-256 of the original text of each
     response. If the stored text deviates, it was altered on its way into the
     rating workbook. Known causes: swallowed line starts, doubled quotation marks
     from a CSV round trip. Extent one or two characters each, without effect on
     content.

  2. Truncation. If the response text ends without terminal punctuation, it breaks
     off mid-sentence. For Sonar Reasoning Pro the part before the appended source
     block is considered, because that block does not come from the model: the
     Perplexity API returns the sources as a separate field beside the response
     text, and the collection script appended it to the text.

  In addition, the script records in which of the three sections prescribed by
  the prompt the truncation falls and whether the safety note is missing. Where
  the safety note is missing it cannot be decided whether there was nothing to
  report or whether the text ended before.

The raw data are not deposited. Path via environment variable:
    export NUTRITION_RAW=/path/to/raw/data

Usage:
    python3 text_completeness.py [output.csv]

Requires openpyxl.
"""
import csv, sys, os, re, hashlib, collections, statistics
import openpyxl

RAW = os.environ.get('NUTRITION_RAW', '.')
KONSENS = 'Final_Konsens_Nutrition_master_rating_Konsensabgleich.xlsx'
SCHLUESSEL = 'Nutrition_master_rating_key_3models_DO_NOT_SHARE.xlsx'
MODELL = {'Open Evidence': 'Open Evidence',
          'gpt-5.5-2026-04-23': 'GPT-5.5',
          'sonar-reasoning-pro': 'Sonar Reasoning Pro'}
ENDZEICHEN = '.!?:;)]»"\u201d\u2019\'*'

# The truncation test presupposes that the response ends with prose. Open Evidence
# ends with a reference list whose last line is regularly a journal name without
# punctuation. For that system the test is not applicable and is not computed,
# rather than rescued with heuristics.
PROSA_ENDE = {'GPT-5.5', 'Sonar Reasoning Pro'}


def blatt(pfad, name):
    ws = openpyxl.load_workbook(pfad, data_only=True)[name]
    kopf = [c.value for c in ws[1]]
    return [d for d in (dict(zip(kopf, r)) for r in ws.iter_rows(min_row=2, values_only=True))
            if d.get('Rating ID')]


def textkoerper(t):
    """Response text without the source apparatus at the end.

    Two forms are removed because both regularly end without punctuation and
    would otherwise trigger the truncation test falsely:
      - the block 'Sources:' with bare URLs appended mechanically for Sonar
      - the numbered reference list of Open Evidence ('1. ', '2. ', ...)
    """
    m = re.search(r'Sources:', t)
    b = (t[:m.start()] if m else t).rstrip()
    zeilen = b.split('\n')
    # Start of a numbered list: a line '1.' or '1. Title' followed by at least
    # two further numbered lines.
    zaehl = re.compile(r'^\s*\d{1,3}\.\s*(\S.*)?$')
    for i, z in enumerate(zeilen):
        if re.match(r'^\s*1\.\s*(\S.*)?$', z):
            if sum(1 for w in zeilen[i + 1:] if zaehl.match(w)) >= 2:
                b = '\n'.join(zeilen[:i]).rstrip()
                break
    return b


def abgeschnitten(t):
    b = textkoerper(t)
    return bool(b) and b[-1] not in ENDZEICHEN


def abschnitt(b):
    """In which of the three prompt sections does the text end?"""
    treffer = {}
    for name, muster in [('1 Direct answer', r'(?i)direct answer'),
                         ('2 Evidence and reasoning', r'(?i)evidence and reasoning'),
                         ('3 Safety note', r'(?i)safety note')]:
        m = list(re.finditer(muster, b))
        if m:
            treffer[name] = m[-1].start()
    return max(treffer, key=treffer.get) if treffer else '(no section recognisable)'


def main(ziel):
    schluessel = {d['Rating ID']: d for d in blatt(os.path.join(RAW, SCHLUESSEL), 'Row Key')}
    zeilen = blatt(os.path.join(RAW, KONSENS), 'Rating')

    pruefsumme, aus = [], []
    for d in zeilen:
        rid = d['Rating ID']
        t = d['Model answer'] or ''
        erwartet = schluessel[rid].get('Model answer SHA-256')
        if erwartet and erwartet != hashlib.sha256(t.encode('utf-8')).hexdigest():
            pruefsumme.append(rid)
        modell = MODELL[schluessel[rid]['Actual model']]
        if modell not in PROSA_ENDE or not abgeschnitten(t):
            continue
        b = textkoerper(t)
        aus.append(dict(rating_id=rid, model=modell,
                        domain=d['Domain'], question_id=d['Question ID'],
                        question_type=d['Question type'], item_guideline=d['Guideline'],
                        chars=len(b), truncated_in=abschnitt(b),
                        safety_note_present='yes' if re.search(r'(?i)safety note', b) else 'no',
                        last_60_chars=b[-60:].replace('\n', ' ')))

    aus.sort(key=lambda r: (r['model'], r['rating_id']))
    with open(ziel, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(aus[0].keys()))
        w.writeheader()
        w.writerows(aus)

    print('%d responses checked' % len(zeilen))
    print('checksum deviates: %d' % len(pruefsumme))
    print('text truncated: %d' % len(aus))
    for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
        if m not in PROSA_ENDE:
            print('   %-22s not applicable (response ends with a reference list)' % m)
            continue
        print('   %-22s %2d of 60' % (m, len([r for r in aus if r['model'] == m])))
    son = [r for r in aus if r['model'] == 'Sonar Reasoning Pro']
    if son:
        print('   truncated in: %s' % dict(collections.Counter(r['truncated_in'] for r in son)))
        print('   without safety note: %d' % sum(1 for r in son if r['safety_note_present'] == 'no'))
        print('   length of prose body, median: %d chars' % statistics.median([r['chars'] for r in son]))
    print('written: %s' % ziel)
    print()
    print('Reference values - a run must reproduce these:')
    print('  checksum deviations depend on the private key version (15 in the audited local copy)')
    print('  text truncated             22 of 120 checked')
    print('     Open Evidence            not applicable')
    print('     GPT-5.5                  0 of 60')
    print('     Sonar Reasoning Pro     22 of 60')
    print('  Sonar, truncated in section  1 Direct answer 4 / 2 Evidence 15 / 3 Safety 2 / no section 1')
    print('  Sonar, without safety note  20 of 22')
    print('  Sonar, median prose body  2344 chars (complete responses: 3510)')


if __name__ == '__main__':
    z = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'truncated_responses.csv')
    main(z)
