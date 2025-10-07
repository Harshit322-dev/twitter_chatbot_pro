from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()


def analyze_sentiment(text: str) -> tuple[str, float]:
    scores = _analyzer.polarity_scores(text or "")
    compound = scores.get("compound", 0.0)
    if compound >= 0.05:
        return ("positive", compound)
    elif compound <= -0.05:
        return ("negative", compound)
    return ("neutral", compound)
