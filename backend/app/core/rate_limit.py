"""
core/rate_limit.py

Rate limiting configuration using slowapi.
Limits are applied per-client IP to prevent abuse.

Rate tiers:
  - COMPUTE: 5/minute  — expensive scoring operations
  - MUTATION: 10/minute — POST/PUT/DELETE that modify state
  - READ: 60/minute    — GET endpoints
  - HEALTH: 120/minute — monitoring endpoints
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter keyed by client IP address
limiter = Limiter(key_func=get_remote_address)

# Named rate strings for use in @limiter.limit() decorators
RATE_COMPUTE = "5/minute"
RATE_MUTATION = "10/minute"
RATE_READ = "60/minute"
RATE_HEALTH = "120/minute"
