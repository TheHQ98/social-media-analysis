from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yake
from typing import Dict, Any, List
import requests
from flask import request, current_app

analyzer = SentimentIntensityAnalyzer()


def main():
    """
    get data from redis list, and send to back to redis list named elastic
    """
    payload = request.get_json(force=True)
    records: List[Dict[str, Any]] = payload if isinstance(payload, list) else [payload]

    for record in records:
        # only process language of post is english, otherwise drop it
        if record.get("data", {}).get("language", "") != "en":
            current_app.logger.error(f"Found non-english post, dropped: {record.get('data', {}).get('language')}")
            continue

        content = record.get("data", {}).get("content", "")
        soup = BeautifulSoup(content, 'html.parser')
        clean_content = soup.get_text()

        score = analyzer.polarity_scores(clean_content)
        sentiment = score['compound']

        if sentiment >= 0.05:
            sentiment_label = "positive"
        elif sentiment <= -0.05:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"
        current_app.logger.info(f"Sentiment: {sentiment} | {sentiment_label}")

        record["sentiment"] = sentiment

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
