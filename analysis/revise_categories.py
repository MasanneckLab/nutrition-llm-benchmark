# -*- coding: utf-8 -*-
"""Revision of the citation categories (Supplementary Material S4).

Works on citations_long_v3.csv and changes two things:

  A) Four corrections to the existing assignment. The category rule in
     archive/classify_citations_v1.py decides URL citations by domain and a
     search pattern in the path. In four constellations that misfires because the
     domain is right but the document behind it is not:

       1. bda.uk.com/resource/...          Food Fact Sheets of the British Dietetic
                                           Association, patient information, not
                                           the applicable guideline.  A -> F
       2. nice.org.uk/guidance/ng97/resources/...
                                           NICE patient decision aid.  A -> B
       3. clinicalnutrition.science/.../parenteral-nutrition-geriatrics/
                                           ESPEN guideline, but not the one of the item;
                                           the hit came from the word dementia in the
                                           path segment geriatrics-and-dementia.  A -> B
       4. espen.org/.../ESPEN_practical_guideline_...
                                           short version of the same guideline.  A -> A*

  B) Resolution of category '?'. In version v3, 151 citations are unassigned
     because their domain is in no pattern list. The assignment below was made
     individually; DOMAINS documents category, reason and method of verification
     per domain, using the labels of Supplementary Material S4. 'PubMed query':
     identifier queried against PubMed on 22 Aug 2026. 'Page content': the page
     was opened and its content checked. Every domain carries one of the two;
     the cases initially marked as open were resolved individually before submission.

Rule order on which the assignment rests:
  1. guideline applicable to the item                    -> A  (short version A*)
  2. other guideline or consensus statement              -> B
  3. narrative review derived from a reference guideline -> C
  4. published through a scientific process              -> D
  5. otherwise                                           -> F
  Additionally the marker 'commercial' for manufacturer or provider content,
  independent of the category.

  C) Reclassification under the manuscript's definition (Methods 2.5): journals,
     preprints, theses and institutional reports count as independent evidence
     irrespective of indexing. Eighteen domains that the PubMed-based rule had put
     in F are D; see RECLASSIFIED. 27 citations, all Sonar Reasoning Pro.

Usage:
    python3 revise_categories.py [../data/citations_long_v3.csv] [output.csv]

Without arguments: ../data/citations_long_v3.csv -> ../data/category_revision.csv
Standard library only.
"""
import csv, sys, os, re, collections

# ---------------------------------------------------------------- domain table
# (category, reason, verification, commercial)
DOMAINS = {
    # -- B: guidelines and consensus statements of other issuers
    'acponline.org':            ('B', 'ACP/AAFP clinical guideline on dementia treatment', 'Page content', 0),
    'has-sante.fr':             ('B', 'Haute Autorite de Sante, national malnutrition guideline', 'Page content', 0),
    'strokebestpractices.ca':   ('B', 'Canadian Stroke Best Practice Recommendations', 'Page content', 0),
    'racgp.org.au':             ('B', 'RACGP, national general practice guideline on dementia', 'Page content', 0),
    'nationalacademies.org':    ('B', 'NASEM consensus report', 'Page content', 0),
    'malnutritionpathway.co.uk':('B', 'Managing Adult Malnutrition, consensus pathway of British professional bodies', 'Page content', 0),
    'nestlehealthscience.com':  ('B', 'ASPEN guideline hosted on a manufacturer site', 'Page content', 1),
    'clinicalnutrition.science':('B', 'NutriBib, guideline collection', 'Page content', 0),

    # -- D: findable via PubMed
    'jacc.org':                 ('D', 'JACC Advances, PMID 38938359', 'PubMed query', 0),
    'e-cnr.org':                ('D', 'Clinical Nutrition Research, PMID 40386660', 'PubMed query', 0),
    'cureus.com':               ('D', 'Cureus, PMID 41281079', 'PubMed query', 0),
    'ovid.com':                 ('D', 'NEJM review, full-text link via Ovid', 'Page content', 0),
    'researchportal.ukhsa.gov.uk': ('D', 'repository entry of a published paper', 'Page content', 0),
    'ccjm.org':                 ('D', 'Cleveland Clinic Journal of Medicine', 'Page content', 0),
    'archivesofmedicalscience.com': ('D', 'Archives of Medical Science', 'Page content', 0),
    'jstage.jst.go.jp':         ('D', 'Journal of UOEH via J-Stage', 'Page content', 0),
    'cfrjournal.com':           ('D', 'Cardiac Failure Review', 'Page content', 0),

    # -- D: journals without PubMed index (reclassified, see docstring)
    'pubs.asha.org':            ('F', 'ASHA Perspectives, identifier not resolvable', 'PubMed query', 0),
    'austinpublishinggroup.com':('D', 'Austin Publishing Group', 'Page content', 0),
    'esmed.org':                ('D', 'Medical Research Archives, European Society of Medicine', 'Page content', 0),
    'journals.rcni.com':        ('D', 'Nursing Older People, identifier not resolvable', 'Page content', 0),
    'aging-us.com':             ('F', 'press release in the news room, not a journal article', 'Page content', 0),
    'jnursinghomeresearch.com': ('D', 'Journal of Nursing Home Research', 'Page content', 0),
    'ispub.com':                ('D', 'Internet Scientific Publications', 'Page content', 0),
    'clinical-nutrition.imedpub.com': ('D', 'iMedPub', 'Page content', 0),
    'ifnmujournal.com':         ('D', 'Galician Medical Journal', 'Page content', 0),
    'ejgg.org':                 ('D', 'European Journal of Geriatrics and Gerontology', 'Page content', 0),
    'dergipark.org.tr':         ('D', 'Dergipark, Turkish journal platform', 'Page content', 0),
    'binasss.sa.cr':            ('D', 'library scan, journal not identifiable', 'Page content', 0),
    'cfps.org.sg':              ('D', 'The Singapore Family Physician', 'Page content', 0),
    'bcmj.org':                 ('D', 'BC Medical Journal', 'Page content', 0),

    # -- F -> D where a thesis or preprint: theses, repositories, preprints (reclassified, see docstring)
    'papers.ssrn.com':          ('D', 'SSRN preprint', 'Page content', 0),
    'diva-portal.org':          ('D', 'thesis, Swedish repository', 'Page content', 0),
    'scholarlypublications.universiteitleiden.nl': ('D', 'thesis, Leiden', 'Page content', 0),
    'wp.ufpel.edu.br':          ('F', 'file storage of a Brazilian university', 'Page content', 0),
    'challengesandinitiatives.trubox.ca': ('F', 'course file storage, PDF without publisher', 'Page content', 0),
    'smgg.es':                  ('F', 'article PDF of a Spanish professional society', 'Page content', 0),
    'aanep.org.ar':             ('D', 'document download, Argentine nutrition society', 'Page content', 0),
    'cieah.ulpgc.es':           ('F', 'information page of a university centre', 'Page content', 0),
    'mcgill.ca':                ('F', 'brochure of the manufacturer of Hydralyte, Woodward 2013', 'Page content', 1),

    # -- F: professional societies, no guideline character
    'apta.org':                 ('F', 'description of the MNA test, resource page', 'Page content', 0),
    'aapa.org':                 ('F', 'toolkit page, not a guideline', 'Page content', 0),
    'siog.org':                 ('F', 'educational page on CGA', 'Page content', 0),
    'heart.org':                ('F', 'AHA news article', 'Page content', 0),
    'healthinaging.org':        ('F', 'AGS foundation, patient information', 'Page content', 0),
    'ohioafp.org':              ('F', 'association article', 'Page content', 0),
    'sepsis.org':               ('F', 'Sepsis Alliance, patient information', 'Page content', 0),
    'nia.nih.gov':              ('F', 'NIA information page', 'Page content', 0),

    # -- F: agencies, care organisations, hospitals
    'acl.gov':                  ('D', 'Administration for Community Living, fact sheets', 'Page content', 0),
    'aspe.hhs.gov':             ('D', 'ASPE commissioned research report, RTI International', 'Page content', 0),
    'health.state.mn.us':       ('F', 'WIC manual of a state agency', 'Page content', 0),
    'services.nhslothian.scot': ('F', 'local care pathway, NHS Lothian', 'Page content', 0),
    'milkeninstitute.org':      ('F', 'think tank report', 'Page content', 0),
    'defeatmalnutrition.today': ('F', 'statement of a campaign coalition', 'Page content', 0),
    'mealsonwheelsamerica.org': ('F', 'service organisation', 'Page content', 0),
    'pblob1storage.blob.core.windows.net': ('F', 'NADRC handbook, file storage', 'Page content', 0),
    'nationwidechildrens.org':  ('F', 'hospital information page', 'Page content', 0),
    'ucsfhealth.org':           ('F', 'hospital patient information', 'Page content', 0),
    'mdanderson.org':           ('F', 'hospital blog', 'Page content', 0),
    'barrowneuro.org':          ('F', 'in-house magazine of a hospital', 'Page content', 0),

    # -- F: trade press, blogs, learning portals
    'caringfortheages.com':     ('F', 'AMDA association newspaper', 'Page content', 0),
    'practicalgastro.com':      ('F', 'journal without indexing', 'Page content', 0),
    'todaysgeriatricmedicine.com': ('F', 'trade magazine', 'Page content', 0),
    'nursingtimes.net':         ('F', 'trade magazine', 'Page content', 0),
    'bjgplife.com':             ('F', 'companion blog of the BJGP', 'Page content', 0),
    'geripal.org':              ('F', 'Blog', 'Page content', 0),
    'emcrit.org':               ('F', 'blog, Internet Book of Critical Care', 'Page content', 0),
    'evolutionmedicine.com':    ('F', 'Blog', 'Page content', 0),
    'oncohemakey.com':          ('F', 'mirror page of a book chapter', 'Page content', 0),
    'physio-pedia.com':         ('F', 'Wiki', 'Page content', 0),
    'geekymedics.com':          ('F', 'learning portal', 'Page content', 0),
    'osmosis.org':              ('F', 'learning portal', 'Page content', 0),
    'studocu.com':              ('F', 'student notes exchange', 'Page content', 0),
    'dysphagiacafe.com':        ('F', 'Blog', 'Page content', 0),
    'medicalnewstoday.com':     ('F', 'lay portal', 'Page content', 0),
    'emedicine.medscape.com':   ('F', 'Medscape Reference', 'Page content', 0),
    'nutritionalassessment.org':('F', 'home page without a document', 'Page content', 0),
    'edr.iaedpfoundation.com':  ('F', 'association magazine on eating disorders', 'Page content', 0),
    'compassionandchoices.org': ('F', 'advocacy organisation', 'Page content', 0),
    'dementia.org.au':          ('F', 'patient and caregiver organisation', 'Page content', 0),
    'dementianc.org':           ('F', 'patient and caregiver organisation', 'Page content', 0),
    'hospicefoundation.ie':     ('F', 'foundation, fact sheet', 'Page content', 0),
    'benrose.org':              ('F', 'service organisation', 'Page content', 0),

    # -- F, commercial: manufacturers, providers, service companies
    'nestlemedicalhub.com':     ('F', 'Nestle Health Science, product portal', 'Page content', 1),
    'proconnect.abbott':        ('F', 'Abbott, manufacturer portal', 'Page content', 1),
    'frieslandcampinainstitute.com': ('F', 'FrieslandCampina, manufacturer institute', 'Page content', 1),
    'lllnutrition.com':         ('F', 'training module with manufacturer ties', 'Page content', 1),
    'sqwincher.com':            ('F', 'beverage manufacturer', 'Page content', 1),
    'gfs.com':                  ('F', 'food wholesaler', 'Page content', 1),
    'momsmeals.com':            ('F', 'meal delivery service', 'Page content', 1),
    'goodrx.com':               ('F', 'commercial health portal', 'Page content', 1),
    'betterrx.com':             ('F', 'hospice medication provider', 'Page content', 1),
    'pabau.com':                ('F', 'practice software, template', 'Page content', 1),
    'completedentalworks.com.au': ('F', 'dental practice', 'Page content', 1),
    'h2health.com':             ('F', 'therapy provider', 'Page content', 1),
    'resource.medpro.com':      ('F', 'insurer, risk management', 'Page content', 1),
    'asteroidhealth.com':       ('F', 'provider blog', 'Page content', 1),
    'neuraleffects.com':        ('F', 'provider blog', 'Page content', 1),
    'elmirageer.com':           ('F', 'emergency clinic, promotional blog', 'Page content', 1),
    'stellishealth.com':        ('F', 'provider blog', 'Page content', 1),
    'healthmatters.io':         ('F', 'commercial laboratory value explanation service', 'Page content', 1),
    'certificates.stanmoreuk.org': ('F', 'certificate provider', 'Page content', 1),
    'nursingcecentral.com':     ('F', 'continuing education provider', 'Page content', 1),
    'medbridge.com':            ('F', 'continuing education provider', 'Page content', 1),
    'centerwatch.com':          ('F', 'trial listing', 'Page content', 1),
    'ctv.veeva.com':            ('F', 'trial listing', 'Page content', 1),
    'nursinghomelawcenter.org': ('F', 'law firm advertising', 'Page content', 1),
    'nursinghometruth.com':     ('F', 'law firm advertising', 'Page content', 1),
    'thegoodcaregroup.com':     ('F', 'home care provider', 'Page content', 1),
    'assistinghands.com':       ('F', 'home care provider', 'Page content', 1),
    'arcadiahomecare.com':      ('F', 'home care provider', 'Page content', 1),
    'brightstarcare.com':       ('F', 'home care provider', 'Page content', 1),
    'rightathome.net':          ('F', 'home care provider', 'Page content', 1),
    'whitsymsinhomecare.com':   ('F', 'home care provider', 'Page content', 1),
    'careforth.com':            ('F', 'home care provider', 'Page content', 1),
    'thekey.com':               ('F', 'home care provider', 'Page content', 1),
    'americarepluspc.com':      ('F', 'home care provider', 'Page content', 1),
    'lovedayandco.com':         ('F', 'care provider', 'Page content', 1),
    'crossroadshospice.com':    ('F', 'hospice operator', 'Page content', 1),
    'generationshospicecare.com': ('F', 'hospice operator', 'Page content', 1),
    'aldendesplaines.com':      ('F', 'care home operator', 'Page content', 1),
    'summersetalc.com':         ('F', 'care home operator', 'Page content', 1),
    'koelschseniorcommunities.com': ('F', 'care home operator', 'Page content', 1),
    'memorylanehome.com':       ('F', 'care home operator', 'Page content', 1),
    'irisseniorliving.com':     ('F', 'care home operator', 'Page content', 1),
    'kingstonatdupont.com':     ('F', 'care home operator', 'Page content', 1),
    'themanorvillageusa.com':   ('F', 'care home operator', 'Page content', 1),
    'chestnutsquare.info':      ('F', 'care home operator', 'Page content', 1),
    'shakerplace.org':          ('F', 'care home operator', 'Page content', 1),
    'terravista.org':           ('F', 'care home operator', 'Page content', 1),
    'sgmays.org':               ('F', 'care home operator', 'Page content', 1),
}


# Domains moved from F to D on 2 Sep 2026 under the manuscript's definition (Methods 2.5):
# journals, preprints, theses and institutional reports count as independent evidence
# irrespective of indexing. Reason, verification and commercial marker unchanged.
# 18 domains, 27 citations, all Sonar Reasoning Pro.
RECLASSIFIED = {
    'acl.gov', 'aanep.org.ar', 'aspe.hhs.gov', 'austinpublishinggroup.com', 'bcmj.org',
    'binasss.sa.cr', 'cfps.org.sg', 'clinical-nutrition.imedpub.com', 'dergipark.org.tr',
    'diva-portal.org', 'ejgg.org', 'esmed.org', 'ifnmujournal.com', 'ispub.com',
    'jnursinghomeresearch.com', 'journals.rcni.com', 'papers.ssrn.com',
    'scholarlypublications.universiteitleiden.nl',
}


def host(url):
    if not url:
        return ''
    teile = url.split('/')
    return re.sub(r'^www\.', '', teile[2].lower()) if len(teile) > 2 else ''


def revidiere(rec):
    """Returns (category, reason, verification, commercial) for a citation."""
    u, k = (rec['url'] or ''), rec['category_code']

    # A) corrections to the existing assignment
    if 'bda.uk.com/resource/' in u:
        return 'F', 'BDA Food Fact Sheet, patient information', 'Page content', 0
    if 'nice.org.uk/guidance/ng97/resources/' in u:
        return 'B', 'NICE patient decision aid', 'Page content', 0
    if 'clinicalnutrition.science' in u and 'parenteral-nutrition-geriatrics' in u:
        return 'B', 'ESPEN guideline, but not the one applicable to the item', 'Page content', 0
    if 'espen.org' in u and 'practical' in u.lower() and k == 'A':
        return 'A*', 'ESPEN practical guideline, short version', 'Page content', 0

    # B) resolution of category '?'
    if k == '?':
        h = host(u)
        if h in DOMAINS:
            kat, grund, weg, komm = DOMAINS[h]
            if h in RECLASSIFIED:
                grund += ' [reclassified: scientific publication, irrespective of PubMed indexing]'
            return kat, grund, weg, komm
        return '?', 'not assigned', '', 0

    return k, '', '', 0


def main(quelle, ziel):
    rows = list(csv.DictReader(open(quelle, encoding='utf-8')))
    aus = []
    for r in rows:
        kat, grund, weg, komm = revidiere(r)
        aus.append(dict(citation_id=r['citation_id'], rating_id=r['rating_id'],
                        model=r['model'], url=r['url'],
                        category_old=r['category_code'], category_new=kat,
                        reason=grund, verification=weg, commercial=komm))
    with open(ziel, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(aus[0].keys()))
        w.writeheader()
        w.writerows(aus)

    geaendert = sum(1 for a, r in zip(aus, rows) if a['category_new'] != r['category_code'])
    offen = sum(1 for a in aus if a['category_new'] == '?')
    print('%d citations read, %d categories changed, %d unassigned' % (len(aus), geaendert, offen))
    print('written: %s' % ziel)
    print()
    print('Reference values - a run must reproduce these:')
    print('  citations total               1462')
    print('  categories changed             176   (151 from ?, 15 A->F, 3 A->B, 7 A->A*; 27 of the 151 as D by reclassification)')
    print('  unassigned                       0')
    c = collections.Counter((a['model'], a['category_new']) for a in aus)
    for m in ['Open Evidence', 'GPT-5.5', 'Sonar Reasoning Pro']:
        n = sum(v for (mm, _), v in c.items() if mm == m)
        teile = '  '.join('%s %d' % (k, c[(m, k)]) for k in ['A', 'A*', 'B', 'C', 'D', 'F'] if c[(m, k)])
        print('  %-22s n=%4d   %s' % (m, n, teile))


if __name__ == '__main__':
    q = sys.argv[1] if len(sys.argv) > 1 else os.path.join('..', 'data', 'citations_long_v3.csv')
    z = sys.argv[2] if len(sys.argv) > 2 else os.path.join('..', 'data', 'category_revision.csv')
    main(q, z)
