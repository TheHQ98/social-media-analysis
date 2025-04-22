from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import yake

# original_context = ("<p>Elon Musk's baby mama drama is good gossip. But I wrote about it because it's something more: a"
#                     "symptom of how MAGA social media's masculinity obsession is getting downright weird. </p><p>This "
#                     "stuff"
#                     "is gross. It's also causing serious harm to audiences. </p><p><a "
#                     "href=\"https://www.salon.com/2025/04/21/elon-musks-baby-mama-drama-matters/\" rel=\"nofollow "
#                     "noopener"
#                     "noreferrer\" target=\"_blank\"><span class=\"invisible\">https://www.</span><span "
#                     "class=\"ellipsis\">salon.com/2025/04/21/elon-musk</span><span "
#                     "class=\"invisible\">s-baby-mama-drama-matters/</span></a></p>")

original_context  =       "<p>How astronomers compare telescopes <a href=\"https://phys.org/news/2025-04-astronomers-telescopes.html\" rel=\"nofollow noopener noreferrer\" translate=\"no\" target=\"_blank\"><span class=\"invisible\">https://</span><span class=\"ellipsis\">phys.org/news/2025-04-astronom</span><span class=\"invisible\">ers-telescopes.html</span></a> <a href=\"https://mastodon.social/tags/science\" class=\"mention hashtag\" rel=\"nofollow noopener noreferrer\" target=\"_blank\">#<span>science</span></a></p>"

soup = BeautifulSoup(original_context, 'html.parser')
clean_text = soup.get_text()

analyzer = SentimentIntensityAnalyzer()
score = analyzer.polarity_scores(clean_text)
compound = score['compound']

if compound >= 0.05:
    sentiment_label = "positive"
elif compound <= -0.05:
    sentiment_label = "negative"
else:
    sentiment_label = "neutral"
print(clean_text)
print(f"Sentiment: {compound} | {sentiment_label}")

kw_extractor = yake.KeywordExtractor(lan="en", n=1, top=5)
keywords = kw_extractor.extract_keywords(clean_text)
keywordsList = [word for word, score in keywords]
print(f"Keywords: {keywordsList}")  # 关键词的重要性得分（越小越重要！）
