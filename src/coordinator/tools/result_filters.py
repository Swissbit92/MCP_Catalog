# src/coordinator/tools/result_filters.py
"""Deterministic junk-result filtering for image search — ADR-009 W-followup.

Aggregated image search (SearXNG over Bing/Google/DuckDuckGo image engines)
surfaces icon-CDN SVGs, placeholder/favicon services, and badge hosts on any
keyword collision — a query word that happens to match an icon filename or a
package name. These are never what a companion user means by "find an image",
yet today they flow straight into the LLM synthesis AND the verified 🔍 Sources
block (e.g. `cdn.jsdelivr.net/.../devicon/hadoop-original.svg`,
`lucide-static/icons/a-arrow-up.svg`).

This module strips that junk deterministically BEFORE results reach synthesis or
citations.

Design — deterministic + always-on (no feature flag):
  * The patterns are hard-coded junk, unit-tested to certainty. A flag here would
    be flag-debt with no soak hypothesis (nothing a soak tells you a unit test
    doesn't), on a single-operator self-hosted system.
  * Guarded by a never-empty fallback: if filtering would remove EVERY result,
    the original set is returned unchanged — a niche query whose only hits are
    icons/diagrams still yields something rather than an empty answer.
  * Scoped to the ``images`` category only. Web/news/video results are left
    untouched (an icon-CDN URL is not junk for a general web search).

The probabilistic bge-m3 relevance floor is a SEPARATE, flag-gated layer
(``SearchRelevanceService.filter_relevant`` wired in ``executor_bindings``) for
keyword-collision false positives a static denylist can't catch — e.g. a museum
artwork whose title merely contains the query word.
"""

from __future__ import annotations

from typing import Any, List
from urllib.parse import urlparse

# Hosts that are EXCLUSIVELY icon / placeholder / favicon / badge services.
# Matched by hostname suffix, so subdomains (img.icons8.com) are covered.
_JUNK_HOST_SUFFIXES = (
    "svgrepo.com",
    "flaticon.com",
    "icons8.com",
    "thenounproject.com",
    "iconscout.com",
    "simpleicons.org",
    "shields.io",          # img.shields.io badges
    "badgen.net",
    "gravatar.com",        # placeholder avatars
    "placeholder.com",     # via.placeholder.com
    "placehold.co",
    "placekitten.com",
    "dummyimage.com",
    "lorempixel.com",
    "openclipart.org",
    "favicon.im",
    "faviconextractor.com",
)

# Shared CDNs / repos that ALSO serve legitimate photos & screenshots — never
# block the whole host, only these icon/logo package paths (path substring).
_JUNK_HOST_PATHS = {
    "jsdelivr.net": (          # matches gcore/fastly/testingcf.jsdelivr.net aliases too
        "/npm/devicon", "/gh/devicons", "/npm/simple-icons", "/npm/lucide",
        "/npm/@fortawesome", "/npm/font-awesome", "/npm/heroicons",
        "/npm/bootstrap-icons", "/npm/@mdi/", "/npm/flag-icons",
        "/npm/@iconify", "/npm/@tabler/icons",
    ),
    "unpkg.com": (
        "/devicon", "/simple-icons", "/lucide", "/@fortawesome",
        "/font-awesome", "/heroicons", "/bootstrap-icons", "/@mdi/",
        "/@iconify", "/@tabler/icons",
    ),
    "cdnjs.cloudflare.com": (
        "/ajax/libs/devicon", "/ajax/libs/font-awesome",
        "/ajax/libs/simple-icons", "/ajax/libs/ionicons",
    ),
    "raw.githubusercontent.com": (
        "/devicons/", "/simple-icons/", "/lucide-icons/",
        "/tabler/tabler-icons", "/fortawesome/",
    ),
}

# Host-independent path signals: any image URL whose path contains one of these
# is disproportionately an icon/logo/badge/favicon rather than a photo.
_JUNK_PATH_SUBSTRINGS = (
    "/icons/", "/icon/", "/svg-icons", "flag-icons",
    "/badge/", "/badges/", "-icon.svg", "-logo.svg", "/favicon",
)


def _url_parts(url: str) -> tuple[str, str]:
    """Return (lowercased hostname, lowercased path) for a URL. Empty on parse
    failure — a URL we can't parse is treated as non-junk (fail-open)."""
    try:
        parsed = urlparse(url)
    except (ValueError, TypeError):
        return "", ""
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    return host, path


def is_junk_image_url(url: str) -> bool:
    """True if `url` looks like icon/placeholder/badge/favicon junk that a
    "find me an image" query never wants. Deterministic; no network."""
    if not url:
        return False
    host, path = _url_parts(url)
    if not host:
        return False

    # 1) Whole-host icon/placeholder services.
    if any(host == h or host.endswith("." + h) for h in _JUNK_HOST_SUFFIXES):
        return True

    # 2) Shared-CDN icon package paths (host suffix + path substring).
    for host_suffix, path_needles in _JUNK_HOST_PATHS.items():
        if host == host_suffix or host.endswith("." + host_suffix):
            if any(needle in path for needle in path_needles):
                return True

    # 3) Host-independent icon/badge/favicon path signals.
    if any(sub in path for sub in _JUNK_PATH_SUBSTRINGS):
        return True

    # 4) SVG is a vector format — icons/logos/glyphs, essentially never photos.
    #    Strip query/fragment already handled by urlparse .path.
    if path.endswith(".svg"):
        return True

    return False


def filter_junk_results(
    results: List[Any], category: str, *, never_empty: bool = True
) -> List[Any]:
    """Drop deterministic junk from IMAGE search results.

    Args:
        results: list of SearchResult-like objects (need a `.url` attribute).
        category: the search category; filtering applies only to "images".
        never_empty: if True and filtering would remove every result, return the
            ORIGINAL list unchanged (graceful degradation — better a junky image
            than no answer for a niche query).

    Returns the filtered list (a new list) — or `results` unchanged for non-image
    categories, a falsy input, or the never-empty fallback.
    """
    if category != "images" or not results:
        return results
    kept = [r for r in results if not is_junk_image_url(getattr(r, "url", "") or "")]
    if never_empty and not kept:
        return results
    return kept
