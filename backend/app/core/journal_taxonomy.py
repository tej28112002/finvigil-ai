"""
BRD FR-JRN-02: "Fixed psychology taxonomy; no buy/sell advice." This is the
single source of truth for which tags a journal entry may carry — every
tag a user attaches must come from this list, enforced in
JournalService.add_tags(). Deliberately observational/behavioral labels
only (how the user felt or acted), never a recommendation ("buy", "sell",
"hold") — the taxonomy itself is part of how this app stays a reflection
tool, not an advice engine.
"""

PSYCHOLOGY_TAGS: dict[str, str] = {
    "fear": "Acted out of fear of losing money",
    "greed": "Chased a bigger gain than the setup justified",
    "fomo": "Fear of missing out — entered late chasing a move",
    "revenge_trading": "Traded to win back a recent loss",
    "overconfidence": "Sized up or skipped checks after a winning streak",
    "hesitation": "Delayed or second-guessed a planned entry/exit",
    "impatience": "Exited early or entered before the setup confirmed",
    "discipline": "Followed the plan as written",
    "patience": "Waited for the right setup without forcing a trade",
    "regret": "Reflecting on a decision with hindsight regret",
    "anxiety": "Felt anxious holding or watching the position",
    "boredom": "Traded out of boredom, not a real setup",
}
