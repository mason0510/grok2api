"""
Retry helpers for token switching.
"""

import random
from typing import Optional, Set

from app.core.config import get_config
from app.core.exceptions import UpstreamException
from app.services.grok.services.model import ModelService
from app.services.reverse.utils.retry import extract_retry_after


async def pick_token(
    token_mgr,
    model_id: str,
    tried: Set[str],
    preferred: Optional[str] = None,
    prefer_tags: Optional[Set[str]] = None,
) -> Optional[str]:
    if preferred and preferred not in tried:
        return preferred

    token = None
    for pool_name in ModelService.pool_candidates_for_model(model_id):
        token = token_mgr.get_token(pool_name, exclude=tried, prefer_tags=prefer_tags)
        if token:
            break

    if not token:
        result = await token_mgr.refresh_cooling_tokens(force=True)
        if result.get("recovered", 0) > 0:
            for pool_name in ModelService.pool_candidates_for_model(model_id):
                token = token_mgr.get_token(
                    pool_name,
                    exclude=tried,
                    prefer_tags=prefer_tags,
                )
                if token:
                    break

    return token


def rate_limited(error: Exception) -> bool:
    if not isinstance(error, UpstreamException):
        return False
    status = error.details.get("status") if error.details else None
    code = error.details.get("error_code") if error.details else None
    return status == 429 or code == "rate_limit_exceeded"


def rate_limit_backoff_seconds(error: Exception) -> float:
    """短退避：遇到瞬时 429 时先等一下，再切下一个 token。"""
    retry_after = extract_retry_after(error)
    if retry_after is not None and retry_after > 0:
        return min(max(float(retry_after), 1.0), 15.0)

    base = float(get_config("retry.retry_backoff_base") or 0.5)
    lower = max(1.0, base * 2)
    upper = max(lower, min(5.0, base * 8))
    return random.uniform(lower, upper)


def transient_upstream(error: Exception) -> bool:
    """Whether error is likely transient and safe to retry with another token."""
    if not isinstance(error, UpstreamException):
        return False
    details = error.details or {}
    status = details.get("status")
    err = str(details.get("error") or error).lower()
    transient_status = {408, 500, 502, 503, 504}
    if status in transient_status:
        return True
    timeout_markers = (
        "timed out",
        "timeout",
        "connection reset",
        "temporarily unavailable",
        "http2",
    )
    return any(marker in err for marker in timeout_markers)


__all__ = ["pick_token", "rate_limited", "rate_limit_backoff_seconds", "transient_upstream"]
