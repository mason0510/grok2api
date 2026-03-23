"""
Proxy pool with sticky selection and failover rotation.

Supports comma-separated proxy URLs in config. Callers keep using the
current proxy until a retry path explicitly rotates to the next one.
"""

import hashlib
import threading
from typing import Any, Optional

from app.core.logger import logger

# ---- internal state ----
_lock = threading.Lock()
_pools: dict[str, list[str]] = {}  # key -> parsed list
_indexes: dict[str, int] = {}  # key -> current index
_token_indexes: dict[tuple[str, str], int] = {}  # (config_key, token) -> bound index
_raw_cache: dict[str, Any] = {}  # key -> last raw config value signature
_FAILOVER_STATUS_CODES = frozenset({403, 429, 502})


def _normalize_raw_proxy_value(raw: Any) -> Any:
    if raw is None:
        return ""
    if isinstance(raw, (list, tuple)):
        return tuple(str(item).strip() for item in raw if str(item).strip())
    return str(raw).strip()


def _parse_proxies(raw: Any) -> list[str]:
    """Parse proxy config from comma-separated string or string array."""
    normalized = _normalize_raw_proxy_value(raw)
    if not normalized:
        return []
    if isinstance(normalized, tuple):
        return list(normalized)
    return [p.strip() for p in normalized.split(",") if p.strip()]


def _ensure_pool(config_key: str) -> list[str]:
    """Load and cache the proxy list for *config_key*."""
    from app.core.config import config  # avoid circular at module level

    raw = config.get(config_key, "")
    raw_signature = _normalize_raw_proxy_value(raw)
    if raw_signature != _raw_cache.get(config_key):
        proxies = _parse_proxies(raw)
        _pools[config_key] = proxies
        _indexes[config_key] = 0
        for binding_key in list(_token_indexes.keys()):
            if binding_key[0] == config_key:
                del _token_indexes[binding_key]
        _raw_cache[config_key] = raw_signature
        if len(proxies) > 1:
            logger.info(
                f"ProxyPool: {config_key} loaded {len(proxies)} proxies for failover"
            )
    return _pools.get(config_key, [])


def get_current_proxy(config_key: str) -> str:
    """Return the current sticky proxy URL for *config_key*."""
    with _lock:
        pool = _ensure_pool(config_key)
        if not pool:
            return ""
        idx = _indexes.get(config_key, 0) % len(pool)
        _indexes[config_key] = idx
        return pool[idx]


def get_current_proxy_from(*config_keys: str) -> tuple[Optional[str], str]:
    """Return the first configured sticky proxy from *config_keys*."""
    for config_key in config_keys:
        proxy = get_current_proxy(config_key)
        if proxy:
            return config_key, proxy
    return None, ""


def _normalize_token_key(token: Optional[str]) -> str:
    if not token:
        return ""
    token = str(token).strip()
    if token.startswith("sso="):
        token = token[4:]
    return token


async def _get_ordered_token_keys() -> list[str]:
    try:
        from app.services.token.manager import (
            BASIC_POOL_NAME,
            SUPER_POOL_NAME,
            TokenManager,
        )

        manager = await TokenManager.get_instance()
        pool_names: list[str] = []
        for pool_name in (BASIC_POOL_NAME, SUPER_POOL_NAME):
            if pool_name in manager.pools:
                pool_names.append(pool_name)
        for pool_name in manager.pools.keys():
            if pool_name not in pool_names:
                pool_names.append(pool_name)

        tokens: list[str] = []
        seen: set[str] = set()
        for pool_name in pool_names:
            pool = manager.pools.get(pool_name)
            if not pool:
                continue
            for token_info in pool.list():
                token_key = _normalize_token_key(token_info.token)
                if token_key and token_key not in seen:
                    tokens.append(token_key)
                    seen.add(token_key)
        return tokens
    except Exception as exc:
        logger.warning(f"ProxyPool: failed to load token order for binding: {exc}")
        return []


async def get_token_bound_proxy(config_key: str, token: Optional[str]) -> str:
    token_key = _normalize_token_key(token)
    with _lock:
        pool = _ensure_pool(config_key)
        if not pool:
            return ""
        if not token_key:
            idx = _indexes.get(config_key, 0) % len(pool)
            _indexes[config_key] = idx
            return pool[idx]
        if len(pool) == 1:
            _token_indexes[(config_key, token_key)] = 0
            return pool[0]
        bound_key = (config_key, token_key)
        if bound_key in _token_indexes:
            idx = _token_indexes[bound_key] % len(pool)
            return pool[idx]

    ordered_tokens = await _get_ordered_token_keys()
    if token_key in ordered_tokens:
        idx = ordered_tokens.index(token_key) % len(pool)
        binding_source = "token-order"
    else:
        idx = int(hashlib.sha256(token_key.encode("utf-8")).hexdigest(), 16) % len(pool)
        binding_source = "token-hash"

    with _lock:
        _token_indexes[(config_key, token_key)] = idx
        proxy = pool[idx]
    logger.info(
        f"ProxyPool: bind token {token_key[:10]}... to {config_key} proxy {idx + 1}/{len(pool)} via {binding_source}"
    )
    return proxy


async def get_token_bound_proxy_from(
    token: Optional[str], *config_keys: str
) -> tuple[Optional[str], str]:
    for config_key in config_keys:
        proxy = await get_token_bound_proxy(config_key, token)
        if proxy:
            return config_key, proxy
    return None, ""


async def rotate_proxy_for_token(config_key: str, token: Optional[str]) -> str:
    token_key = _normalize_token_key(token)
    if not token_key:
        return rotate_proxy(config_key)
    proxy = await get_token_bound_proxy(config_key, token_key)
    pool_size = 0
    with _lock:
        pool_size = len(_ensure_pool(config_key))
    if pool_size > 1:
        logger.warning(
            f"ProxyPool: token-bound mode active, keep token {token_key[:10]}... on {config_key} fixed proxy"
        )
    return proxy


def rotate_proxy(config_key: str) -> str:
    """Advance *config_key* to the next proxy and return it."""
    with _lock:
        pool = _ensure_pool(config_key)
        if not pool:
            return ""
        if len(pool) == 1:
            return pool[0]
        next_idx = (_indexes.get(config_key, 0) + 1) % len(pool)
        _indexes[config_key] = next_idx
        proxy = pool[next_idx]
        logger.warning(
            f"ProxyPool: rotate {config_key} to index {next_idx + 1}/{len(pool)}"
        )
        return proxy


def should_rotate_proxy(status_code: Optional[int]) -> bool:
    """Return whether *status_code* should trigger proxy failover."""
    return status_code in _FAILOVER_STATUS_CODES


def build_http_proxies(proxy_url: str) -> Optional[dict[str, str]]:
    """Build curl_cffi-style proxies mapping from a single proxy URL."""
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}


__all__ = [
    "build_http_proxies",
    "get_current_proxy",
    "get_current_proxy_from",
    "get_token_bound_proxy",
    "get_token_bound_proxy_from",
    "rotate_proxy",
    "rotate_proxy_for_token",
    "should_rotate_proxy",
]
