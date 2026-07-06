# tests/backend/coordinator/test_result_filters.py
"""Unit tests for deterministic image-search junk filtering (result_filters)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from src.coordinator.tools.result_filters import (
    is_junk_image_url,
    filter_junk_results,
)


@dataclass
class _R:
    """Minimal SearchResult stand-in — only `.url` matters to the filter."""
    url: str
    title: str = ""
    description: str = ""


# The five URLs from the live Gwen incident (2026-07-06). The three icon/art
# ones are junk-by-URL; the two porn ones and the museum one are NOT junk-by-URL
# (the museum artwork is a relevance problem, handled by the bge-m3 layer).
INCIDENT_JUNK = [
    "https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons/hadoop/hadoop-original.svg",
    "https://cdn.jsdelivr.net/npm/lucide-static/icons/a-arrow-up.svg",
]
INCIDENT_NOT_JUNK_BY_URL = [
    "https://www.elexia.ai/trendingentertainment207/bbc-deepthroat/",
    "https://www.eporner.com/hd-porn/OtzcdKvPdEf/Deep-throat-at-a-babershop/",
    "https://artic.edu/artworks/14360",  # keyword collision — relevance layer's job
]


class TestIsJunkImageUrl:
    @pytest.mark.parametrize("url", INCIDENT_JUNK)
    def test_incident_junk_urls_flagged(self, url):
        assert is_junk_image_url(url) is True

    @pytest.mark.parametrize("url", INCIDENT_NOT_JUNK_BY_URL)
    def test_incident_content_urls_not_flagged(self, url):
        assert is_junk_image_url(url) is False

    @pytest.mark.parametrize("url", [
        "https://img.icons8.com/color/48/000000/home.png",
        "https://www.svgrepo.com/show/12345/cat.svg",
        "https://www.flaticon.com/free-icon/dog_123",
        "https://thenounproject.com/icon/tree-999/",
        "https://img.shields.io/badge/build-passing-green",
        "https://www.gravatar.com/avatar/abc123",
        "https://via.placeholder.com/150",
        "https://placehold.co/600x400",
    ])
    def test_whole_host_junk_services(self, url):
        assert is_junk_image_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://unpkg.com/simple-icons@latest/icons/github.svg",
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0/svgs/solid/star.svg",
        "https://raw.githubusercontent.com/simple-icons/simple-icons/main/icons/x.svg",
        "https://gcore.jsdelivr.net/npm/@fortawesome/fontawesome-free/svgs/brands/x.svg",
    ])
    def test_shared_cdn_icon_paths(self, url):
        assert is_junk_image_url(url) is True

    def test_shared_cdn_non_icon_path_kept(self):
        # jsdelivr also serves legit repo assets — a non-icon path must survive.
        url = "https://cdn.jsdelivr.net/gh/someuser/photos@main/beach-sunset.jpg"
        assert is_junk_image_url(url) is False

    @pytest.mark.parametrize("url", [
        "https://example.com/assets/icons/user.png",
        "https://cdn.example.com/img/company-logo.svg",
        "https://foo.org/favicon.ico",
        "https://bar.net/media/thing-icon.svg",
    ])
    def test_host_independent_path_signals(self, url):
        assert is_junk_image_url(url) is True

    def test_plain_svg_dropped(self):
        assert is_junk_image_url("https://site.com/diagram.svg") is True

    @pytest.mark.parametrize("url", [
        "https://photos.com/nature/mountain.jpg",
        "https://cdn.site.com/gallery/portrait.jpeg",
        "https://media.example.com/2024/beach.png",
        "https://example.com/a.webp",
    ])
    def test_real_photos_kept(self, url):
        assert is_junk_image_url(url) is False

    def test_empty_and_garbage_inputs(self):
        assert is_junk_image_url("") is False
        assert is_junk_image_url("not a url") is False
        assert is_junk_image_url("http://") is False

    def test_svg_with_query_string_dropped(self):
        # urlparse .path excludes the query, so ?v=2 doesn't hide the .svg
        assert is_junk_image_url("https://x.com/icon.svg?v=2") is True


class TestFilterJunkResults:
    def test_non_image_category_untouched(self):
        results = [_R(u) for u in INCIDENT_JUNK]
        out = filter_junk_results(results, "general")
        assert out is results  # returned unchanged (same object)

    def test_mixed_incident_set_strips_only_junk(self):
        results = [_R(u) for u in INCIDENT_JUNK + INCIDENT_NOT_JUNK_BY_URL]
        out = filter_junk_results(results, "images")
        kept_urls = [r.url for r in out]
        for junk in INCIDENT_JUNK:
            assert junk not in kept_urls
        for good in INCIDENT_NOT_JUNK_BY_URL:
            assert good in kept_urls
        assert len(out) == len(INCIDENT_NOT_JUNK_BY_URL)

    def test_never_empty_fallback_returns_original(self):
        # A set of PURE junk → filtering would empty it → original returned.
        results = [_R(u) for u in INCIDENT_JUNK]
        out = filter_junk_results(results, "images")
        assert out is results

    def test_never_empty_disabled_can_empty(self):
        results = [_R(u) for u in INCIDENT_JUNK]
        out = filter_junk_results(results, "images", never_empty=False)
        assert out == []

    def test_empty_input(self):
        assert filter_junk_results([], "images") == []
        assert filter_junk_results(None, "images") is None

    def test_result_missing_url_attr_is_kept(self):
        class NoUrl:
            pass
        obj = NoUrl()
        out = filter_junk_results([obj], "images")
        assert out == [obj]
