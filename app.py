from flask import Flask,render_template,request,jsonify
import joblib
import os
from news_search import search_news
from evidence_engine import analyze_evidence
from phishing_detector import predict_url

app=Flask(__name__)
BASE_DIR=os.path.dirname(os.path.abspath(__file__))

model=joblib.load(os.path.join(BASE_DIR,"model","fake_news_model.pkl"))
vectorizer=joblib.load(os.path.join(BASE_DIR,"model","vectorizer.pkl"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/analyze",methods=["POST"])
def analyze():
    data=request.get_json()
    text=data.get("text","").strip()

    if not text:
        return jsonify({
            "result":"No Content",
            "message":"Please enter a news article or claim."
        })

    text_vector=vectorizer.transform([text])
    prediction=model.predict(text_vector)[0]
    probabilities=model.predict_proba(text_vector)[0]
    confidence=round(max(probabilities)*100,2)

    news_results=search_news(text,max_results=10)
    evidence=analyze_evidence(
        news_results,claim=text,
        ml_prediction=prediction,
        ml_confidence=confidence
    )

    return jsonify({
        "result":evidence["verdict"],
        "message":evidence["explanation"],
        "confidence":confidence,
        "evidence_strength":evidence["evidence_strength"],
        "supporting_sources":evidence["supporting_sources"],
        "contradicting_sources":evidence["contradicting_sources"],
        "other_sources":evidence["other_sources"],
        "credible_sources":evidence["credible_sources"],
        "independent_sources":evidence["independent_sources"],
        "sources":news_results
    })

@app.route("/check-url",methods=["POST"])
def check_url():
    data=request.get_json()
    url=data.get("url","").strip()

    if not url:
        return jsonify({"result":"No URL","message":"Please enter a URL."})

    result=predict_url(url)

    return jsonify({
        "result":result["verdict"],
        "confidence":result["confidence"],
        "risk":result["risk"],
        "reasons":result["reasons"]
    })

if __name__=="__main__":
    app.run(debug=True)