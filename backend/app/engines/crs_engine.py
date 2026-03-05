"""
engines/crs_engine.py

DEPRECATED — The blended CRS = QFS*0.60 + FSAS*0.40 approach has been retired.

The new scoring pipeline uses:
    1. QFS percentile rank within category → tier assignment
    2. Shortlist top N per category by QFS
    3. FSAS only for shortlisted funds → refines action (not tier)
    4. fund_recommendation table stores QFS + FSAS separately

This file is kept for reference only. Do not import or use.
See: tier_engine.py (assign_tier_by_percentile) and scoring_service.py for the new pipeline.
"""

# This module is intentionally empty. The CRSEngine class has been removed.
# All references should use the new pipeline in scoring_service.py.
