import feedparser
from datetime import datetime
import re

from services.cache_service import CacheService

class NewsService:
    """Fetches real financial news feeds, deduplicates, caches, and scores sentiment and impact."""

    POSITIVE_WORDS = {
        "surge", "jump", "rally", "gain", "profit", "growth", "bullish", "record",
        "beat", "boost", "upgrade", "outperform", "dividend", "expansion", "order",
        "contract", "soar", "positive", "high", "strong", "win", "acquisition"
    }

    NEGATIVE_WORDS = {
        "drop", "fall", "decline", "slump", "loss", "plunge", "bearish", "miss",
        "cut", "downgrade", "probe", "fraud", "penalty", "default", "crisis",
        "weak", "warn", "crash", "negative", "low", "risk", "debt", "selloff"
    }

    @classmethod
    def get_stock_news(cls, symbol):
        clean_sym = CacheService.normalize_symbol(symbol).replace(".NS", "").replace(".BO", "").strip()
        if not clean_sym:
            return []

        cache_key = f"stock_news_{clean_sym}"

        def _fetch():
            articles = []
            seen_titles = set()
            query_url = (
                f"https://news.google.com/rss/search?"
                f"q={clean_sym}+share+price+OR+{clean_sym}+stock+NSE+India"
                f"&hl=en-IN&gl=IN&ceid=IN:en"
            )
            feed = feedparser.parse(query_url)
            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                if not title or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

                link = entry.get("link", "#")
                pub_date = entry.get("published", "Recently")
                source = entry.get("source", {}).get("title") if isinstance(entry.get("source"), dict) else "Market News"
                if not source:
                    source = "Financial Express" if "financialexpress" in link else "Economic Times"

                sentiment, score, impact = cls._analyze_sentiment(title)

                articles.append({
                    "title": title,
                    "url": link,
                    "published": pub_date,
                    "source": source,
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "impact": impact
                })
            return articles

        try:
            return CacheService.get_or_set(cache_key, _fetch, ttl_seconds=CacheService.TTL_STOCK_NEWS, allow_stale=True) or []
        except Exception as e:
            print(f"News fetch error for {symbol}:", e)
            stale = CacheService.get(cache_key, allow_stale=True)
            return stale if stale is not None else []

    @classmethod
    def get_market_news(cls):
        cache_key = "market_news_headlines"

        def _fetch():
            articles = []
            seen_titles = set()
            query_url = (
                "https://news.google.com/rss/search?"
                "q=Indian+stock+market+NIFTY+SENSEX+NSE"
                "&hl=en-IN&gl=IN&ceid=IN:en"
            )
            feed = feedparser.parse(query_url)
            for entry in feed.entries[:6]:
                title = entry.get("title", "").strip()
                if not title or title.lower() in seen_titles:
                    continue
                seen_titles.add(title.lower())

                link = entry.get("link", "#")
                pub_date = entry.get("published", "Recently")
                source = entry.get("source", {}).get("title") if isinstance(entry.get("source"), dict) else "Market News"

                sentiment, score, impact = cls._analyze_sentiment(title)

                articles.append({
                    "title": title,
                    "link": link,
                    "published": pub_date,
                    "source": source or "Market Wire",
                    "sentiment": sentiment,
                    "sentiment_score": score,
                    "impact": impact
                })
            return articles

        try:
            return CacheService.get_or_set(cache_key, _fetch, ttl_seconds=CacheService.TTL_MARKET_NEWS, allow_stale=True) or []
        except Exception as e:
            print("Market news fetch error:", e)
            stale = CacheService.get(cache_key, allow_stale=True)
            return stale if stale is not None else []

    @classmethod
    def _analyze_sentiment(cls, text):
        words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        pos_count = len(words.intersection(cls.POSITIVE_WORDS))
        neg_count = len(words.intersection(cls.NEGATIVE_WORDS))

        if pos_count > neg_count:
            sentiment = "Positive"
            score = min(90, 55 + (pos_count * 15))
            impact = "High" if pos_count >= 2 else "Medium"
        elif neg_count > pos_count:
            sentiment = "Negative"
            score = max(15, 45 - (neg_count * 15))
            impact = "High" if neg_count >= 2 else "Medium"
        else:
            sentiment = "Neutral"
            score = 50
            impact = "Low"

        return sentiment, score, impact

    @classmethod
    def get_sentiment_score(cls, articles):
        if not articles:
            return 50 # Neutral default
        scores = [a.get("sentiment_score", 50) for a in articles]
        return int(round(sum(scores) / len(scores)))
