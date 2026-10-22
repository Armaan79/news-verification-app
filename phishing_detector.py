from urllib.parse import urlparse
import re
import joblib

model=joblib.load("model/phishing_model.pkl")

SUSPICIOUS_WORDS=[
    "login","verify","update","secure","account","password",
    "signin","confirm","wallet","bank","payment","billing",
    "recover","unlock","credential"
]

SHORTENERS=["bit.ly","tinyurl.com","t.co","goo.gl","is.gd","ow.ly","buff.ly"]

def extract_features(url):
    p=urlparse(url)
    host=p.netloc.lower()
    return [
        len(url),len(host),url.count("."),url.count("-"),
        url.count("/"),url.count("@"),url.count("?"),url.count("="),
        url.count("%"),int(p.scheme!="https"),
        int(bool(re.search(r"\d+\.\d+\.\d+\.\d+",host))),
        int("@" in url),
        int(any(w in url.lower() for w in
            ["login","verify","update","secure","account","password"]))
    ]

def security_check(url):
    p=urlparse(url)
    host=p.hostname or ""
    lower=url.lower()
    reasons=[]
    risk=0

    if p.scheme!="https":
        reasons.append("Does not use HTTPS");risk+=10
    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+",host):
        reasons.append("Uses an IP address instead of a domain");risk+=30
    if "@" in url:
        reasons.append("Contains @ symbol");risk+=30
    if "xn--" in host:
        reasons.append("Uses a punycode domain");risk+=25
    if len(url)>100:
        reasons.append("Unusually long URL");risk+=10
    if len(url)>180:risk+=10
    if url.count("-")>=2:
        reasons.append("Contains multiple hyphens");risk+=10
    if len(host.split("."))>=4:
        reasons.append("Contains many subdomains");risk+=15
    if p.port:
        reasons.append("Uses a non-standard port");risk+=15
    if "%" in url:
        reasons.append("Contains encoded URL characters");risk+=10
    if any(w in lower for w in SUSPICIOUS_WORDS):
        reasons.append("Contains suspicious security-related words");risk+=20
    if host in SHORTENERS:
        reasons.append("Uses a URL shortening service");risk+=15
    if re.search(r"(login|verify|account|secure).*(login|verify|account|secure)",lower):
        reasons.append("Contains repeated security-related terms");risk+=10

    return min(risk,100),reasons

def predict_url(url):
    if not re.match(r"^https?://",url.lower()):
        url="http://"+url

    features=extract_features(url)
    prediction=model.predict([features])[0]
    ml_confidence=model.predict_proba([features])[0].max()*100
    risk,reasons=security_check(url)

    if risk>=70:
        verdict="Phishing"
    elif risk<=15 and prediction==0:
        verdict="Legitimate"
    else:
        verdict="Phishing" if prediction else "Legitimate"

    heuristic= risk if verdict=="Phishing" else 100-risk
    confidence=(ml_confidence*.75)+(heuristic*.25)

    if verdict=="Phishing":
        confidence=max(confidence,70 if risk>=50 else 60)
    else:
        confidence=min(confidence,95)

    return {
        "verdict":verdict,
        "confidence":round(confidence,2),
        "risk":risk,
        "reasons":reasons
    }