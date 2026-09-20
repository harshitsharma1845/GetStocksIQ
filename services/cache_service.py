import time
import logging
from threading import Lock
from collections import defaultdict

logger = logging.getLogger("investiq.cache")

class CacheService:
    """Thread-safe in-memory cache with Time-To-Live (TTL), stale fallback,
    per-key stampede protection, and observability metrics.
    """

    # Configurable TTL Constants (Seconds)
    TTL_MARKET_INDICES = 120      # 120s (2m): Index barometer
    TTL_MARKET_MOVERS = 180       # 180s (3m): Batch market movers snapshots
    TTL_STOCK_DETAILS = 180       # 180s (3m): Individual stock quote & details
    TTL_RECOMMENDATIONS = 600     # 600s (10m): Evaluated top candidate pool
    TTL_AI_ANALYSIS = 600         # 600s (10m): Quantitative 7-pillar model
    TTL_MARKET_NEWS = 600         # 600s (10m): Macro market news feed
    TTL_STOCK_NEWS = 600          # 600s (10m): Company-specific news articles
    TTL_STOCK_META = 86400        # 86400s (24h): Static corporate metadata

    # Internal state
    _cache = {}                   # key -> {"value": val, "created_at": ts, "expires_at": ts}
    _lock = Lock()                # Global lock for cache dict mutations
    _key_locks = defaultdict(Lock) # Per-key locks for stampede protection
    _key_locks_mutex = Lock()     # Lock protecting _key_locks dictionary

    # Observability metrics
    _stats = {
        "hits": 0,
        "misses": 0,
        "stale_hits": 0,
        "sets": 0,
    }

    @classmethod
    def normalize_symbol(cls, symbol):
        """Uniformly formats stock symbols across all services and cache keys."""
        if not symbol or not isinstance(symbol, str):
            return ""
        clean = symbol.strip().upper().rstrip("?").rstrip("&")
        # Standardize index aliases
        if clean in ["NIFTY", "NIFTY50", "NIFTY 50", "^NSEI"]:
            return "^NSEI"
        if clean in ["SENSEX", "BSE", "BSE SENSEX", "^BSESN"]:
            return "^BSESN"
        # Standardize Indian equities
        if "." not in clean and not clean.startswith("^") and len(clean) > 0:
            return f"{clean}.NS"
        return clean

    @classmethod
    def get(cls, key, allow_stale=False):
        """Retrieves a cached value.
        - Returns fresh value if time <= expires_at
        - Returns stale value if time > expires_at AND allow_stale=True
        - Returns None if not found or expired with allow_stale=False
        """
        with cls._lock:
            entry = cls._cache.get(key)
            if not entry:
                cls._stats["misses"] += 1
                logger.debug(f"[CACHE_MISS] key={key}")
                return None

            now = time.time()
            val = entry["value"]
            expires_at = entry["expires_at"]

            if expires_at is None or now <= expires_at:
                cls._stats["hits"] += 1
                logger.debug(f"[CACHE_HIT] key={key}")
                return val

            # Expired entry
            if allow_stale:
                cls._stats["stale_hits"] += 1
                logger.debug(f"[CACHE_STALE] key={key} (expired {now - expires_at:.1f}s ago)")
                return val

            cls._stats["misses"] += 1
            logger.debug(f"[CACHE_EXPIRED] key={key}")
            return None

    @classmethod
    def get_with_meta(cls, key, allow_stale=False):
        """Returns (value, status, created_at) where status is 'FRESH', 'STALE', or 'MISS'."""
        with cls._lock:
            entry = cls._cache.get(key)
            if not entry:
                cls._stats["misses"] += 1
                return None, "MISS", None

            now = time.time()
            val = entry["value"]
            expires_at = entry["expires_at"]
            created_at = entry["created_at"]

            if expires_at is None or now <= expires_at:
                cls._stats["hits"] += 1
                return val, "FRESH", created_at

            if allow_stale:
                cls._stats["stale_hits"] += 1
                return val, "STALE", created_at

            cls._stats["misses"] += 1
            return None, "EXPIRED", created_at

    @classmethod
    def set(cls, key, value, ttl_seconds=60):
        """Stores a value in cache with created timestamp and expiration timestamp."""
        now = time.time()
        expires_at = (now + ttl_seconds) if ttl_seconds else None
        with cls._lock:
            cls._cache[key] = {
                "value": value,
                "created_at": now,
                "expires_at": expires_at,
            }
            cls._stats["sets"] += 1
            logger.debug(f"[CACHE_SET] key={key} ttl={ttl_seconds}s")

    @classmethod
    def get_or_set(cls, key, fetch_fn, ttl_seconds=60, allow_stale=True):
        """Thread-safe read-through cache with per-key stampede protection and stale fallback.
        1. Checks for fresh cache.
        2. If expired or miss, locks on the specific key to prevent duplicate concurrent queries.
        3. Calls fetch_fn(). If successful, saves to cache and returns.
        4. If fetch_fn() raises an exception and allow_stale=True, returns last known stale value.
        5. If no stale value exists, re-raises the exception or returns None.
        """
        # Quick lock-free check for fresh cache
        val = cls.get(key, allow_stale=False)
        if val is not None:
            return val

        # Obtain per-key lock to prevent stampede across simultaneous worker threads
        with cls._key_locks_mutex:
            key_lock = cls._key_locks[key]

        with key_lock:
            # Re-check cache after acquiring per-key lock (in case another thread just populated it)
            val = cls.get(key, allow_stale=False)
            if val is not None:
                return val

            start_t = time.time()
            try:
                logger.debug(f"[EXTERNAL_REQUEST] key={key}")
                fresh_val = fetch_fn()
                duration = time.time() - start_t
                logger.debug(f"[EXTERNAL_REQUEST_DURATION] key={key} duration={duration:.3f}s")

                if fresh_val is not None:
                    cls.set(key, fresh_val, ttl_seconds=ttl_seconds)
                return fresh_val
            except Exception as exc:
                duration = time.time() - start_t
                logger.warning(f"[EXTERNAL_REQUEST_FAILED] key={key} duration={duration:.3f}s error={str(exc)}")
                if allow_stale:
                    stale_val = cls.get(key, allow_stale=True)
                    if stale_val is not None:
                        logger.info(f"[CACHE_STALE_FALLBACK_SERVED] key={key}")
                        return stale_val
                raise exc

    @classmethod
    def delete(cls, key):
        with cls._lock:
            cls._cache.pop(key, None)

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._cache.clear()
            cls._stats = {"hits": 0, "misses": 0, "stale_hits": 0, "sets": 0}

    @classmethod
    def get_stats(cls):
        """Returns diagnostic cache performance metrics."""
        with cls._lock:
            total_reads = cls._stats["hits"] + cls._stats["stale_hits"] + cls._stats["misses"]
            hit_ratio = ((cls._stats["hits"] + cls._stats["stale_hits"]) / total_reads) if total_reads > 0 else 0.0
            return {
                "hits": cls._stats["hits"],
                "misses": cls._stats["misses"],
                "stale_hits": cls._stats["stale_hits"],
                "sets": cls._stats["sets"],
                "total_entries": len(cls._cache),
                "hit_ratio": round(hit_ratio, 4),
            }

