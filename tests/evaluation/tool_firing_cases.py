# tests/evaluation/tool_firing_cases.py
"""Golden query set for the ADR-008 tool-brain firing eval.

Separated from the runner so the case set can be linted, counted, and
schema-checked headless (no Ollama), and so editing cases never touches
runner logic.

Each case declares what SHOULD happen, in terms of the observable
``ResponseMetadata.source_type`` the live stack returns:

    tool_brain          native tool fired AND a search actually ran
    brave_mcp           fell through to the legacy deterministic force-search floor
    llm                 no tool at all — answered directly
    groundedness_abstain  ADR-007 gate replaced an ungrounded draft
    wallet_*            deterministic wallet flow

``expect`` is the set of source_types that count as CORRECT for that case.
Several buckets deliberately accept more than one: for a web-intent turn we
care that the answer was *grounded in a search*, and both the native path
(tool_brain) and the deterministic floor (brave_mcp) achieve that. The
distinction between them is reported separately as the NATIVE-FIRE RATE,
which is the number that actually says whether the tool brain is earning
its keep versus the legacy floor carrying it.
"""

from __future__ import annotations

# --- buckets -----------------------------------------------------------------

WEB_EXPLICIT = "web_explicit"
WEB_COLLOQUIAL = "web_colloquial"
IMAGE_FIND = "image_find"
VIDEO_FIND = "video_find"
CHITCHAT = "chitchat"
WALLET = "wallet"

BUCKETS = [WEB_EXPLICIT, WEB_COLLOQUIAL, IMAGE_FIND, VIDEO_FIND, CHITCHAT, WALLET]

# source_type values that mean "this answer was grounded in a live search"
GROUNDED = {"tool_brain", "brave_mcp"}
# source_type values that mean "a native tool call fired and executed"
NATIVE = {"tool_brain"}

# --- the golden set ----------------------------------------------------------
#
# persona: eeva has web + wallet; gwen has the image/video subset.
# Keep queries evergreen — a case that depends on a current event will rot.

GOLDEN_CASES: list[dict] = [
    # -- explicit web intent: unambiguous search commands. The router's
    #    EXPLICIT_SEARCH_COMMANDS fast-path should catch these even if the
    #    model stays silent, so anything but a grounded answer is a real miss.
    {"id": "we1", "bucket": WEB_EXPLICIT, "persona": "nephilim_eeva",
     "query": "search the web for the current population of Zurich",
     "expect": GROUNDED},
    {"id": "we2", "bucket": WEB_EXPLICIT, "persona": "nephilim_eeva",
     "query": "look up who won the most recent Formula 1 world championship",
     "expect": GROUNDED},
    {"id": "we3", "bucket": WEB_EXPLICIT, "persona": "nephilim_eeva",
     "query": "google the current price of bitcoin",
     "expect": GROUNDED},
    {"id": "we4", "bucket": WEB_EXPLICIT, "persona": "nephilim_eeva",
     "query": "can you search online for recent news about the Swiss National Bank",
     "expect": GROUNDED},
    {"id": "we5", "bucket": WEB_EXPLICIT, "persona": "nephilim_eeva",
     "query": "find me information about the Gotthard Base Tunnel",
     "expect": GROUNDED},

    # -- colloquial web intent: no search verb. This is the bucket TB0 found
    #    native calling misses ~40% of, and the reason the deterministic floor
    #    exists. Expect grounded; watch how much of it is floor vs native.
    {"id": "wc1", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "what's going on with the European Central Bank lately?",
     "expect": GROUNDED},
    {"id": "wc2", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "who is the current chancellor of Germany?",
     "expect": GROUNDED},
    {"id": "wc3", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "how much does a Tesla Model 3 cost these days?",
     "expect": GROUNDED},
    {"id": "wc4", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "any idea what the weather is like in Geneva right now?",
     "expect": GROUNDED},
    {"id": "wc5", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "is the Zurich airport busy at the moment?",
     "expect": GROUNDED},
    {"id": "wc6", "bucket": WEB_COLLOQUIAL, "persona": "nephilim_eeva",
     "query": "tell me about the latest Mistral AI model release",
     "expect": GROUNDED},

    # -- image find: the _MEDIA_SEARCH verb+noun regex should route these, and
    #    TB5 narrows the offered surface to the single image tool. A miss here
    #    is direct evidence FOR the ROADMAP item-45 media-aware floor.
    {"id": "im1", "bucket": IMAGE_FIND, "persona": "gwen",
     "query": "show me pictures of the Matterhorn",
     "expect": GROUNDED, "expect_tool": "image_search"},
    {"id": "im2", "bucket": IMAGE_FIND, "persona": "gwen",
     "query": "find me images of vintage motorcycles",
     "expect": GROUNDED, "expect_tool": "image_search"},
    {"id": "im3", "bucket": IMAGE_FIND, "persona": "gwen",
     "query": "can you show me some photos of Kyoto in autumn",
     "expect": GROUNDED, "expect_tool": "image_search"},
    {"id": "im4", "bucket": IMAGE_FIND, "persona": "gwen",
     "query": "get me a picture of a snow leopard",
     "expect": GROUNDED, "expect_tool": "image_search"},

    # -- video find: the specific case TB5 called out as choice-paralysis-prone
    #    (video_search missed among four tools). This bucket is the primary
    #    decider for item 45.
    {"id": "vi1", "bucket": VIDEO_FIND, "persona": "gwen",
     "query": "show me a video of how sourdough starter is made",
     "expect": GROUNDED, "expect_tool": "video_search"},
    {"id": "vi2", "bucket": VIDEO_FIND, "persona": "gwen",
     "query": "find me videos about restoring old watches",
     "expect": GROUNDED, "expect_tool": "video_search"},
    {"id": "vi3", "bucket": VIDEO_FIND, "persona": "gwen",
     "query": "can you find a clip of the northern lights",
     "expect": GROUNDED, "expect_tool": "video_search"},
    {"id": "vi4", "bucket": VIDEO_FIND, "persona": "gwen",
     "query": "show me a video tour of the Louvre",
     "expect": GROUNDED, "expect_tool": "video_search"},

    # -- chitchat: MUST NOT fire a tool. A tool call here is a false positive —
    #    the failure mode that made the pre-TB5 build unusable (unsolicited
    #    "let me check your wallet"). Roleplay phrasings that superficially
    #    resemble a search ("come find me") are deliberately included.
    {"id": "cc1", "bucket": CHITCHAT, "persona": "nephilim_eeva",
     "query": "how are you feeling today?",
     "expect": {"llm"}},
    {"id": "cc2", "bucket": CHITCHAT, "persona": "nephilim_eeva",
     "query": "I had a rough day, just want to talk",
     "expect": {"llm"}},
    {"id": "cc3", "bucket": CHITCHAT, "persona": "gwen",
     "query": "come find me when you're ready",
     "expect": {"llm"}},
    {"id": "cc4", "bucket": CHITCHAT, "persona": "gwen",
     "query": "show me what you're really thinking",
     "expect": {"llm"}},
    {"id": "cc5", "bucket": CHITCHAT, "persona": "nephilim_eeva",
     "query": "what do you think makes a person trustworthy?",
     "expect": {"llm"}},
    {"id": "cc6", "bucket": CHITCHAT, "persona": "nephilim_eeva",
     "query": "tell me a short story about a lighthouse keeper",
     "expect": {"llm"}},
    {"id": "cc7", "bucket": CHITCHAT, "persona": "nephilim_eeva",
     "query": "who are you and what do you do?",
     "expect": {"llm"}},

    # -- wallet: must stay on the deterministic flow, NEVER the native surface.
    #    TB5 scoped _try_tool_brain to NEEDS_WEB_SEARCH precisely so wallet
    #    never enters the model-decided path. tool_brain here is a safety fail.
    {"id": "wa1", "bucket": WALLET, "persona": "nephilim_eeva",
     "query": "what's my wallet balance?",
     "expect": {"wallet_mcp", "wallet_flow", "llm"}},
    {"id": "wa2", "bucket": WALLET, "persona": "nephilim_eeva",
     "query": "show me my sol balance",
     "expect": {"wallet_mcp", "wallet_flow", "llm"}},
    {"id": "wa3", "bucket": WALLET, "persona": "nephilim_eeva",
     "query": "do I have any tokens in my wallet",
     "expect": {"wallet_mcp", "wallet_flow", "llm"}},
]


def cases_for_bucket(bucket: str) -> list[dict]:
    """All golden cases in one bucket."""
    return [c for c in GOLDEN_CASES if c["bucket"] == bucket]
