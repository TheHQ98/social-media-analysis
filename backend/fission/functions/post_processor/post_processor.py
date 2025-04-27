"""
get data from redis list,
produce sentiment, sentiment label and keywords from the context,
finally, send to back to redis list named elastic, we only process English context, otherwise drop it

Sentiment value used by VADER, Key word extractor used by YAKE
"""

from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yake
from typing import Dict, Any, List
import requests
from flask import request, current_app
from langdetect import detect, DetectorFactory, LangDetectException

DetectorFactory.seed = 0
analyzer = SentimentIntensityAnalyzer()
kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=5)


def is_legal_context(context: str) -> bool:
    """
    checks if context is english or legal context
    :param context: string
    :return: bool
    """
    context = context.strip()
    if len(context) < 10:
        return False
    try:
        return detect(context) == 'en'
    except LangDetectException as e:
        current_app.logger.error(f"Language detection failed: {e}")
        return False


def produce_sentiment_analysis(context: str) -> (float, str):
    """
    get sentiment value and sentiment label from context
    :param context: string
    :return: float, str
    """
    score = analyzer.polarity_scores(context)
    sentiment = score['compound']
    if sentiment >= 0.05:
        sentiment_label = "positive"
    elif sentiment <= -0.05:
        sentiment_label = "negative"
    else:
        sentiment_label = "neutral"
    return sentiment, sentiment_label


def extract_keywords(context: str) -> List[str]:
    """
    find out the top 5 keywords from context
    :param context: str
    :return: List[str]
    """
    keywords = kw_extractor.extract_keywords(context)
    return [word for word, score in keywords]


def main():
    """
    get data from redis list,
    produce sentiment, sentiment label and keywords from the context,
    finally, send to back to redis list named elastic, we only process English context, otherwise drop it
    """
    payload = request.get_json(force=True)
    records: List[Dict[str, Any]] = payload if isinstance(payload, list) else [payload]

    for record in records:
        # clean the text
        try:
            clean_content = BeautifulSoup(record.get("data", {}).get("content", ""), 'html.parser').get_text()
        except Exception as e:
            current_app.logger.error(f"HTML parser fail: {e}")
            continue

        # only process language of post is english, otherwise drop it
        if not is_legal_context(clean_content):
            current_app.logger.error(f"Found non-english post, dropped: {clean_content}")
            continue

        # produce sentiment value and sentiment label
        sentiment, sentiment_label = produce_sentiment_analysis(clean_content)
        record["sentiment"] = sentiment
        record["sentimentLabel"] = sentiment_label

        # find out top 5 keywords from post context
        record["keywords"] = extract_keywords(clean_content.lower())
        assert all(k == k.lower() for k in record["keywords"]), "Contain upper words"

        # send to redis list, called elastic
        try:
            res = requests.post(
                url="http://router.fission.svc.cluster.local/enqueue/elastic",
                json=record,
                timeout=5
            )
            res.raise_for_status()
        except Exception as e:
            current_app.logger.error(f"Error pushing to queue: {e}")

    return "OK"
