# ============================================================
# 📁 FILE: main.py - SMART WEBSITE MASTER (BOSS) v7.0
# 🎯 ROLE: MASTER ORCHESTRATOR
# 🔗 USED BY: ai_service.py, app.py
#
# PURPOSE:
#   • Task orchestration
#   • Browser connection management
#   • Checkpoint / Resume
#   • Retry + Self-Healing
#   • Platform detection
#   • Task filtering
#   • Safe human handoff
#   • Persistent local state
#   • Graceful stop / pause
#   • Runtime status
#
# IMPORTANT:
#   CAPTCHA / OTP / payment / security verification
#   ko bypass nahi karta. Human handoff par rukta hai.
# ============================================================

import time
import json
import os
import re
import threading
from datetime import datetime

from config import *
from smart_hands import SmartHands
from smart_utils import SmartUtils


class SmartMain:
    """
    🧠 SMART WEBSITE MASTER

    Ye system ka BOSS / Orchestrator hai.

    Flow:

        COMMAND
           ↓
        PLATFORM DETECT
           ↓
        STATE LOAD
           ↓
        BROWSER CONNECT
           ↓
        NAVIGATE
           ↓
        OBSERVE / SCAN
           ↓
        TASK FILTER
           ↓
        TASK EXECUTION
           ↓
        VERIFY
           ↓
        CHECKPOINT
           ↓
        NEXT TASK
           ↓
        SUMMARY

    Agar browser band ho jaye:
        state save hoti hai
        system reconnect/resume kar sakta hai.

    Agar CAPTCHA / OTP / payment/security challenge mile:
        HUMAN_HANDOFF state
        task pause
        unsafe bypass nahi.
    """

    VERSION = "7.0.0"

    # --------------------------------------------------------
    # Runtime limits
    # --------------------------------------------------------

    DEFAULT_MAX_TASKS = 5
    DEFAULT_TASK_TIMEOUT = 180
    DEFAULT_RETRY_LIMIT = 3
    DEFAULT_MIN_FILLED = 70

    CHECKPOINT_FILE = "smart_master_checkpoint.json"
    RUNTIME_FILE = "smart_master_runtime.json"

    # --------------------------------------------------------
    # Platform configuration
    # --------------------------------------------------------

    PLATFORM_URLS = {
        "rapidworkers": "https://rapidworkers.com",
        "timebucks": "https://www.timebucks.com",
        "freecash": "https://www.freecash.com",
        "swagbucks": "https://www.swagbucks.com",
        "ysense": "https://www.ysense.com",
        "prizerebel": "https://www.prizerebel.com",
        "grabpoints": "https://www.grabpoints.com",
    }

    PLATFORM_ALIASES = {
        "rapidworker": "rapidworkers",
        "rapidworkers": "rapidworkers",
        "rapid worker": "rapidworkers",

        "timebucks": "timebucks",
        "time bucks": "timebucks",

        "freecash": "freecash",
        "free cash": "freecash",

        "swagbucks": "swagbucks",
        "swag bucks": "swagbucks",

        "ysense": "ysense",
        "y sense": "ysense",

        "prizerebel": "prizerebel",
        "prize rebel": "prizerebel",

        "grabpoints": "grabpoints",
        "grab points": "grabpoints",
    }

    # --------------------------------------------------------
    # Safe human-intervention indicators
    # --------------------------------------------------------

    HUMAN_HANDOFF_WORDS = (
        "captcha",
        "recaptcha",
        "hcaptcha",
        "otp",
        "one time password",
        "verification code",
        "security verification",
        "payment verification",
        "card verification",
        "identity verification",
        "human verification",
    )

    # ========================================================
    # 1. INITIALIZATION
    # ========================================================

    def __init__(self):
        self.hands = SmartHands()
        self.utils = SmartUtils()

        # Memory
        self.memory = self._load_memory()

        # Runtime counters
        self.retry_count = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.total_earned = 0.0

        # State
        self.is_running = False
        self.is_paused = False
        self.stop_requested = False
        self.human_handoff = False

        self.current_task = None
        self.current_task_index = 0
        self.current_platform = "rapidworkers"

        self.start_time = None
        self.last_action_time = None
        self.last_error = None
        self.last_result = None

        # Current execution information
        self.current_phase = "idle"
        self.current_action = None

        # Resume information
        self.resume_available = False
        self.session_id = None

        # Thread lock
        self._lock = threading.RLock()

        # Load previous checkpoint
        self._load_checkpoint()

    # ========================================================
    # 2. SAFE CONFIG HELPERS
    # ========================================================

    def _get_config(self, name, default=None):
        """
        config.py mein variable available ho toh use karo.
        Nahi toh default.
        """
        try:
            return globals().get(name, default)
        except Exception:
            return default

    def _get_max_retries(self):
        value = self._get_config("MAX_RETRIES", self.DEFAULT_RETRY_LIMIT)

        try:
            return max(1, int(value))
        except Exception:
            return self.DEFAULT_RETRY_LIMIT

    def _get_min_filled_percent(self):
        value = self._get_config(
            "MIN_FILLED_PERCENT",
            self.DEFAULT_MIN_FILLED
        )

        try:
            return float(value)
        except Exception:
            return float(self.DEFAULT_MIN_FILLED)

    # ========================================================
    # 3. TIME / ID HELPERS
    # ========================================================

    def _now(self):
        return datetime.now().isoformat()

    def _new_session_id(self):
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _elapsed_seconds(self):
        if not self.start_time:
            return 0

        try:
            return max(
                0,
                int((datetime.now() - self.start_time).total_seconds())
            )
        except Exception:
            return 0

    # ========================================================
    # 4. MEMORY
    # ========================================================

    def _load_memory(self):
        """
        Existing MEMORY_FILE ko preserve karta hai.
        """
        memory_file = self._get_config(
            "MEMORY_FILE",
            "smart_memory.json"
        )

        try:
            if os.path.exists(memory_file):
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict):
                    raise ValueError("Invalid memory format")

                data.setdefault("tasks", [])
                data.setdefault("learnings", {})

                return data

        except Exception as e:
            print(f"⚠️ Memory load failed: {e}")

        return {
            "tasks": [],
            "learnings": {}
        }

    def _save_memory(self):
        memory_file = self._get_config(
            "MEMORY_FILE",
            "smart_memory.json"
        )

        try:
            temp_file = memory_file + ".tmp"

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    self.memory,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

            os.replace(temp_file, memory_file)

        except Exception as e:
            print(f"⚠️ Memory save failed: {e}")

    def _store_experience(
        self,
        task,
        success,
        notes="",
        platform=None
    ):
        """
        Experience ko memory mein store karta hai.
        """
        try:
            entry = {
                "task": str(task)[:500],
                "success": bool(success),
                "timestamp": self._now(),
                "platform": platform or self.current_platform,
                "notes": str(notes)[:1000]
            }

            self.memory.setdefault("tasks", [])
            self.memory["tasks"].append(entry)

            # Memory ko unlimited grow hone se bachao.
            if len(self.memory["tasks"]) > 1000:
                self.memory["tasks"] = self.memory["tasks"][-1000:]

            self._save_memory()

        except Exception as e:
            print(f"⚠️ Experience save failed: {e}")

    def _get_previous_learning(self, task):
        """
        Same successful task ki previous learning.
        """
        try:
            tasks = self.memory.get("tasks", [])

            for item in reversed(tasks):
                if (
                    item.get("task") == task
                    and item.get("success") is True
                ):
                    return item.get("notes", "")

        except Exception:
            pass

        return None

    # ========================================================
    # 5. CHECKPOINT SYSTEM
    # ========================================================

    def _checkpoint_data(self):
        return {
            "version": self.VERSION,
            "session_id": self.session_id,

            "timestamp": self._now(),

            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "stop_requested": self.stop_requested,
            "human_handoff": self.human_handoff,

            "platform": self.current_platform,

            "current_phase": self.current_phase,
            "current_action": self.current_action,

            "current_task": self.current_task,
            "current_task_index": self.current_task_index,

            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "retry_count": self.retry_count,

            "total_earned": self.total_earned,

            "last_error": self.last_error,
            "last_result": self.last_result,

            "start_time": (
                self.start_time.isoformat()
                if self.start_time else None
            )
        }

    def _save_checkpoint(self):
        """
        Atomic checkpoint save.

        Crash / browser close ke baad state recover karne mein
        help karta hai.
        """
        try:
            data = self._checkpoint_data()

            temp = self.CHECKPOINT_FILE + ".tmp"

            with open(temp, "w", encoding="utf-8") as f:
                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

            os.replace(temp, self.CHECKPOINT_FILE)

            self.resume_available = True

        except Exception as e:
            print(f"⚠️ Checkpoint save failed: {e}")

    def _load_checkpoint(self):
        """
        Previous session ka checkpoint load.
        """
        try:
            if not os.path.exists(self.CHECKPOINT_FILE):
                return False

            with open(
                self.CHECKPOINT_FILE,
                "r",
                encoding="utf-8"
            ) as f:
                data = json.load(f)

            if not isinstance(data, dict):
                return False

            # Old completed session ko automatically resume nahi karo.
            old_running = data.get("is_running", False)

            if not old_running:
                return False

            self.session_id = data.get("session_id")

            self.current_platform = data.get(
                "platform",
                self.current_platform
            )

            self.current_phase = data.get(
                "current_phase",
                "resume"
            )

            self.current_action = data.get("current_action")

            self.current_task = data.get("current_task")

            self.current_task_index = int(
                data.get("current_task_index", 0)
            )

            self.tasks_completed = int(
                data.get("tasks_completed", 0)
            )

            self.tasks_failed = int(
                data.get("tasks_failed", 0)
            )

            self.retry_count = int(
                data.get("retry_count", 0)
            )

            self.total_earned = float(
                data.get("total_earned", 0.0)
            )

            self.last_error = data.get("last_error")
            self.last_result = data.get("last_result")

            self.is_paused = True
            self.resume_available = True

            print(
                f"♻️ Previous checkpoint found: "
                f"{self.current_platform}"
            )

            return True

        except Exception as e:
            print(f"⚠️ Checkpoint load failed: {e}")

        return False

    def clear_checkpoint(self):
        """
        Successful final completion ke baad checkpoint remove.
        """
        try:
            if os.path.exists(self.CHECKPOINT_FILE):
                os.remove(self.CHECKPOINT_FILE)

            self.resume_available = False

        except Exception as e:
            print(f"⚠️ Checkpoint clear failed: {e}")

    # ========================================================
    # 6. RUNTIME STATE
    # ========================================================

    def _save_runtime(self):
        try:
            data = {
                "version": self.VERSION,
                "timestamp": self._now(),
                "platform": self.current_platform,
                "phase": self.current_phase,
                "action": self.current_action,
                "task": self.current_task,
                "task_index": self.current_task_index,
                "running": self.is_running,
                "paused": self.is_paused,
                "human_handoff": self.human_handoff,
                "last_error": self.last_error
            }

            with open(
                self.RUNTIME_FILE,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    data,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception:
            pass

    def _set_phase(self, phase, action=None):
        with self._lock:
            self.current_phase = phase
            self.current_action = action
            self.last_action_time = datetime.now()

            self._save_runtime()
            self._save_checkpoint()

    # ========================================================
    # 7. STOP / PAUSE CONTROL
    # ========================================================

    def request_stop(self):
        """
        Safe graceful stop.
        """
        with self._lock:
            self.stop_requested = True
            self.is_paused = False

            self._set_phase("stopping")

            print("🛑 Stop requested.")

    def pause(self, reason="Manual pause"):
        """
        Pause without destroying checkpoint.
        """
        with self._lock:
            self.is_paused = True
            self._set_phase("paused", reason)

            print(f"⏸️ Paused: {reason}")

    def resume(self):
        """
        Existing checkpoint se resume.
        """
        with self._lock:
            if not self.resume_available and not self.current_task:
                return False

            self.stop_requested = False
            self.is_paused = False
            self.human_handoff = False

            self._set_phase("resuming")

            print("▶️ Resume requested.")

            return True

    def _should_stop(self):
        return self.stop_requested

    # ========================================================
    # 8. HUMAN HANDOFF
    # ========================================================

    def _requires_human(self, text):
        """
        Unsafe/security challenge detect.
        """
        if not text:
            return False

        value = str(text).lower()

        return any(
            word in value
            for word in self.HUMAN_HANDOFF_WORDS
        )

    def _enter_human_handoff(self, reason):
        """
        Security challenge par system stop/pause.
        """
        self.human_handoff = True
        self.is_paused = True
        self.current_phase = "human_handoff"
        self.current_action = reason

        self.last_error = reason

        self._save_checkpoint()
        self._save_runtime()

        print(f"👤 HUMAN HANDOFF REQUIRED: {reason}")

        return {
            "status": "human_handoff",
            "requires_human": True,
            "reason": reason,
            "platform": self.current_platform,
            "task": self.current_task
        }

    # ========================================================
    # 9. PLATFORM DETECTION
    # ========================================================

    def detect_platform(self, command):
        """
        Command se platform intelligently detect.
        """
        text = str(command or "").lower()

        # Longest match first
        aliases = sorted(
            self.PLATFORM_ALIASES.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for alias, platform in aliases:
            if alias in text:
                return platform

        return "rapidworkers"

    def get_platform_url(self, platform):
        return self.PLATFORM_URLS.get(
            platform,
            self.PLATFORM_URLS["rapidworkers"]
        )

    # ========================================================
    # 10. SAFE METHOD CALLER
    # ========================================================

    def _call_if_available(
        self,
        obj,
        method_name,
        *args,
        **kwargs
    ):
        """
        SmartHands / SmartUtils mein method available ho toh
        call karo.

        Isse new main.py purane modules ko unnecessarily break
        nahi karta.
        """
        try:
            method = getattr(obj, method_name, None)

            if callable(method):
                return True, method(*args, **kwargs)

        except Exception as e:
            return False, e

        return False, None

    # ========================================================
    # 11. BROWSER CONNECTION
    # ========================================================

    def _connect_browser(self):
        self._set_phase("browser_connect")

        try:
            ok, result = self._call_if_available(
                self.hands,
                "connect"
            )

            if not ok:
                return False

            return bool(result)

        except Exception as e:
            self.last_error = str(e)
            return False

    def _navigate(self, url):
        self._set_phase("navigation", url)

        try:
            ok, result = self._call_if_available(
                self.hands,
                "navigate",
                url
            )

            if not ok:
                return False

            return result is not False

        except Exception as e:
            self.last_error = str(e)
            return False

    # ========================================================
    # 12. TASK SCANNING
    # ========================================================

    def _get_page_text(self):
        """
        SmartHands ke existing get_page_text() ko use karta hai.
        """
        try:
            ok, result = self._call_if_available(
                self.hands,
                "get_page_text"
            )

            if ok and result is not None:
                return str(result)

        except Exception:
            pass

        return ""

    def _scan_tasks(self):
        """
        Dashboard se tasks identify.

        Existing 70%+ logic preserve kiya gaya hai.
        """
        self._set_phase("task_scan")

        print("📡 Scanning dashboard tasks...")

        page_text = self._get_page_text()

        if not page_text:
            print("⚠️ No page text received.")
            return []

        tasks = []

        lines = page_text.splitlines()

        min_percent = self._get_min_filled_percent()

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Examples:
            # 7/10
            # 70/100
            # 15 / 20
            matches = re.findall(
                r"(\d+)\s*/\s*(\d+)",
                line
            )

            if not matches:
                continue

            for filled_raw, total_raw in matches:
                try:
                    filled = int(filled_raw)
                    total = int(total_raw)

                    if total <= 0:
                        continue

                    percent = (
                        filled / total
                    ) * 100

                    if percent >= min_percent:
                        tasks.append({
                            "title": line[:200],
                            "filled": filled,
                            "total": total,
                            "percent": round(percent, 2),
                            "platform": self.current_platform
                        })

                except Exception:
                    continue

        # Duplicate remove
        unique = []
        seen = set()

        for task in tasks:
            key = (
                task["title"],
                task["filled"],
                task["total"]
            )

            if key not in seen:
                seen.add(key)
                unique.append(task)

        # Highest fill percentage first
        unique.sort(
            key=lambda x: x.get("percent", 0),
            reverse=True
        )

        print(
            f"✅ Found {len(unique)} tasks "
            f"with {min_percent:.0f}%+ filled."
        )

        return unique

    # ========================================================
    # 13. TASK VALIDATION
    # ========================================================

    def _validate_task(self, task):
        if not isinstance(task, dict):
            return False, "Invalid task object"

        title = str(task.get("title", "")).strip()

        if not title:
            return False, "Task title missing"

        if self._requires_human(title):
            return False, "Security/human verification detected"

        return True, ""

    # ========================================================
    # 14. TASK EXECUTION
    # ========================================================

    def _do_task(self, task):
        """
        Actual task execution layer.

        Existing SmartHands-specific automation ko preserve
        karta hai.

        Agar advanced execute_task() available hai:
            use it.

        Warna old safe execution flow.
        """
        title = str(task.get("title", ""))

        self._set_phase(
            "task_execute",
            title[:100]
        )

        print(
            f"▶️ Executing: {title[:100]}"
        )

        # Security check
        if self._requires_human(title):
            self._enter_human_handoff(
                "Security verification detected"
            )
            return False

        # ----------------------------------------------------
        # Advanced SmartHands hook
        # ----------------------------------------------------

        advanced_methods = (
            "execute_task",
            "perform_task",
            "run_task"
        )

        for method_name in advanced_methods:
            try:
                method = getattr(
                    self.hands,
                    method_name,
                    None
                )

                if callable(method):
                    result = method(task)

                    if isinstance(result, dict):
                        if result.get("requires_human"):
                            self._enter_human_handoff(
                                result.get(
                                    "reason",
                                    "Human verification required"
                                )
                            )
                            return False

                        if "success" in result:
                            return bool(result["success"])

                    return bool(result)

            except Exception as e:
                print(
                    f"⚠️ {method_name} failed: {e}"
                )
                self.last_error = str(e)

        # ----------------------------------------------------
        # Existing fallback behavior
        # ----------------------------------------------------

        try:
            ok, speed = self._call_if_available(
                self.utils,
                "get_typing_speed"
            )

            if ok:
                try:
                    print(
                        f"⌨️ Typing speed: "
                        f"{float(speed):.0f} WPM"
                    )
                except Exception:
                    pass

        except Exception:
            pass

        self._call_if_available(
            self.utils,
            "action_pause"
        )

        # Existing simulated mistake logic preserved.
        try:
            ok, mistake = self._call_if_available(
                self.utils,
                "should_make_mistake",
                0.10
            )

            if ok and mistake:
                print("⚠️ Simulated retry condition.")
                return False

        except Exception:
            pass

        self._call_if_available(
            self.utils,
            "take_break"
        )

        # ----------------------------------------------------
        # NOTE:
        # Real website interaction should be implemented
        # inside SmartHands / browser bridge.
        #
        # This fallback does NOT falsely claim that a website
        # task was completed.
        # ----------------------------------------------------

        return False

    # ========================================================
    # 15. TASK RESULT VERIFICATION
    # ========================================================

    def _verify_task(self, task, result):
        """
        Result ko verify karta hai.

        False positive avoid karne ke liye simple success
        claim nahi karta.
        """
        if isinstance(result, dict):
            if result.get("requires_human"):
                return False

            if "success" in result:
                return bool(result["success"])

        return bool(result)

    # ========================================================
    # 16. RETRY ENGINE
    # ========================================================

    def _execute_task_with_retry(self, task):
        """
        Self-healing retry engine.
        """
        max_retries = self._get_max_retries()

        title = str(task.get("title", ""))

        previous = self._get_previous_learning(title)

        if previous:
            print(
                f"🧠 Previous learning found: "
                f"{previous[:200]}"
            )

        for attempt in range(1, max_retries + 1):

            if self._should_stop():
                return False

            while self.is_paused and not self.stop_requested:
                time.sleep(1)

            self.retry_count += 1

            print(
                f"🔄 Task attempt "
                f"{attempt}/{max_retries}"
            )

            self.current_task = task

            self._set_phase(
                "task_attempt",
                f"{attempt}/{max_retries}"
            )

            try:
                # Optional thinking delay
                self._call_if_available(
                    self.utils,
                    "thinking_time"
                )

                result = self._do_task(task)

                verified = self._verify_task(
                    task,
                    result
                )

                self.last_result = {
                    "task": title,
                    "success": verified,
                    "attempt": attempt,
                    "timestamp": self._now()
                }

                if verified:
                    self.tasks_completed += 1

                    # Existing earning logic preserved,
                    # but only after actual success.
                    self.total_earned += 0.10

                    self._store_experience(
                        title,
                        True,
                        "Task completed successfully",
                        self.current_platform
                    )

                    self._save_checkpoint()

                    print(
                        f"✅ Task completed."
                    )

                    return True

                # Human handoff state
                if self.human_handoff:
                    return False

                print(
                    "⚠️ Task did not verify as successful."
                )

                if attempt < max_retries:
                    self._call_if_available(
                        self.utils,
                        "human_delay",
                        2,
                        5
                    )

            except Exception as e:
                self.last_error = str(e)

                print(
                    f"❌ Task attempt error: {e}"
                )

                self._save_checkpoint()

                if attempt < max_retries:
                    self._call_if_available(
                        self.utils,
                        "human_delay",
                        3,
                        6
                    )

        self.tasks_failed += 1

        self._store_experience(
            title,
            False,
            f"Failed after {max_retries} attempts",
            self.current_platform
        )

        return False

    # ========================================================
    # 17. TIME MANAGEMENT
    # ========================================================

    def run_with_time_management(
        self,
        task_description,
        estimated_seconds=120,
        task=None
    ):
        """
        Task timer + execution.
        """
        self._set_phase(
            "time_managed_task",
            task_description
        )

        print(
            f"⏱️ Estimated time: "
            f"{estimated_seconds}s"
        )

        self._call_if_available(
            self.utils,
            "start_task_timer"
        )

        task_data = task or {
            "title": task_description
        }

        started = time.time()

        result = self._execute_task_with_retry(
            task_data
        )

        elapsed = time.time() - started

        target = float(estimated_seconds)

        try:
            ok, actual_elapsed = self._call_if_available(
                self.utils,
                "get_elapsed_time"
            )

            if ok:
                elapsed = float(actual_elapsed)

        except Exception:
            pass

        print(
            f"⏱️ Time: {elapsed:.1f}s "
            f"| Target: {target:.1f}s"
        )

        if elapsed <= target:
            print("✅ Within target time.")
        else:
            print("⚠️ Above target time.")

        return result

    # ========================================================
    # 18. NAVIGATION + PLATFORM SETUP
    # ========================================================

    def _prepare_platform(self):
        """
        Browser connect + platform navigation.
        """
        platform = self.current_platform
        url = self.get_platform_url(platform)

        # Connect
        if not self._connect_browser():
            self.last_error = "Browser not connected"
            return False

        # Navigate
        if not self._navigate(url):
            self.last_error = (
                f"Navigation failed: {url}"
            )
            return False

        # Wait
        self._call_if_available(
            self.utils,
            "human_delay",
            3,
            5
        )

        return True

    # ========================================================
    # 19. OPTIONAL LOGIN HOOK
    # ========================================================

    def _platform_login(self):
        """
        Existing login methods ko preserve karta hai.

        IMPORTANT:
        CAPTCHA/OTP aaye toh human handoff.
        """
        platform = self.current_platform

        self._set_phase(
            "login",
            platform
        )

        print(
            f"🔑 Preparing login: {platform}"
        )

        credentials = {
            "rapidworkers": (
                self._get_config("GOOGLE_EMAIL"),
                self._get_config("GOOGLE_PASSWORD")
            ),

            "timebucks": (
                self._get_config("TIMEBUCKS_EMAIL"),
                self._get_config("TIMEBUCKS_PASSWORD")
            ),

            "freecash": (
                self._get_config("FREECASH_EMAIL"),
                self._get_config("FREECASH_PASSWORD")
            ),

            "swagbucks": (
                self._get_config("SWAGBUCKS_EMAIL"),
                self._get_config("SWAGBUCKS_PASSWORD")
            ),

            "ysense": (
                self._get_config("YSENSE_EMAIL"),
                self._get_config("YSENSE_PASSWORD")
            ),

            "prizerebel": (
                self._get_config("PRIZEREBEL_EMAIL"),
                self._get_config("PRIZEREBEL_PASSWORD")
            ),

            "grabpoints": (
                self._get_config("GRABPOINTS_EMAIL"),
                self._get_config("GRABPOINTS_PASSWORD")
            )
        }

        email, password = credentials.get(
            platform,
            (None, None)
        )

        # Agar credentials configured nahi hain,
        # silently fake-login nahi karna.
        if not email or not password:
            print(
                "ℹ️ No configured credentials "
                f"for {platform}. "
                "Continuing without automatic login."
            )
            return True

        method_name = f"{platform}_login"

        method = getattr(
            self.hands,
            method_name,
            None
        )

        if not callable(method):
            print(
                f"ℹ️ {method_name}() not available."
            )
            return True

        try:
            result = method(
                email,
                password
            )

            if isinstance(result, dict):
                if result.get("requires_human"):
                    self._enter_human_handoff(
                        result.get(
                            "reason",
                            "Login verification required"
                        )
                    )
                    return False

                if result.get("success") is False:
                    return False

            return result is not False

        except Exception as e:
            self.last_error = str(e)

            if self._requires_human(str(e)):
                self._enter_human_handoff(
                    str(e)
                )

            return False

    # ========================================================
    # 20. TASK SELECTION
    # ========================================================

    def _select_tasks(self, tasks, limit=None):
        """
        Best eligible tasks select.
        """
        if limit is None:
            limit = self.DEFAULT_MAX_TASKS

        selected = []

        for task in tasks:
            valid, reason = self._validate_task(task)

            if not valid:
                print(
                    f"⏭️ Skipping task: {reason}"
                )
                continue

            selected.append(task)

            if len(selected) >= limit:
                break

        return selected

    # ========================================================
    # 21. MAIN RUN
    # ========================================================

    def run(
        self,
        command,
        max_tasks=None,
        resume=False
    ):
        """
        🚀 MASTER ENTRY POINT

        Existing ai_service.py:
            SmartMain().run(command)

        bhi kaam karega.
        """
        command = str(command or "").strip()

        if not command:
            return "❌ Empty command."

        with self._lock:

            if self.is_running and not self.is_paused:
                return (
                    "⚠️ System already running.\n"
                    f"📌 Phase: {self.current_phase}\n"
                    f"📌 Platform: {self.current_platform}"
                )

            # ------------------------------------------------
            # Resume mode
            # ------------------------------------------------

            if resume or (
                self.resume_available
                and self.is_paused
            ):
                return self._resume_run()

            # ------------------------------------------------
            # Fresh run
            # ------------------------------------------------

            self.session_id = self._new_session_id()

            self.current_platform = self.detect_platform(
                command
            )

            self.current_task_index = 0
            self.current_task = None

            self.tasks_completed = 0
            self.tasks_failed = 0
            self.retry_count = 0
            self.total_earned = 0.0

            self.stop_requested = False
            self.is_paused = False
            self.human_handoff = False

            self.last_error = None
            self.last_result = None

            self.start_time = datetime.now()

            self.is_running = True

            self._set_phase(
                "starting",
                command
            )

        print("=" * 60)
        print("🧠 SMART WEBSITE MASTER v7.0")
        print("=" * 60)
        print(f"📌 Command: {command}")
        print(f"📌 Platform: {self.current_platform}")
        print(f"🆔 Session: {self.session_id}")
        print("=" * 60)

        try:

            # ------------------------------------------------
            # 1. Browser
            # ------------------------------------------------

            if not self._prepare_platform():

                self.is_running = False

                return (
                    "❌ Browser connection/navigation failed.\n"
                    f"📌 Error: {self.last_error}"
                )

            # ------------------------------------------------
            # 2. Login
            # ------------------------------------------------

            if not self._platform_login():

                if self.human_handoff:
                    return self._human_handoff_response()

                self.is_running = False

                return (
                    "❌ Platform login/setup failed.\n"
                    f"📌 Error: {self.last_error}"
                )

            # ------------------------------------------------
            # 3. Scan
            # ------------------------------------------------

            tasks = self._scan_tasks()

            if not tasks:

                self.is_running = False

                self._set_phase("no_tasks")

                self.clear_checkpoint()

                return (
                    f"❌ No "
                    f"{self._get_min_filled_percent():.0f}%+ "
                    f"tasks found on "
                    f"{self.current_platform}."
                )

            # ------------------------------------------------
            # 4. Select
            # ------------------------------------------------

            selected = self._select_tasks(
                tasks,
                max_tasks or self.DEFAULT_MAX_TASKS
            )

            if not selected:

                self.is_running = False

                self._set_phase("no_eligible_tasks")

                self.clear_checkpoint()

                return (
                    "❌ Tasks were found, "
                    "but none were eligible for execution."
                )

            # ------------------------------------------------
            # 5. Execute
            # ------------------------------------------------

            results = []

            for index, task in enumerate(
                selected,
                start=0
            ):

                if self._should_stop():
                    break

                self.current_task_index = index
                self.current_task = task

                self._save_checkpoint()

                print()
                print(
                    f"📌 TASK {index + 1}/"
                    f"{len(selected)}"
                )
                print(
                    f"📝 {task['title'][:150]}"
                )
                print(
                    f"📊 Filled: "
                    f"{task['percent']:.0f}%"
                )

                result = self.run_with_time_management(
                    task_description=task["title"],
                    estimated_seconds=(
                        self.DEFAULT_TASK_TIMEOUT
                    ),
                    task=task
                )

                results.append({
                    "task": task["title"],
                    "success": bool(result),
                    "percent": task["percent"]
                })

                self._save_checkpoint()

                # Human handoff
                if self.human_handoff:
                    return self._human_handoff_response(
                        results
                    )

                # Stop
                if self._should_stop():
                    break

                self._call_if_available(
                    self.utils,
                    "take_break"
                )

            # ------------------------------------------------
            # 6. Finalize
            # ------------------------------------------------

            return self._finalize_run(results)

        except KeyboardInterrupt:

            self.request_stop()

            return self._finalize_run(
                [],
                interrupted=True
            )

        except Exception as e:

            self.last_error = str(e)

            print(
                f"💥 MASTER ERROR: {e}"
            )

            self._save_checkpoint()

            self.is_running = False

            return (
                "❌ Master system error.\n"
                f"📌 {e}\n"
                "♻️ Checkpoint saved for recovery."
            )

    # ========================================================
    # 22. RESUME
    # ========================================================

    def _resume_run(self):
        """
        Previous checkpoint se resume.

        Browser closed tha toh browser state nahi,
        lekin automation state restore hoti hai.
        """
        if not self.current_platform:
            self.current_platform = "rapidworkers"

        self.stop_requested = False
        self.is_paused = False
        self.human_handoff = False
        self.is_running = True

        if not self.start_time:
            self.start_time = datetime.now()

        self._set_phase("resume")

        print("=" * 60)
        print("♻️ RESUMING SMART MASTER")
        print("=" * 60)
        print(
            f"📌 Platform: "
            f"{self.current_platform}"
        )
        print(
            f"📌 Task index: "
            f"{self.current_task_index}"
        )
        print(
            f"📌 Current task: "
            f"{self.current_task}"
        )
        print("=" * 60)

        try:

            # Browser dobara connect
            if not self._prepare_platform():
                self.is_running = False

                return (
                    "❌ Browser reconnect failed.\n"
                    "♻️ Checkpoint preserved."
                )

            # Login/setup
            if not self._platform_login():

                if self.human_handoff:
                    return self._human_handoff_response()

                self.is_running = False

                return (
                    "❌ Resume login/setup failed.\n"
                    "♻️ Checkpoint preserved."
                )

            # Dashboard re-scan
            tasks = self._scan_tasks()

            if not tasks:
                self.is_running = False

                return (
                    "⚠️ Resume successful, "
                    "but no eligible tasks are currently visible."
                )

            # Current task ke baad ke tasks
            start_index = max(
                0,
                self.current_task_index
            )

            remaining = tasks[start_index:]

            selected = self._select_tasks(
                remaining,
                self.DEFAULT_MAX_TASKS
            )

            results = []

            for task in selected:

                if self._should_stop():
                    break

                self.current_task = task

                result = self.run_with_time_management(
                    task["title"],
                    self.DEFAULT_TASK_TIMEOUT,
                    task
                )

                results.append({
                    "task": task["title"],
                    "success": bool(result),
                    "percent": task["percent"]
                })

                self._save_checkpoint()

                if self.human_handoff:
                    return self._human_handoff_response(
                        results
                    )

            return self._finalize_run(
                results,
                resumed=True
            )

        except Exception as e:

            self.last_error = str(e)

            self._save_checkpoint()

            self.is_running = False

            return (
                "❌ Resume failed.\n"
                f"📌 {e}\n"
                "♻️ Checkpoint preserved."
            )

    # ========================================================
    # 23. HUMAN HANDOFF RESPONSE
    # ========================================================

    def _human_handoff_response(self, results=None):

        self.is_running = False
        self.is_paused = True

        self._save_checkpoint()

        return (
            "👤 **Human action required**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Platform: {self.current_platform}\n"
            f"📌 Task: "
            f"{str(self.current_task)[:150]}\n"
            f"⚠️ Reason: {self.last_error or self.current_action}\n"
            "\n"
            "System ne unsafe verification ko bypass "
            "nahi kiya hai.\n"
            "Human verification complete hone ke baad "
            "resume kiya ja sakta hai.\n"
            "\n"
            "♻️ Checkpoint saved."
        )

    # ========================================================
    # 24. FINAL SUMMARY
    # ========================================================

    def _finalize_run(
        self,
        results,
        interrupted=False,
        resumed=False
    ):
        success_count = sum(
            1
            for item in results
            if item.get("success")
        )

        total_count = len(results)

        duration = self._elapsed_seconds()

        # Stop browser gracefully
        try:
            self._call_if_available(
                self.hands,
                "close"
            )
        except Exception:
            pass

        self.is_running = False

        if interrupted or self.stop_requested:
            self._set_phase("stopped")

            # IMPORTANT:
            # Stop par checkpoint clear nahi hota.
            self._save_checkpoint()

            return (
                "🛑 **Automation stopped**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📌 Platform: {self.current_platform}\n"
                f"📌 Completed: {self.tasks_completed}\n"
                f"📌 Failed: {self.tasks_failed}\n"
                f"💰 Earned: ${self.total_earned:.2f}\n"
                "♻️ Checkpoint saved.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )

        self._set_phase("completed")

        # Successful normal completion
        self.clear_checkpoint()

        success_rate = (
            success_count / total_count * 100
            if total_count
            else 0
        )

        mode = "Resume" if resumed else "Fresh"

        return (
            "✅ **Task Summary**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 Mode: {mode}\n"
            f"📌 Platform: {self.current_platform}\n"
            f"📌 Tasks: "
            f"{success_count}/{total_count} completed\n"
            f"❌ Failed: {self.tasks_failed}\n"
            f"💰 Total Earned: "
            f"${self.total_earned:.2f}\n"
            f"⏱️ Duration: "
            f"{duration // 60} minutes\n"
            f"📊 Success Rate: "
            f"{success_rate:.0f}%\n"
            f"🔄 Retries: {self.retry_count}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    # ========================================================
    # 25. STATUS
    # ========================================================

    def get_status(self):
        """
        AI / app.py / popup ke liye structured status.
        """
        with self._lock:

            return {
                "version": self.VERSION,

                "status": (
                    "running"
                    if self.is_running
                    else (
                        "paused"
                        if self.is_paused
                        else "idle"
                    )
                ),

                "phase": self.current_phase,
                "action": self.current_action,

                "platform": self.current_platform,

                "session_id": self.session_id,

                "current_task": self.current_task,

                "current_task_index": (
                    self.current_task_index
                ),

                "tasks_completed": (
                    self.tasks_completed
                ),

                "tasks_failed": (
                    self.tasks_failed
                ),

                "retry_count": (
                    self.retry_count
                ),

                "total_earned": (
                    f"${self.total_earned:.2f}"
                ),

                "human_handoff": (
                    self.human_handoff
                ),

                "requires_human": (
                    self.human_handoff
                ),

                "resume_available": (
                    self.resume_available
                ),

                "last_error": self.last_error,

                "memory_size": len(
                    self.memory.get(
                        "tasks",
                        []
                    )
                ),

                "uptime": self._elapsed_seconds()
            }

    # ========================================================
    # 26. COMMAND CONTROL API
    # ========================================================

    def control(self, action):
        """
        Generic control layer.

        Supported:
            status
            pause
            resume
            stop
        """
        action = str(
            action or ""
        ).strip().lower()

        if action == "status":
            return self.get_status()

        if action == "pause":
            self.pause("Manual pause")
            return self.get_status()

        if action == "resume":
            if self.resume():
                return self._resume_run()

            return {
                "status": "idle",
                "message": "No resume checkpoint available."
            }

        if action == "stop":
            self.request_stop()

            return self.get_status()

        return {
            "status": "error",
            "message": (
                "Unknown control action"
            )
        }


# ============================================================
# 27. TESTING
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("🧠 SMART WEBSITE MASTER v7.0")
    print("🧪 TEST MODE")
    print("=" * 60)

    system = SmartMain()

    print()
    print("📊 Initial Status:")
    print(
        json.dumps(
            system.get_status(),
            indent=2,
            ensure_ascii=False
        )
    )

    print()
    print("🔎 Platform detection tests:")

    tests = [
        "RapidWorkers pe jao",
        "TimeBucks open karo",
        "FreeCash task karo",
        "Swagbucks kholo",
        "ySense open karo",
        "PrizeRebel task",
        "GrabPoints kholo"
    ]

    for command in tests:
        print(
            f"  {command} "
            f"→ "
            f"{system.detect_platform(command)}"
        )

    print()
    print("✅ Smart Website Master loaded.")
    print(
        "ℹ️ Actual website execution "
        "SmartHands/browser bridge par depend karega."
    )
