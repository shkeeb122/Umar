============================================================

📁 FILE: smart_utils.py

🎯 ROLE: ADVANCED UTILITY + TIME + RETRY + METRICS ENGINE

🔗 USED BY: main.py, smart_hands.py

📌 VERSION: 8.0.0

PURPOSE:

Reliable automation utilities.

Timing, retries, waits, metrics, cancellation,

text/URL helpers, task tracking and safe result handling.

SAFETY:

No CAPTCHA bypass

No OTP/security bypass

No anti-detection/stealth logic

No fake task completion

No infinite retry loops

============================================================

import json
import random
import re
import time
import threading
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

class SmartUtils:
"""
🧠 SmartUtils v8.0

Central utility engine for:
  - timing
  - action tracking
  - bounded retries
  - exponential backoff
  - cancellation
  - task timers
  - safe waits
  - text normalization
  - URL utilities
  - metrics
  - structured results
  - runtime information
"""

VERSION = "8.0.0"

# ------------------------------------------------------------
# DEFAULTS
# ------------------------------------------------------------

DEFAULT_HUMAN_DELAY_MIN = 0.20
DEFAULT_HUMAN_DELAY_MAX = 0.80

DEFAULT_TYPING_SPEED_MIN = 35
DEFAULT_TYPING_SPEED_MAX = 65

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 0.50
DEFAULT_BACKOFF_MAX = 8.0

DEFAULT_WAIT_INTERVAL = 0.25
DEFAULT_MAX_WAIT = 30.0

MAX_TEXT_LENGTH = 50000
MAX_HISTORY = 1000

# ------------------------------------------------------------
# INIT
# ------------------------------------------------------------

def __init__(self):
    # Task timing
    self.task_start_time = None
    self.task_end_time = None
    self.total_time_spent = 0.0

    # Action counters
    self.actions = 0
    self.successful_actions = 0
    self.failed_actions = 0
    self.retry_count = 0

    # Task counters
    self.tasks_started = 0
    self.tasks_completed = 0
    self.tasks_failed = 0
    self.tasks_skipped = 0

    # Runtime
    self.runtime_start_time = time.monotonic()
    self.last_action_time = None

    # Action history
    self.action_history = []

    # Error history
    self.error_history = []

    # Thread safety
    self._lock = threading.RLock()

    # Stop/cancel event
    self._stop_event = threading.Event()

    # Pause event
    self._pause_event = threading.Event()
    self._pause_event.set()

# ============================================================
# 1. CLOCK / TIMESTAMP
# ============================================================

def now(self):
    """Timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)

def timestamp(self):
    """ISO timestamp."""
    return self.now().isoformat()

def monotonic(self):
    """Monotonic clock for durations."""
    return time.monotonic()

def get_current_time(self):
    """Current local time."""
    return datetime.now().strftime("%H:%M:%S")

def get_today_date(self):
    """Current local date."""
    return datetime.now().strftime("%Y-%m-%d")

def get_runtime_seconds(self):
    """Total utility runtime."""
    return max(0.0, time.monotonic() - self.runtime_start_time)

# ============================================================
# 2. CONTROL — STOP / PAUSE / RESUME
# ============================================================

def request_stop(self):
    """Request graceful stop."""
    self._stop_event.set()
    return True

def clear_stop(self):
    """Clear stop request."""
    self._stop_event.clear()
    return True

def is_stop_requested(self):
    """Check whether stop was requested."""
    return self._stop_event.is_set()

def pause(self):
    """Pause utility operations."""
    self._pause_event.clear()
    return True

def resume(self):
    """Resume utility operations."""
    self._pause_event.set()
    return True

def is_paused(self):
    """Check pause state."""
    return not self._pause_event.is_set()

def check_control(self):
    """
    Raise a controlled exception if automation was stopped.
    Wait while paused.
    """
    if self.is_stop_requested():
        raise RuntimeError("Automation stop requested.")

    while not self._pause_event.is_set():
        if self.is_stop_requested():
            raise RuntimeError("Automation stop requested.")
        time.sleep(0.10)

    return True

# ============================================================
# 3. SAFE SLEEP
# ============================================================

def sleep(self, seconds, interruptible=True):
    """
    Sleep without blindly blocking the automation forever.

    Returns:
        True  = completed
        False = interrupted
    """
    try:
        seconds = max(0.0, float(seconds))
    except (TypeError, ValueError):
        seconds = 0.0

    end_time = time.monotonic() + seconds

    while True:
        if interruptible and self.is_stop_requested():
            return False

        remaining = end_time - time.monotonic()

        if remaining <= 0:
            return True

        time.sleep(min(0.10, remaining))

# ============================================================
# 4. NORMAL ACTION DELAYS
# ============================================================

def human_delay(
    self,
    min_sec=DEFAULT_HUMAN_DELAY_MIN,
    max_sec=DEFAULT_HUMAN_DELAY_MAX
):
    """
    Natural pacing delay.

    This is for usability/stability only.
    It is NOT an anti-detection mechanism.
    """
    try:
        minimum = max(0.0, float(min_sec))
        maximum = max(minimum, float(max_sec))
    except (TypeError, ValueError):
        minimum = self.DEFAULT_HUMAN_DELAY_MIN
        maximum = self.DEFAULT_HUMAN_DELAY_MAX

    delay = random.uniform(minimum, maximum)
    self.sleep(delay)

    return delay

def thinking_time(self):
    """Short normal processing pause."""
    return self.human_delay(0.8, 2.0)

def action_pause(self):
    """Short pause between normal actions."""
    return self.human_delay(0.2, 0.8)

# ============================================================
# 5. TYPING SPEED
# ============================================================

def get_typing_speed(self):
    """
    Return normal typing speed in WPM.
    """
    return random.uniform(
        self.DEFAULT_TYPING_SPEED_MIN,
        self.DEFAULT_TYPING_SPEED_MAX
    )

def typing_delay(self, speed_wpm=None):
    """
    Calculate delay per character.
    """
    if speed_wpm is None:
        speed_wpm = self.get_typing_speed()

    try:
        speed_wpm = float(speed_wpm)
    except (TypeError, ValueError):
        speed_wpm = 45.0

    speed_wpm = max(1.0, speed_wpm)

    chars_per_second = speed_wpm * 5.0 / 60.0

    if chars_per_second <= 0:
        return 0.05

    return 1.0 / chars_per_second

def human_type(self, text, speed_wpm=None):
    """
    Type simulation utility.

    IMPORTANT:
    This function only generates a paced character sequence.
    Actual browser typing remains the responsibility of
    SmartHands/content.js.
    """
    if text is None:
        return ""

    text = str(text)

    base_delay = self.typing_delay(speed_wpm)

    output = []

    for char in text:
        self.check_control()

        delay = base_delay * random.uniform(0.75, 1.25)
        self.sleep(delay)

        output.append(char)

    return "".join(output)

# ============================================================
# 6. RETRY ENGINE
# ============================================================

def calculate_backoff(
    self,
    attempt,
    base=DEFAULT_BACKOFF_BASE,
    maximum=DEFAULT_BACKOFF_MAX
):
    """
    Exponential backoff with small jitter.

    attempt:
        0 -> first retry delay
        1 -> second retry delay
        ...
    """
    try:
        attempt = max(0, int(attempt))
        base = max(0.0, float(base))
        maximum = max(base, float(maximum))
    except (TypeError, ValueError):
        attempt = 0
        base = self.DEFAULT_BACKOFF_BASE
        maximum = self.DEFAULT_BACKOFF_MAX

    delay = min(maximum, base * (2 ** attempt))
    jitter = random.uniform(0.0, min(0.25, delay * 0.25))

    return min(maximum, delay + jitter)

def retry(
    self,
    function,
    max_retries=DEFAULT_MAX_RETRIES,
    retry_exceptions=(Exception,),
    action_name="operation",
    *args,
    **kwargs
):
    """
    Execute a function with bounded retries.

    Returns:
        function result

    Raises:
        last exception after retry limit.
    """
    max_retries = max(0, int(max_retries))

    last_error = None

    for attempt in range(max_retries + 1):
        self.check_control()

        try:
            result = function(*args, **kwargs)

            self.retry_count += attempt

            return result

        except retry_exceptions as exc:
            last_error = exc

            self.record_error(
                action_name,
                str(exc),
                attempt=attempt
            )

            if attempt >= max_retries:
                raise

            delay = self.calculate_backoff(attempt)

            self.retry_count += 1

            self.sleep(delay)

    if last_error:
        raise last_error

    return None

# ============================================================
# 7. WAIT ENGINE
# ============================================================

def wait_until(
    self,
    condition,
    timeout=DEFAULT_MAX_WAIT,
    interval=DEFAULT_WAIT_INTERVAL,
    description="condition"
):
    """
    Wait until condition() returns truthy.

    The condition should be lightweight.
    """
    try:
        timeout = max(0.0, float(timeout))
        interval = max(0.05, float(interval))
    except (TypeError, ValueError):
        timeout = self.DEFAULT_MAX_WAIT
        interval = self.DEFAULT_WAIT_INTERVAL

    start = time.monotonic()

    while time.monotonic() - start < timeout:
        self.check_control()

        try:
            if condition():
                return True
        except Exception as exc:
            self.record_error(
                f"wait:{description}",
                str(exc)
            )

        self.sleep(interval)

    return False

def wait_for_seconds(self, seconds):
    """Interruptible fixed wait."""
    return self.sleep(seconds)

# ============================================================
# 8. TASK TIMER
# ============================================================

def start_task_timer(self):
    """Start task timer."""
    with self._lock:
        self.task_start_time = datetime.now()
        self.task_end_time = None
        self.tasks_started += 1

    return self.task_start_time

def stop_task_timer(self):
    """Stop task timer."""
    with self._lock:
        if self.task_start_time is None:
            return 0.0

        self.task_end_time = datetime.now()

        elapsed = (
            self.task_end_time - self.task_start_time
        ).total_seconds()

        elapsed = max(0.0, elapsed)

        self.total_time_spent += elapsed

        return elapsed

def get_elapsed_time(self):
    """Current task elapsed time."""
    if self.task_start_time is None:
        return 0.0

    end = self.task_end_time or datetime.now()

    return max(
        0.0,
        (end - self.task_start_time).total_seconds()
    )

def get_target_time(self, estimated_seconds):
    """
    Calculate a reasonable target duration.

    This is scheduling logic only.
    It does not attempt to disguise automation.
    """
    try:
        estimated = max(0.0, float(estimated_seconds))
    except (TypeError, ValueError):
        estimated = 0.0

    # Small scheduling tolerance.
    target = estimated * random.uniform(0.90, 1.10)

    # Avoid absurdly small values.
    return max(0.5, target)

def wait_for_target(self, estimated_seconds):
    """
    Wait until target task duration.

    Useful when a workflow genuinely requires
    a minimum pacing interval.
    """
    target = self.get_target_time(estimated_seconds)
    elapsed = self.get_elapsed_time()

    if elapsed < target:
        remaining = target - elapsed
        return self.sleep(remaining)

    return False

def track_time(self, estimated_seconds):
    """Return task timing information."""
    elapsed = self.get_elapsed_time()
    target = self.get_target_time(estimated_seconds)

    return {
        "elapsed": round(elapsed, 3),
        "target": round(target, 3),
        "diff": round(target - elapsed, 3),
        "on_time": elapsed <= target,
        "timestamp": self.timestamp()
    }

# ============================================================
# 9. TASK STATUS
# ============================================================

def mark_task_started(self):
    self.start_task_timer()
    return True

def mark_task_completed(self):
    elapsed = self.stop_task_timer()

    with self._lock:
        self.tasks_completed += 1

    return elapsed

def mark_task_failed(self):
    elapsed = self.stop_task_timer()

    with self._lock:
        self.tasks_failed += 1

    return elapsed

def mark_task_skipped(self):
    with self._lock:
        self.tasks_skipped += 1

    return True

# ============================================================
# 10. ACTION TRACKING
# ============================================================

def record_action(
    self,
    action,
    success=True,
    duration=0.0,
    error=None,
    metadata=None
):
    """
    Record an automation action.
    """
    with self._lock:
        self.actions += 1

        if success:
            self.successful_actions += 1
        else:
            self.failed_actions += 1

        self.last_action_time = time.monotonic()

        item = {
            "action": str(action),
            "success": bool(success),
            "duration": round(float(duration or 0), 4),
            "error": str(error) if error else None,
            "timestamp": self.timestamp(),
            "metadata": self.sanitize_metadata(metadata)
        }

        self.action_history.append(item)

        if len(self.action_history) > self.MAX_HISTORY:
            self.action_history = self.action_history[
                -self.MAX_HISTORY:
            ]

    return item

def record_error(self, action, error, attempt=None):
    """Record an error without exposing secrets."""
    item = {
        "action": str(action),
        "error": self.redact_sensitive_text(str(error)),
        "attempt": attempt,
        "timestamp": self.timestamp()
    }

    with self._lock:
        self.error_history.append(item)

        if len(self.error_history) > self.MAX_HISTORY:
            self.error_history = self.error_history[
                -self.MAX_HISTORY:
            ]

    return item

# ============================================================
# 11. ACTION WRAPPER
# ============================================================

def run_action(
    self,
    action_name,
    function,
    *args,
    max_retries=0,
    **kwargs
):
    """
    Execute and automatically measure an action.
    """
    self.check_control()

    started = time.monotonic()

    try:
        if max_retries > 0:
            result = self.retry(
                function,
                max_retries=max_retries,
                action_name=action_name,
                *args,
                **kwargs
            )
        else:
            result = function(*args, **kwargs)

        duration = time.monotonic() - started

        self.record_action(
            action_name,
            success=True,
            duration=duration
        )

        return result

    except Exception as exc:
        duration = time.monotonic() - started

        self.record_action(
            action_name,
            success=False,
            duration=duration,
            error=exc
        )

        raise

# ============================================================
# 12. BREAK MANAGEMENT
# ============================================================

def take_break(
    self,
    chance=0.0,
    minimum_seconds=30,
    maximum_seconds=120
):
    """
    Optional break scheduler.

    Default chance is 0, so automation does not unexpectedly
    sleep for a long period.
    """
    try:
        chance = min(1.0, max(0.0, float(chance)))
        minimum_seconds = max(0.0, float(minimum_seconds))
        maximum_seconds = max(
            minimum_seconds,
            float(maximum_seconds)
        )
    except (TypeError, ValueError):
        return False

    if random.random() >= chance:
        return False

    duration = random.uniform(
        minimum_seconds,
        maximum_seconds
    )

    return self.sleep(duration)

# ============================================================
# 13. DECISION HELPERS
# ============================================================

def should_make_mistake(self, chance=0.0):
    """
    Kept for backward compatibility.

    Default is disabled because reliable automation
    should not intentionally introduce errors.
    """
    try:
        chance = min(1.0, max(0.0, float(chance)))
    except (TypeError, ValueError):
        chance = 0.0

    return random.random() < chance

def should_skip_task(self, chance=0.0):
    """Optional task-skip decision."""
    try:
        chance = min(1.0, max(0.0, float(chance)))
    except (TypeError, ValueError):
        chance = 0.0

    return random.random() < chance

# ============================================================
# 14. COLLECTION UTILITIES
# ============================================================

def random_element(self, elements):
    """Safe random list selection."""
    if not elements:
        return None

    try:
        return random.choice(elements)
    except (IndexError, TypeError):
        return None

def first_non_empty(self, *values):
    """Return first non-empty value."""
    for value in values:
        if value is not None and str(value).strip():
            return value

    return None

def clamp(self, value, minimum, maximum):
    """Clamp numeric value."""
    try:
        value = float(value)
        minimum = float(minimum)
        maximum = float(maximum)

        return max(minimum, min(maximum, value))
    except (TypeError, ValueError):
        return minimum

# ============================================================
# 15. TEXT UTILITIES
# ============================================================

def normalize_text(self, text):
    """
    Normalize whitespace while preserving readable text.
    """
    if text is None:
        return ""

    text = str(text)

    text = text.replace("\x00", " ")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()

def truncate_text(
    self,
    text,
    maximum=MAX_TEXT_LENGTH,
    suffix="..."
):
    """Safely truncate large page text."""
    if text is None:
        return ""

    text = str(text)

    try:
        maximum = max(1, int(maximum))
    except (TypeError, ValueError):
        maximum = self.MAX_TEXT_LENGTH

    if len(text) <= maximum:
        return text

    if maximum <= len(suffix):
        return text[:maximum]

    return text[:maximum - len(suffix)] + suffix

def contains_any(self, text, words, case_sensitive=False):
    """Check whether text contains any supplied word."""
    if text is None:
        return False

    source = str(text)

    if not case_sensitive:
        source = source.lower()

    for word in words or []:
        if word is None:
            continue

        candidate = str(word)

        if not case_sensitive:
            candidate = candidate.lower()

        if candidate in source:
            return True

    return False

def clean_lines(self, text):
    """Return unique non-empty cleaned lines."""
    if text is None:
        return []

    result = []
    seen = set()

    for line in str(text).splitlines():
        line = self.normalize_text(line)

        if not line:
            continue

        key = line.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(line)

    return result

# ============================================================
# 16. URL UTILITIES
# ============================================================

def is_valid_url(self, url):
    """Basic HTTP/HTTPS URL validation."""
    if not url:
        return False

    try:
        parsed = urlparse(str(url).strip())

        return (
            parsed.scheme.lower() in ("http", "https")
            and bool(parsed.netloc)
        )
    except Exception:
        return False

def normalize_url(self, url):
    """Normalize a URL without altering its destination."""
    if not url:
        return ""

    url = str(url).strip()

    if not url:
        return ""

    if "://" not in url:
        url = "https://" + url

    try:
        parsed = urlparse(url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        return urlunparse((
            scheme,
            netloc,
            parsed.path or "/",
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    except Exception:
        return url

def get_domain(self, url):
    """Extract hostname."""
    try:
        parsed = urlparse(self.normalize_url(url))
        return parsed.netloc.lower()
    except Exception:
        return ""

# ============================================================
# 17. SELECTOR UTILITIES
# ============================================================

def css_escape_string(self, value):
    """
    Escape a value for use inside a CSS string.

    This does NOT execute JavaScript.
    """
    if value is None:
        return ""

    value = str(value)

    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\A ")
        .replace("\r", "\\D ")
    )

def js_string(self, value):
    """
    Safely encode a Python value as a JavaScript string literal.

    Uses JSON encoding instead of unsafe f-string interpolation.
    """
    return json.dumps(
        "" if value is None else str(value),
        ensure_ascii=False
    )

# ============================================================
# 18. JSON UTILITIES
# ============================================================

def safe_json_loads(self, value, default=None):
    """Safe JSON decode."""
    if value is None:
        return default

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default

def safe_json_dumps(self, value, default="{}"):
    """Safe JSON encode."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":")
        )
    except (TypeError, ValueError):
        return default

# ============================================================
# 19. SECURITY / LOG SANITIZATION
# ============================================================

def redact_sensitive_text(self, text):
    """
    Remove common credential/token-like values from logs.

    This is intentionally conservative.
    """
    if text is None:
        return ""

    text = str(text)

    patterns = [
        (
            r"(?i)(password\s*[=:]\s*)[^,\s]+",
            r"\1[REDACTED]"
        ),
        (
            r"(?i)(api[_-]?key\s*[=:]\s*)[^,\s]+",
            r"\1[REDACTED]"
        ),
        (
            r"(?i)(token\s*[=:]\s*)[^,\s]+",
            r"\1[REDACTED]"
        ),
        (
            r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
            r"\1[REDACTED]"
        )
    ]

    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)

    return self.truncate_text(text, 5000)

def sanitize_metadata(self, metadata):
    """Remove obvious sensitive fields from action metadata."""
    if metadata is None:
        return {}

    if not isinstance(metadata, dict):
        return {
            "value": self.redact_sensitive_text(metadata)
        }

    blocked = {
        "password",
        "passwd",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "cookie",
        "cookies",
        "authorization"
    }

    result = {}

    for key, value in metadata.items():
        normalized_key = str(key).lower()

        if normalized_key in blocked:
            result[str(key)] = "[REDACTED]"
        else:
            result[str(key)] = value

    return result

# ============================================================
# 20. RESULT BUILDER
# ============================================================

def result(
    self,
    success,
    action,
    data=None,
    error=None,
    requires_human=False,
    url=None,
    title=None,
    **extra
):
    """
    Standard result format shared by automation components.
    """
    output = {
        "success": bool(success),
        "action": str(action),
        "url": url,
        "title": title,
        "data": data,
        "error": self.redact_sensitive_text(error)
            if error else None,
        "requires_human": bool(requires_human),
        "timestamp": self.timestamp()
    }

    output.update(extra)

    return output

# ============================================================
# 21. METRICS
# ============================================================

def get_metrics(self):
    """Return complete runtime metrics."""
    with self._lock:
        success_rate = 0.0

        if self.actions:
            success_rate = (
                self.successful_actions /
                self.actions
            ) * 100.0

        return {
            "version": self.VERSION,

            "runtime_seconds": round(
                self.get_runtime_seconds(),
                3
            ),

            "task": {
                "started": self.tasks_started,
                "completed": self.tasks_completed,
                "failed": self.tasks_failed,
                "skipped": self.tasks_skipped,
                "current_elapsed": round(
                    self.get_elapsed_time(),
                    3
                )
            },

            "actions": {
                "total": self.actions,
                "successful": self.successful_actions,
                "failed": self.failed_actions,
                "retries": self.retry_count,
                "success_rate_percent": round(
                    success_rate,
                    2
                )
            },

            "time": {
                "total_task_time": round(
                    self.total_time_spent,
                    3
                )
            },

            "control": {
                "stopped": self.is_stop_requested(),
                "paused": self.is_paused()
            },

            "history": {
                "actions": len(self.action_history),
                "errors": len(self.error_history)
            },

            "timestamp": self.timestamp()
        }

# ============================================================
# 22. HISTORY
# ============================================================

def get_action_history(self, limit=50):
    """Return recent action history."""
    try:
        limit = max(1, int(limit))
    except (TypeError, ValueError):
        limit = 50

    with self._lock:
        return list(self.action_history[-limit:])

def get_error_history(self, limit=50):
    """Return recent error history."""
    try:
        limit = max(1, int(limit))
    except (TypeError, ValueError):
        limit = 50

    with self._lock:
        return list(self.error_history[-limit:])

def clear_history(self):
    """Clear action/error history."""
    with self._lock:
        self.action_history.clear()
        self.error_history.clear()

    return True

# ============================================================
# 23. RESET
# ============================================================

def reset_task(self):
    """Reset current task timer only."""
    with self._lock:
        self.task_start_time = None
        self.task_end_time = None

    return True

def reset_metrics(self):
    """Reset counters while keeping control state."""
    with self._lock:
        self.total_time_spent = 0.0

        self.actions = 0
        self.successful_actions = 0
        self.failed_actions = 0
        self.retry_count = 0

        self.tasks_started = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_skipped = 0

        self.action_history.clear()
        self.error_history.clear()

        self.runtime_start_time = time.monotonic()

    return True

# ============================================================
# 24. COMPATIBILITY HELPERS
# ============================================================

def get_status(self):
    """Compatibility status method."""
    return self.get_metrics()

def ping(self):
    """Simple health check."""
    return {
        "ok": True,
        "version": self.VERSION,
        "timestamp": self.timestamp()
    }

============================================================

OPTIONAL MODULE-LEVEL HELPERS

============================================================

def utc_timestamp():
"""Simple global timestamp helper."""
return datetime.now(timezone.utc).isoformat()

def safe_json(value):
"""Simple global JSON serializer."""
try:
return json.dumps(
value,
ensure_ascii=False
)
except Exception:
return "{}"

============================================================

END OF smart_utils.py v8.0.0

============================================================
