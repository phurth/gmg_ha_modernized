DOMAIN = "gmg"

# How often to poll the grill, in seconds.
SCAN_INTERVAL_SECONDS = 30

# Per-request UDP timeout and retry count for a single status poll. Kept short
# so an unplugged grill fails a poll quickly instead of blocking the event loop.
STATUS_TIMEOUT = 2
STATUS_RETRIES = 3
