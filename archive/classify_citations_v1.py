#!/usr/bin/env python3
"""
Classification of the extracted citations into source categories (version 1 rule).

This file is imported unchanged by analysis/classify_citations.py. Only comments,
docstrings and the reason strings were translated; patterns and logic are as in the
original run.

Categories (rule-based, every single decision traceable in the output file):

  A   ESPEN reference guideline applicable to the item
  A*  ESPEN practical guideline / short version of the same guideline  (subgroup of A)
  B   other guideline or consensus statement (GLIM, EWGSOP, ASPEN/AND, NICE, USPSTF, other ESPEN guidelines)
  C   guideline-derived secondary literature (narrative review that summarises the guideline
      or comes from its authors)
  D   independent scientific evidence (RCT, cohort, meta-analysis, other review)
  F   non-scientific or grey source (patient organisation, learning portal, video, commercial)
  ?   not classifiable

E (earlier guideline edition) is carried as a separate flag, not as an exclusive category,
because an earlier edition can be A or B at the same time. In this version the flag is
set by publication year 2015-2018; merge_documents.py replaces it by an edition comparison.
"""
import csv, re, os, collections

OUT = os.path.dirname(os.path.abspath(__file__))

# ---- category C: guideline-derived secondary literature, fixed by name
#      reason documented for each so that the decision remains checkable
C_WORKS = [
    (r'malnutrition in older adults', r'(new england|nejm)',
     'Cruz-Jentoft & Volkert, NEJM 2025 - review by the ESPEN geriatrics guideline authors'),
    (r'malnutrition in older adults', r'lancet',
     'Dent et al., Lancet 2023 - review summarising the ESPEN geriatrics guideline'),
    (r'malnutrition in adults', r'(new england|nejm)',
     'Cederholm & Bosaeus, NEJM 2024 - review by a GLIM/ESPEN author'),
]

# ---- category A: the three reference guidelines
A_PATTERNS = {
    'ESPEN Geriatrics': [r'geriatric', r'hydration in geriatr'],
    'ESPEN Dementia':   [r'dementia'],
    'ESPEN Polymorbid': [r'polymorbid'],
}
A_GUARD = r'(espen|volkert|wunderle|gomes|bischoff|schuetz)'
PRACTICAL = r'practical guideline'

# ---- category B: other guidelines / consensus statements
B_PATTERNS = [
    r'\bGLIM\b', r'EWGSOP', r'\bASPEN\b', r'academy of nutrition and dietetics',
    r'\bNICE\b', r'preventive services task force', r'consensus (report|statement)',
    r'clinical practice guideline', r'position (of|paper|statement)',
    r'\bICFSR\b', r'sarcopeni[ac] obesity: espen', r'recommendations? (of|from) the',
    r'\bDGEM\b', r'guideline',
]

# ---- category F: non-scientific domains (for URL citations)
F_DOMAINS = {
    'youtube.com', 'droracle.ai', 'merckmanuals.com', 'alz.org', 'alzint.org',
    'alzheimers.org.uk', 'alzheimer.ca', 'alzheimers.gov', 'consultant360.com',
    'wordpress.com', 'olderadultnutritionscreening.wordpress.com', 'healthline.com',
    'webmd.com', 'medscape.com', 'wikipedia.org', 'reddit.com', 'quora.com',
    'nutritioncare.org', 'eatright.org', 'verywellhealth.com', 'patient.info',
    'mayoclinic.org', 'clevelandclinic.org', 'nhs.uk', 'dementiauk.org',
}
SCI_DOMAINS = {
    'pmc.ncbi.nlm.nih.gov', 'pubmed.ncbi.nlm.nih.gov', 'ncbi.nlm.nih.gov',
    'sciencedirect.com', 'jamanetwork.com', 'nejm.org', 'thelancet.com',
    'nature.com', 'bmj.com', 'springer.com', 'link.springer.com', 'wiley.com',
    'onlinelibrary.wiley.com', 'academic.oup.com', 'frontiersin.org', 'mdpi.com',
    'cochranelibrary.com', 'karger.com', 'tandfonline.com', 'sagepub.com',
    'journals.lww.com', 'cambridge.org', 'plos.org', 'biomedcentral.com',
}
GUIDELINE_DOMAINS = {
    'espen.org', 'andeal.org', 'bda.uk.com', 'nice.org.uk',
    'uspreventiveservicestaskforce.org', 'bpac.org.nz', 'eatrightpro.org',
}

OLD_YEARS = {'2015', '2016', '2017', '2018'}

# ---- extended domain assignment for the URL citations of Sonar Reasoning Pro
#      aim: lower the share of unclassified sources far enough that the reported
#      share of grey literature becomes robust
PUBLISHER_PAT = re.compile(
    r'(onlinelibrary\.wiley|springer|sciencedirect|elsevier|nature\.com|bmj\.com|'
    r'jamanetwork|nejm\.org|thelancet|academic\.oup|karger|mdpi|frontiersin|'
    r'cochranelibrary|cochrane\.org|tandfonline|sagepub|journals\.lww|cambridge\.org|'
    r'plos\.org|biomedcentral|agsjournals|japi\.org|jarlife\.net|physiology\.org|'
    r'ahajournals|acpjournals|annals\.org|jamda|clinicalnutritionjournal|'
    r'nutritionj|bmcgeriatr|dovepress|hindawi|scielo|researchgate|semanticscholar|'
    r'europepmc|ouci\.dntb|osti\.gov|\.unibe\.ch|repository\.|eprints\.)', re.I)

SOCIETY_PAT = re.compile(
    r'(bgs\.org\.uk|bapen\.org\.uk|nutritioncare\.org|paltmed\.org|aafp\.org|'
    r'aahpm\.org|dietitians|dietetic|nice\.org\.uk|uspreventive|espen\.org|'
    r'andeal\.org|bda\.uk\.com|eatrightpro|malnutritionquality|crns\.ca|'
    r'anfponline|nccdp\.org|isdi\.org|bpac\.org\.nz|geriatrics|nutritionsociety|'
    r'esmo\.org|who\.int|nhmrc\.gov\.au|sign\.ac\.uk|guidelinecentral)', re.I)

LAY_PAT = re.compile(
    r'(facebook|youtube|twitter|instagram|linkedin|reddit|quora|tiktok|'
    r'agingcare|caregiver|ncoa\.org|seniorservices|guidestar|hebrewseniorlife|'
    r'alz\.|alzheimer|alzint|alzra|alzdiscovery|dementia(uk|society)|'
    r'bannerhealth|ouhealth|lonestar|dietitiansondemand|todaysdietitian|'
    r'hmpglobal|hcpa\.info|mna-elderly|droracle|merckmanuals|healthline|webmd|'
    r'verywell|patient\.info|mayoclinic|clevelandclinic|medlineplus|'
    r'consultant360|wordpress|blogspot|medium\.com|hign\.org|caresearch|'
    r'generations\.asaging|nutrition\.org\.uk|helpguide|aarp)', re.I)

GOVHEALTH_PAT = re.compile(
    r'(albertahealthservices|health\.vic\.gov|nhs\.uk|healthdirect|'
    r'ilaging\.illinois|\.gov\.au|hse\.ie|canada\.ca)', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', (s or '')).strip().lower()


def classify(rec):
    """Returns (category, reason, outdated_flag)."""
    title = norm(rec['title'])
    journal = norm(rec['journal'])
    author = norm(rec['author'])
    raw = norm(rec['raw'])
    url = rec['url']
    host = rec['domain_host']
    year = rec['year']
    blob = f'{title} {journal} {author} {raw}'

    # --- URL citations (Sonar) ---
    if url:
        if host in GUIDELINE_DOMAINS or 'espen' in url.lower():
            item = rec['item_guideline'] or ''
            for k, pats in A_PATTERNS.items():
                if k.split()[-1].lower() in item.lower():
                    if any(re.search(p, url, re.I) for p in pats):
                        return 'A', f'URL on {host}, title pattern matches the item guideline', False
            return 'B', f'guideline domain {host}', False
        if host in F_DOMAINS:
            return 'F', f'non-scientific domain {host}', False
        if host in SCI_DOMAINS:
            return 'D', f'scientific domain {host}', False
        # extended assignment, order deliberate: lay source beats professional society,
        # because patient portals can be run by professional societies
        if LAY_PAT.search(url):
            return 'F', f'lay, patient or commercial source ({host})', False
        if PUBLISHER_PAT.search(url):
            return 'D', f'publisher or repository domain ({host})', False
        if SOCIETY_PAT.search(url):
            return 'B', f'professional society or guideline body ({host})', False
        if GOVHEALTH_PAT.search(url):
            return 'F', f'health authority, patient information ({host})', False
        if host.endswith('.edu') or '.ac.' in host:
            return 'D', f'university domain ({host})', False
        return '?', f'domain {host} not assigned', False

    # --- bibliographic citations (GPT-5.5, Open Evidence) ---
    old = year in OLD_YEARS

    # C first: otherwise "review" would slip through as D
    for tpat, jpat, why in C_WORKS:
        if re.search(tpat, blob) and re.search(jpat, blob):
            return 'C', why, old

    # A: reference guideline applicable to the item
    item = rec['item_guideline'] or ''
    if re.search(A_GUARD, blob):
        for k, pats in A_PATTERNS.items():
            keyword = k.split()[-1].lower()          # geriatrics / dementia / polymorbid
            if keyword[:8] in item.lower().replace('geriatrics', 'geriatric'):
                if any(re.search(p, blob) for p in pats):
                    if re.search(PRACTICAL, blob):
                        return 'A*', 'ESPEN practical guideline, short version of the same guideline', old
                    return 'A', 'ESPEN reference guideline applicable to the item', old
        # ESPEN guideline, but not the one of the item
        if re.search(r'espen', blob) and re.search(r'guideline', blob):
            return 'B', 'ESPEN guideline, but not the one applicable to the item', old

    # B: other guideline / consensus
    for p in B_PATTERNS:
        if re.search(p, blob, re.I):
            return 'B', f'guideline/consensus pattern: {p}', old

    # Open Evidence's own label as an additional signal
    if rec['oe_tag'] == 'Guideline':
        return 'B', 'own label of Open Evidence: Guideline', old
    if rec['oe_tag'] in ('Review', 'RCT', 'Recent'):
        return 'D', f'own label of Open Evidence: {rec["oe_tag"]}', old

    if title or author:
        return 'D', 'scientific publication without guideline feature', old
    return '?', 'too little information', old


def main():
    # legacy entry point of version 1; the current pipeline imports classify() only
    recs = list(csv.DictReader(open(f'{OUT}/citations_raw.csv')))
    for r in recs:
        cat, why, old = classify(r)
        r['category'] = cat
        r['reason'] = why
        r['outdated_flag'] = 'yes' if old else ''

    fn = f'{OUT}/classified_citations.csv'
    with open(fn, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(recs[0].keys()))
        w.writeheader()
        w.writerows(recs)
    print(f'{len(recs)} citations classified -> {fn}')

    print('\n### Citation categories per system (share of all citations)')
    hdr = ['A', 'A*', 'B', 'C', 'D', 'F', '?']
    print('  %-22s %s' % ('', '  '.join(f'{h:>5}' for h in hdr) + '   total'))
    for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
        sub = [r for r in recs if r['model'] == m]
        c = collections.Counter(r['category'] for r in sub)
        line = '  '.join(f'{100*c[h]/len(sub):4.0f}%' for h in hdr)
        print(f'  {m:22s} {line}   {len(sub)}')

    print('\n### Key figure: share of responses with at least one citation of category A/A*')
    for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
        byans = collections.defaultdict(set)
        for r in recs:
            if r['model'] == m:
                byans[r['rating_id']].add(r['category'])
        hasA = sum(1 for v in byans.values() if 'A' in v or 'A*' in v)
        print(f'  {m:22s} {hasA:2d}/60  ({100*hasA/60:.1f} %)')

    print('\n### Cross-tabulation with the consensus rating of guideline reference')
    for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
        print(f'  {m}')
        byans = {}
        for r in recs:
            if r['model'] == m:
                byans.setdefault(r['rating_id'], {'glr': r['glr'], 'cats': set()})
                byans[r['rating_id']]['cats'].add(r['category'])
        for glr in ['Yes', 'Partly', 'No']:
            sel = [v for v in byans.values() if v['glr'] == glr]
            if not sel:
                continue
            a = sum(1 for v in sel if 'A' in v['cats'] or 'A*' in v['cats'])
            c = sum(1 for v in sel if 'C' in v['cats'])
            b = sum(1 for v in sel if 'B' in v['cats'])
            print(f'     GLR={glr:6s} n={len(sel):2d} | with A {a:2d} | with B {b:2d} | with C {c:2d}')


if __name__ == '__main__':
    main()
