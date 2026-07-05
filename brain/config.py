"""
Goldfront OS — encoded business rules (single source of truth).

These are the thresholds and facts from the master spec (§9). Everything in the
Brain reads from here so a rule change happens in ONE place and propagates.

Do not hardcode any of these numbers elsewhere.
"""

# --- Deal thresholds -------------------------------------------------------
MARGIN_FLOOR = 0.25          # minimum margin vs. ARV to consider at all
MARGIN_PREFERRED = 0.30      # margin at/above this is a clean GO on margin
DSCR_FLOOR = 1.00            # minimum DSCR
DSCR_PREFERRED = 1.25        # DSCR at/above this is a clean GO on coverage

# --- Capital / lending facts ----------------------------------------------
JOE_CAPITAL_RATE = 0.10      # + 1 point
GOLDFRONT_LEND_RATE_LOW = 0.12
GOLDFRONT_LEND_RATE_HIGH = 0.14
PREFERRED_DSCR_LENDER = "CB3"

# --- Markets ---------------------------------------------------------------
CORE_MARKETS = ("Cleveland", "Akron", "Canton")

# --- The flywheel: six touches on one relationship ------------------------
FLYWHEEL_TOUCHES = (
    "hard_money",
    "construction",
    "title",
    "insurance",
    "dscr_refi",
    "property_management",
)

# --- Memory ----------------------------------------------------------------
DECISION_HALFLIFE_DAYS = 180  # recent decisions outweigh old ones (tunable)
