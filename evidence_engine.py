"""Evidence engine: checks whether news sources support or contradict a claim."""

import csv
import re
from difflib import SequenceMatcher

# ---------- rules ----------

STOP = set("""
the a an is are was were has have had to of in on for and or with this that
from by will be been its their they it as at into about after before according
says said news report reports new latest claim claims reported but can who how
why you our his her all any may now
""".split())

with open("data/evidence_rules.csv", encoding="utf-8") as f:
    RULES = list(csv.DictReader(f))

COUNTRIES = {r["value"] for r in RULES if r["type"] == "country"}
ALIASES = {r["value"]: r["category"] for r in RULES if r["type"] == "alias"}
SATIRE = ("the onion", "theonion.com")
NUMBER_WORDS = {w: str(i) for i, w in enumerate(
    "one two three four five six seven eight nine ten".split(), 1)}


def rx(pattern):
    """Compile a '|'-separated list of alternatives as whole-word regex."""
    return re.compile(r"\b(?:" + pattern + r")\b")


NEGATION = rx(r"not|never|cannot|\w+n't")
DENIAL = rx(r"false|fake|wrong|busted|debunked|refut\w*|dismiss\w*|contrary to")
QUESTION = re.compile(r"\?")
ATTRIBUTION = rx(
    r"say|says|said|told|claim\w*|report\w*|believ\w*|belief|convinced|think\w*"
    r"|thought|argu(?:e|es|ed)|according to|reject\w*|den(?:y|ies|ied)"
    r"|criticiz\w*|promis\w*|insist\w*|opinion|survey|poll"
)
ATTEMPT = rx(
    r"prov(?:e|es|ing)|convinc(?:e|es|ing)|attempt\w*|tri(?:es|ed)|trying"
    r"|plan|planned|plans|intend|intends|intended"
)
CONTEXT = rx(
    r"earth week|campaign|event|conference|program|theme|project|initiative"
    r"|barycent(?:er|re)|cent(?:er|re) of mass|reference frame"
    r"|relative (?:to|motion)|technically|strictly speaking|in physics"
    r"|new (?:insight|findings)|what would happen if|hypothetical"
    r"|like (?:believing|saying)|as if|just as|metaphor\w*|analogy|akin to"
    r"|rather than|instead of|something else|(?:another|different) object"
    r"|statement|quoted?|remarks?|comments?|reaction|response|controversy"
    r"|controversial|viral|april fools?|april 1|satir(?:e|ical)|parody|jokes?"
    r"|funny|humorous|just kidding|for fun|cent(?:er|re)[sd]? around"
    r"|focus(?:es|ed) on|dedicated to|aims to"
)
FUTURE = rx(
    r"forecast|forecasted|predict|predicts|predicted|projection|projected"
    r"|expected|expect|will|could|may|might|upcoming|planned|planning"
    r"|set to|poised to"
)
GLOBAL_SCOPE = rx(r"worldwide|global|world|international|across the world|around the world")
LIMITED_SCOPE_ACTION = rx(
    r"shutdown|shut down|closed|closing|halted|suspended|suspend|exit|withdraw|withdrawal"
)
RELATION = rx(r"(?:revolves?|rotates?|moves?|travels?|goes|go) around|orbits|circles")
UNITS = rx(
    r"meter|meters|metre|metres|kilometer|kilometers|kilometre|kilometres"
    r"|mile|miles|foot|feet|kg|kilogram|kilograms|gram|grams|degree|degrees"
    r"|celsius|fahrenheit|percent|%|million|billion|trillion"
)
QUANTITY = re.compile(
    r"(\d+(?:\.\d+)?)\s*(meters?|metres?|kilometers?|kilometres?|"
    r"miles?|feet?|foot|kg|kilograms?|grams?|degrees?|celsius|fahrenheit|percent|%)"
)

# Relationships that must agree before a headline can support a claim.
RELATION_GROUPS = [set(g.split()) for g in (
    "tall taller height high higher short shorter meters metres meter metre",
    "visible visibility see seen sight",
    "independent independence freedom liberated liberation",
    "landed landing land arrived arrival",
    "built build constructed construction",
    "died death killed dead",
    "won win victory defeated lost loss",
    "born birth",
    "launched launch released release",
    "opened open closed close closing",
    "acquired acquisition bought buy purchased purchase",
    "announced announcement announces announce",
    "approved approval passed pass policy policies",
    "shutdown shut closed closing halted suspended suspend exit withdraw",
)]

ACTION_CONFLICTS = [(set(a.split()), set(b.split())) for a, b in (
    ("independent independence freedom", "rule ruled ruler ruling"),
    ("won win victory", "lost loss defeated"),
    ("opened open", "closed close closing"),
    ("launched launch released release", "planned plan expected upcoming"),
)]

# ---------- text helpers ----------


def clean(text):
    text = str(text or "").lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"(?<=\d),(?=\d)", "", text)


def tokens(text):
    return re.findall(r"[a-z0-9']+", clean(text))


def stem(word):
    for _ in range(2):
        for suffix in ("ies", "ing", "ed", "es", "s"):
            if word.endswith(suffix) and not word.endswith("ss") and len(word) - len(suffix) >= 3:
                word = word[:-len(suffix)] + ("y" if suffix == "ies" else "")
                break
    return word[:-1] if word.endswith("e") and len(word) > 3 else word


def words(text):
    return {stem(w) for w in tokens(text)}


def entities(text):
    return {
        stem(w) for w in tokens(text)
        if len(w) > 2 and w not in STOP and not NEGATION.fullmatch(w) and not w.isdigit()
    }


def numbers(text):
    """Meaningful numbers; ordinary years (1900-2099) are ignored."""
    return {
        NUMBER_WORDS.get(t, t) for t in tokens(text)
        if t in NUMBER_WORDS or (t.isdigit() and not 1900 <= int(t) <= 2099)
    }


def quantities(text):
    """Numbers used as measurements, e.g. ('5', 'meter')."""
    return {(n, stem(u)) for n, u in QUANTITY.findall(clean(text))}


def units(text):
    return set(UNITS.findall(clean(text)))


def overlap(claim, title):
    ce, te = entities(claim), entities(title)
    cw, tw = words(claim), words(title)
    return len(ce & te) / max(len(ce), 1), len(cw & tw) / max(len(cw), 1)


def phrase_score(claim, title):
    return SequenceMatcher(None, clean(claim), clean(title)).ratio()


# ---------- classification helpers ----------

def reported_statement(title):
    return bool(ATTRIBUTION.search(clean(title)))


def future(title):
    return bool(FUTURE.search(clean(title)))


def satire(title):
    return bool(re.search(
        r"\b(?:satire|satirical|parody|joke|jokes|funny|humorous|onion)\b", clean(title)))


def contextual_negation(title):
    text = clean(title)
    return bool(CONTEXT.search(text)
                or re.search(r"\bnot\b[^.?!]{0,80}\b(?:but|rather|instead)\b", text))


def attribution_only(title):
    text = clean(title)
    return bool(QUESTION.search(text) or ATTEMPT.search(text)
                or re.search(r"\b(?:myth|rumou?r|alleged|opinion|belief|survey|poll)\b", text))


def relation_match(claim, title):
    cw, tw = words(claim), words(title)
    return any(cw & g and tw & g for g in RELATION_GROUPS)


def relation_conflict(claim, title):
    cw, tw = words(claim), words(title)
    return any((cw & a and tw & b) or (cw & b and tw & a) for a, b in ACTION_CONFLICTS)


def scope_mismatch(claim, title):
    return bool(GLOBAL_SCOPE.search(clean(claim))
                and LIMITED_SCOPE_ACTION.search(clean(title))
                and not GLOBAL_SCOPE.search(clean(title)))


def relation(text):
    """(subject, object) of an 'X orbits Y' style statement, else None."""
    text = clean(text)
    m = RELATION.search(text)
    if not m:
        return None

    def side(part):
        return [stem(w) for w in re.findall(r"[a-z0-9]+", part) if w not in STOP and len(w) > 2]

    before, after = side(text[:m.start()]), side(text[m.end():])
    return (before[-1], after[0]) if before and after else None


def denies(claim, title):
    cw = words(claim)
    return any(
        len(cw & words(clause)) >= min(2, len(cw))
        and (NEGATION.search(clause) or DENIAL.search(clause))
        for clause in re.split(r"[.!?:;]|\b(?:but|however|although|while)\b", clean(title))
    )


# ---------- relevance ----------

def relevant(claim, title):
    claim, title = clean(claim), clean(title)

    if not words(claim):
        return False

    # Keep exact checks for specific measurements.
    cq = quantities(claim)
    if cq and not cq <= quantities(title):
        return False

    cu = units(claim)
    if cu and not cu & units(title):
        return False

    if relation_conflict(claim, title):
        return False

    ent, word = overlap(claim, title)
    phrase = phrase_score(claim, title)

    if relation_match(claim, title):
        return ent >= 0.40 and word >= 0.25

    return ((ent >= 0.40 and word >= 0.25)
            or (ent >= 0.35 and phrase >= 0.30)
            or (word >= 0.40 and phrase >= 0.30))


# ---------- evidence classification ----------

def measurement_match(claim, title):
    cq = quantities(claim)
    return bool(cq) and cq <= quantities(title) and bool(entities(claim) & entities(title))


def contradiction(claim, title):
    claim, title = clean(claim), clean(title)

    if future(title) or contextual_negation(title) or attribution_only(title):
        return False
    if scope_mismatch(claim, title):
        return True
    if not relevant(claim, title):
        return False

    claim_neg, title_neg = bool(NEGATION.search(claim)), bool(NEGATION.search(title))

    # A negative claim is contradicted by a direct positive statement.
    if claim_neg:
        return not title_neg

    # Reversed relationship, or explicit denial (only after relevance is established).
    claim_rel, title_rel = relation(claim), relation(title)
    return bool((claim_rel and title_rel and claim_rel == title_rel[::-1])
                or DENIAL.search(title) or denies(claim, title))


def evidence_type(claim, title):
    claim, title = clean(claim), clean(title)

    if (satire(title) or attribution_only(title) or future(title)
            or contextual_negation(title) or not relevant(claim, title)):
        return "neutral"
    if measurement_match(claim, title):
        return "direct_support"
    if contradiction(claim, title):
        return "direct_contradiction"

    claim_rel, title_rel = relation(claim), relation(title)
    if claim_rel and title_rel:
        return "direct_support" if claim_rel == title_rel else "neutral"

    ent, word = overlap(claim, title)
    return "direct_support" if ent >= 0.60 and word >= 0.25 else "neutral"


def stance(claim, title):
    return {"direct_support": "supporting",
            "direct_contradiction": "contradicting"}.get(evidence_type(claim, title), "neutral")


# ---------- source handling ----------

def is_satirical_source(source, link=""):
    source, link = clean(source), clean(link)
    return any(s in source or s in link for s in SATIRE)


def independent_count(sources):
    """Counts distinct stories; very similar syndicated headlines count as one."""
    groups = []
    for r in sources:
        title = clean(r.get("title", ""))
        countries = {ALIASES.get(w, w) for w in re.findall(r"[a-z]+", title)} & COUNTRIES
        if not any(SequenceMatcher(None, title, other).ratio()
                   >= (0.30 if countries & old else 0.60) for old, other in groups):
            groups.append((countries, title))
    return len(groups)


# ---------- final evidence analysis ----------

def analyze_evidence(results, claim="", ml_prediction=None, ml_confidence=None):
    buckets = {"supporting": [], "contradicting": [], "neutral": []}
    seen = set()

    for r in results or []:
        source = r.get("source", "").strip().lower()
        if not source or source in seen:
            continue
        if is_satirical_source(source, r.get("link", "")):
            buckets["neutral"].append(r)
            continue
        seen.add(source)
        buckets[stance(claim, r.get("title", ""))].append(r)

    sup, con, other = buckets["supporting"], buckets["contradicting"], buckets["neutral"]
    n_sup, n_con = len(sup), len(con)

    def credible(items):
        return sum(r.get("source_score", 1) >= 3 for r in items)

    cred_sup, cred_con = credible(sup), credible(con)
    ind_sup, ind_con = independent_count(sup), independent_count(con)

    def build(verdict, strength, explanation):
        return {
            "verdict": verdict,
            "evidence_strength": strength,
            "supporting_sources": sup,
            "contradicting_sources": con,
            "other_sources": other,
            "credible_sources": cred_sup + cred_con,
            "independent_sources": max(ind_sup, ind_con),
            "explanation": explanation,
        }

    if not results:
        return build("Unable to Verify", "Low", "No relevant news reports were found.")

    if ind_con >= 2 and not n_sup:
        return build("Likely Misinformation", "High" if cred_con >= 2 else "Medium",
                     "Multiple independent reports contradict the claim.")

    if ind_sup >= 2 and not n_con:
        return build("Likely Reliable", "High" if cred_sup >= 2 else "Medium",
                     "Multiple independent reports support the claim.")

    if n_sup and n_con:
        verdict = ("Possibly Misinformation" if n_con > n_sup
                   else "Possibly Reliable" if n_sup > n_con
                   else "Conflicting Evidence")
        return build(verdict, "High" if cred_sup + cred_con >= 2 else "Medium",
                     "Both supporting and contradicting reports were found.")

    if n_con:
        return build("Possibly Misinformation", "Medium" if cred_con else "Low",
                     "A relevant report contradicts the claim.")

    if n_sup:
        return build("Possibly Reliable", "Medium" if cred_sup else "Low",
                     "A relevant report supports the claim.")

    if ml_confidence is not None and ml_confidence >= 60:
        return build("Probably Reliable" if ml_prediction == 1 else "Probably Misinformation",
                     "Medium",
                     "The ML model shows moderate confidence, but web evidence is limited.")

    return build("Unable to Verify", "Low",
                 "Not enough relevant and reliable evidence was found.")