# ============================================================
# smart_hands.py — SMART BROWSER EXECUTION ENGINE v15.0
# ============================================================
# PURPOSE:
#   Reliable browser automation engine for SmartMain v7+
#
# FLOW:
#   CONNECT
#      ↓
#   OBSERVE
#      ↓
#   ACT
#      ↓
#   VERIFY
#      ↓
#   RETRY / HUMAN HANDOFF
#      ↓
#   RESULT
#
# COMPATIBILITY:
#   main.py v7.0
#   ai_service.py
#   Flask backend
#   Kiwi/Extension bridge architecture
#
# SAFETY:
#   - No CAPTCHA bypass
#   - No OTP/security bypass
#   - No anti-detection tricks
#   - No fake task completion
#   - No infinite retry loops
# ============================================================

import json
import time
import urllib.request
import urllib.error
import subprocess
import shutil
import os
import sys
import socket
import zipfile
import atexit
import signal
import threading
import queue
import re
import hashlib
import tempfile
from datetime import datetime
from websocket import create_connection

from config import *


# ============================================================
# LOGGER
# ============================================================

class SmartLogger:

    LEVELS = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    COLORS = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARN": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[95m",
        "RESET": "\033[0m",
    }

    def __init__(
        self,
        name="SmartHands",
        log_file="smart_hands.log",
        level="INFO"
    ):
        self.name = name
        self.log_file = log_file
        self.level = self.LEVELS.get(level, 20)
        self.lock = threading.Lock()
        self.max_log_size = 5 * 1024 * 1024

        directory = os.path.dirname(log_file)

        if directory:
            os.makedirs(directory, exist_ok=True)

        self._rotate_if_needed()

    def _rotate_if_needed(self):
        try:
            if (
                os.path.exists(self.log_file)
                and os.path.getsize(self.log_file) > self.max_log_size
            ):
                old = self.log_file + ".old"

                if os.path.exists(old):
                    os.remove(old)

                os.rename(self.log_file, old)
        except Exception:
            pass

    def _log(self, level, msg):

        if self.LEVELS.get(level, 20) < self.level:
            return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        color = self.COLORS.get(level, "")
        reset = self.COLORS["RESET"]

        line = f"[{level}] [{timestamp}] {msg}"

        print(f"{color}{line}{reset}")

        try:
            with self.lock:
                self._rotate_if_needed()

                with open(
                    self.log_file,
                    "a",
                    encoding="utf-8"
                ) as f:
                    f.write(line + "\n")
        except Exception:
            pass

    def debug(self, msg):
        self._log("DEBUG", msg)

    def info(self, msg):
        self._log("INFO", msg)

    def warn(self, msg):
        self._log("WARN", msg)

    def error(self, msg):
        self._log("ERROR", msg)

    def critical(self, msg):
        self._log("CRITICAL", msg)


logger = SmartLogger()


# ============================================================
# SMART HANDS
# ============================================================

class SmartHands:
    """
    SMART BROWSER EXECUTION ENGINE v15.0

    Main responsibilities:

        Browser connection
        Page navigation
        DOM observation
        Element finding
        Clicking
        Typing
        Text extraction
        Waiting
        Task execution
        Verification
        Retry
        Human handoff
        Session state
        Metrics
        Checkpoint support
    """

    VERSION = "15.0.0"

    DEFAULT_TIMEOUT = 15
    PAGE_TIMEOUT = 20
    ACTION_TIMEOUT = 15

    HUMAN_INDICATORS = [
        "captcha",
        "recaptcha",
        "hcaptcha",
        "verify you are human",
        "verification required",
        "security check",
        "one-time password",
        "otp",
        "two-factor",
        "2fa",
        "identity verification",
        "payment verification",
    ]

    PLATFORM_URLS = {
        "rapidworkers": "https://rapidworkers.com",
        "timebucks": "https://www.timebucks.com",
        "freecash": "https://www.freecash.com",
        "swagbucks": "https://www.swagbucks.com",
        "ysense": "https://www.ysense.com",
        "prizerebel": "https://www.prizerebel.com",
        "grabpoints": "https://www.grabpoints.com",
    }

    # --------------------------------------------------------
    # INIT
    # --------------------------------------------------------

    def __init__(
        self,
        headless=True,
        proxy_list=None,
        captcha_api_key=None,
        use_ai=False,
        max_parallel=5,
        enable_network=False
    ):

        self.ws = None
        self.is_connected = False
        self.page_id = None

        self.chrome_process = None
        self.retry_count = 0
        self.max_retries = 3

        self.browser_path = None
        self.temp_profile = None

        self.port = self._find_free_port()

        self.download_attempted = False

        self.headless = bool(headless)

        # Kept for compatibility.
        # Not used for bypass/evasion.
        self.proxy_list = proxy_list or []
        self.current_proxy = None
        self.captcha_api_key = captcha_api_key

        self.use_ai = use_ai
        self.max_parallel = max(1, int(max_parallel))

        self.enable_network = enable_network
        self.network_data = []
        self.tabs = []

        self.state_file = "smart_hands_state.json"
        self.memory_file = "khatarnak_memory.json"
        self.optimization_file = "optimization_cache.json"
        self.checkpoint_file = "smart_hands_checkpoint.json"

        self.session_cookies = {}
        self.current_ua = None

        self.cloud_browser_fallback = os.environ.get(
            "BROWSERLESS_API_KEY"
        )

        self.task_queue = queue.Queue()
        self.results = []

        self.metrics = {
            "version": self.VERSION,
            "launch_time": 0,
            "last_action": None,
            "last_action_time": 0,
            "task_times": [],
            "success_count": 0,
            "fail_count": 0,
            "success_rate": 0,
            "actions": 0,
            "reconnects": 0,
        }

        self.fail_count = 0
        self.success_count = 0

        self.stop_requested = False
        self.pause_requested = False
        self.closed = False

        self._ws_lock = threading.RLock()
        self._state_lock = threading.RLock()

        self.memory = self._load_memory()
        self.optimization_data = self._load_optimization_data()

        # Safe stable user agent.
        self.current_ua = (
            self._load_saved_ua()
            or "Mozilla/5.0 "
               "(Windows NT 10.0; Win64; x64) "
               "AppleWebKit/537.36 "
               "(KHTML, like Gecko) "
               "Chrome/120.0.0.0 Safari/537.36"
        )

        self._load_session()

        # ----------------------------------------------------
        # Browser discovery
        # ----------------------------------------------------

        self._fix_library_path()

        self.browser_path = self._find_system_chrome()

        if not self.browser_path:
            self.browser_path = self._find_static_chrome()

        if not self.browser_path:
            logger.warn(
                "Chrome/Chromium not found locally. "
                "Automatic download can be attempted when connect() runs."
            )

        self._start_metrics_thread()

        atexit.register(self.close)

        logger.info(
            f"SmartHands v{self.VERSION} initialized."
        )

    # ========================================================
    # GENERIC RESULT
    # ========================================================

    def _result(
        self,
        success,
        action,
        data=None,
        error=None,
        requires_human=False
    ):

        return {
            "success": bool(success),
            "action": action,
            "url": self._current_url(),
            "title": self._current_title(),
            "data": data,
            "error": error,
            "requires_human": bool(requires_human),
            "timestamp": datetime.now().isoformat(),
        }

    # ========================================================
    # URL / PAGE HELPERS
    # ========================================================

    def _current_url(self):

        try:
            result = self.send_command(
                "Runtime.evaluate",
                {
                    "expression": "location.href",
                    "returnByValue": True
                },
                retry=False
            )

            return (
                result
                .get("result", {})
                .get("result", {})
                .get("value", "")
            )
        except Exception:
            return ""

    def _current_title(self):

        try:
            result = self.send_command(
                "Runtime.evaluate",
                {
                    "expression": "document.title",
                    "returnByValue": True
                },
                retry=False
            )

            return (
                result
                .get("result", {})
                .get("result", {})
                .get("value", "")
            )
        except Exception:
            return ""

    # ========================================================
    # LIBRARY PATH
    # ========================================================

    def _fix_library_path(self):

        paths = [
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib",
            "/usr/local/lib",
            "/lib",
            "/lib64",
            "/usr/lib/chromium",
            "/usr/lib/chromium-browser",
        ]

        valid = [
            p for p in paths
            if os.path.exists(p)
        ]

        if valid:

            old = os.environ.get(
                "LD_LIBRARY_PATH",
                ""
            )

            combined = valid

            if old:
                combined.append(old)

            os.environ["LD_LIBRARY_PATH"] = ":".join(
                dict.fromkeys(combined)
            )

            logger.debug(
                f"Library paths available: {len(valid)}"
            )

    # ========================================================
    # FIND CHROME
    # ========================================================

    def _find_system_chrome(self):

        paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium",
            "/opt/google/chrome/chrome",
            "/usr/local/bin/google-chrome",
            "/usr/bin/chrome",
        ]

        for path in paths:

            if (
                os.path.exists(path)
                and os.access(path, os.X_OK)
            ):
                logger.info(
                    f"System browser found: {path}"
                )
                return path

        for command in [
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "chrome",
        ]:

            found = shutil.which(command)

            if found:
                logger.info(
                    f"Browser found in PATH: {found}"
                )
                return found

        return None

    # ========================================================
    # STATIC CHROME
    # ========================================================

    def _find_static_chrome(self):

        candidates = [
            os.path.join(
                os.getcwd(),
                "static_chrome",
                "chrome"
            ),
            os.path.join(
                os.getcwd(),
                "chrome-bin",
                "chrome-linux64",
                "chrome"
            ),
            os.path.join(
                os.getcwd(),
                "chrome-bin",
                "chrome"
            ),
        ]

        for path in candidates:

            if (
                os.path.exists(path)
                and os.access(path, os.X_OK)
            ):

                logger.info(
                    f"Cached browser found: {path}"
                )

                return path

        return None

    # ========================================================
    # OPTIONAL BROWSER DOWNLOAD
    # ========================================================

    def _download_chrome_enhanced(self):

        chrome_dir = os.path.join(
            os.getcwd(),
            "chrome-bin"
        )

        os.makedirs(
            chrome_dir,
            exist_ok=True
        )

        cached = self._find_static_chrome()

        if cached:
            return cached

        # One bounded attempt set only.
        # No infinite loops.
        mirrors = [
            (
                "https://storage.googleapis.com/"
                "chrome-for-testing-public/"
                "126.0.6478.61/linux64/"
                "chrome-linux64.zip"
            ),
        ]

        zip_path = os.path.join(
            chrome_dir,
            "chrome.zip"
        )

        for url in mirrors:

            try:

                logger.info(
                    "Attempting Chrome download..."
                )

                urllib.request.urlretrieve(
                    url,
                    zip_path
                )

                if not zipfile.is_zipfile(
                    zip_path
                ):
                    raise RuntimeError(
                        "Downloaded file is not a valid ZIP."
                    )

                with zipfile.ZipFile(
                    zip_path,
                    "r"
                ) as zf:
                    zf.extractall(chrome_dir)

                try:
                    os.remove(zip_path)
                except Exception:
                    pass

                found = self._find_static_chrome()

                if found:
                    logger.info(
                        f"Browser downloaded: {found}"
                    )
                    return found

            except Exception as e:

                logger.warn(
                    f"Browser download failed: {e}"
                )

                try:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                except Exception:
                    pass

        return None

    # ========================================================
    # PORT
    # ========================================================

    def _find_free_port(self):

        for port in range(9222, 9500):

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            try:

                sock.settimeout(0.2)

                result = sock.connect_ex(
                    ("127.0.0.1", port)
                )

                if result != 0:
                    return port

            except Exception:
                pass

            finally:
                try:
                    sock.close()
                except Exception:
                    pass

        return 9222

    # ========================================================
    # LAUNCH
    # ========================================================

    def _launch_chrome(self):

        if not self.browser_path:

            self.browser_path = (
                self._download_chrome_enhanced()
            )

        if not self.browser_path:

            logger.error(
                "No Chrome/Chromium executable available."
            )

            return False

        if self.browser_path == "cloud":

            return self._connect_cloud_browser()

        if not os.path.exists(
            self.browser_path
        ):

            logger.error(
                "Browser executable does not exist."
            )

            return False

        base_dir = (
            tempfile.gettempdir()
            if sys.platform.startswith("linux")
            else os.getcwd()
        )

        self.temp_profile = os.path.join(
            base_dir,
            f"smart_hands_profile_{os.getpid()}_"
            f"{int(time.time())}"
        )

        os.makedirs(
            self.temp_profile,
            exist_ok=True
        )

        cmd = [
            self.browser_path,

            f"--remote-debugging-port={self.port}",

            f"--user-data-dir={self.temp_profile}",

            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",

            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",

            "--no-first-run",
            "--no-default-browser-check",

            "--window-size=1280,720",
        ]

        if self.headless:

            cmd.extend([
                "--headless=new",
                "--disable-gpu",
            ])

        env = os.environ.copy()

        if sys.platform.startswith("linux"):
            env.setdefault(
                "DISPLAY",
                ":99"
            )

        debug_path = os.path.join(
            os.getcwd(),
            "chrome_debug.log"
        )

        try:

            debug_file = open(
                debug_path,
                "a",
                encoding="utf-8"
            )

            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=debug_file,
                stderr=debug_file,
                shell=False,
                start_new_session=True,
                env=env,
            )

            if self._wait_for_port(
                timeout=20
            ):

                self.metrics[
                    "launch_time"
                ] = time.time()

                try:
                    debug_file.close()
                except Exception:
                    pass

                logger.info(
                    "Chrome launched successfully."
                )

                return True

            try:
                debug_file.close()
            except Exception:
                pass

            self._kill_process()

            logger.error(
                "Chrome debugging port did not open."
            )

            return False

        except Exception as e:

            logger.error(
                f"Chrome launch failed: {e}"
            )

            try:
                debug_file.close()
            except Exception:
                pass

            self._kill_process()

            return False

    # ========================================================
    # KILL
    # ========================================================

    def _kill_process(self):

        process = self.chrome_process

        if not process:
            return

        try:

            if (
                sys.platform != "win32"
                and process.poll() is None
            ):

                try:
                    os.killpg(
                        os.getpgid(process.pid),
                        signal.SIGTERM
                    )
                except Exception:
                    process.terminate()

            elif process.poll() is None:

                process.terminate()

            try:
                process.wait(timeout=3)
            except Exception:

                try:
                    process.kill()
                except Exception:
                    pass

        except Exception:
            pass

        self.chrome_process = None

    # ========================================================
    # WAIT PORT
    # ========================================================

    def _wait_for_port(self, timeout=20):

        start = time.time()

        while (
            time.time() - start
            < timeout
        ):

            try:

                with urllib.request.urlopen(
                    f"http://127.0.0.1:{self.port}/json",
                    timeout=0.5
                ):
                    return True

            except Exception:
                time.sleep(0.15)

        return False

    def _is_port_open(self):

        try:

            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/json",
                timeout=1
            ):
                return True

        except Exception:
            return False

    # ========================================================
    # CLOUD BROWSER
    # ========================================================

    def _connect_cloud_browser(self):

        if not self.cloud_browser_fallback:
            return False

        try:

            import requests

            response = requests.get(
                "https://chrome.browserless.io/"
                "json/version",
                params={
                    "token":
                    self.cloud_browser_fallback
                },
                timeout=10
            )

            if response.status_code != 200:
                return False

            data = response.json()

            ws_url = data.get(
                "webSocketDebuggerUrl"
            )

            if not ws_url:
                return False

            self.ws = create_connection(
                ws_url,
                timeout=15
            )

            self.is_connected = True
            self.page_id = "cloud"

            logger.info(
                "Connected to remote browser."
            )

            return True

        except Exception as e:

            logger.error(
                f"Remote browser connection failed: {e}"
            )

            return False

    # ========================================================
    # CONNECT
    # ========================================================

    def connect(self, retry=True):

        logger.info(
            "Connecting to browser..."
        )

        self.closed = False
        self._load_session()

        if not self._is_port_open():

            if not self._launch_chrome():

                if (
                    retry
                    and self.retry_count
                    < self.max_retries
                ):

                    self.retry_count += 1
                    self.metrics[
                        "reconnects"
                    ] += 1

                    time.sleep(
                        min(
                            2 ** self.retry_count,
                            8
                        )
                    )

                    return self.connect(
                        retry=True
                    )

                if self.cloud_browser_fallback:
                    return self._connect_cloud_browser()

                return False

        try:

            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/json",
                timeout=3
            ) as response:

                tabs = json.loads(
                    response.read().decode()
                )

            pages = [
                t for t in tabs
                if t.get("type") == "page"
            ]

            if not pages:

                logger.info(
                    "No page found; creating new page."
                )

                try:

                    request = urllib.request.Request(
                        f"http://127.0.0.1:{self.port}/json/new",
                        method="PUT"
                    )

                    with urllib.request.urlopen(
                        request,
                        timeout=3
                    ) as response:

                        page = json.loads(
                            response.read().decode()
                        )

                except Exception:

                    return False

            else:
                page = pages[0]

            ws_url = page.get(
                "webSocketDebuggerUrl"
            )

            if not ws_url:
                return False

            self.ws = create_connection(
                ws_url,
                timeout=15
            )

            self.page_id = page.get("id")
            self.is_connected = True
            self.retry_count = 0

            self._enable_page()

            logger.info(
                f"Browser connected. Page ID: {self.page_id}"
            )

            return True

        except Exception as e:

            logger.error(
                f"Connection failed: {e}"
            )

            self.is_connected = False

            if retry:
                time.sleep(1)

                if (
                    self.retry_count
                    < self.max_retries
                ):

                    self.retry_count += 1

                    return self.connect(
                        retry=True
                    )

            return False

    # ========================================================
    # ENABLE PAGE
    # ========================================================

    def _enable_page(self):

        try:
            self.send_command(
                "Runtime.enable",
                retry=False
            )
        except Exception:
            pass

        try:
            self.send_command(
                "Page.enable",
                retry=False
            )
        except Exception:
            pass

        if self.enable_network:

            try:
                self.send_command(
                    "Network.enable",
                    retry=False
                )
            except Exception:
                pass

    # ========================================================
    # ENSURE CONNECTION
    # ========================================================

    def ensure_connection(self):

        if (
            not self.is_connected
            or not self.ws
        ):

            return self.connect()

        try:

            result = self.send_command(
                "Browser.getVersion",
                retry=False
            )

            if "error" in result:

                raise RuntimeError(
                    "Browser health check failed"
                )

            return True

        except Exception:

            self.is_connected = False

            try:
                self.ws.close()
            except Exception:
                pass

            self.ws = None

            return self.connect()

    # ========================================================
    # CDP COMMAND
    # ========================================================

    def send_command(
        self,
        method,
        params=None,
        retry=True
    ):

        if params is None:
            params = {}

        if (
            not self.is_connected
            or not self.ws
        ):

            if not self.connect(
                retry=retry
            ):
                return {
                    "error": {
                        "message":
                        "Browser not connected"
                    }
                }

        command_id = int(
            time.time() * 1000000
        )

        message = {
            "id": command_id,
            "method": method,
            "params": params
        }

        try:

            with self._ws_lock:

                self.ws.send(
                    json.dumps(message)
                )

                deadline = (
                    time.time()
                    + self.DEFAULT_TIMEOUT
                )

                while time.time() < deadline:

                    raw = self.ws.recv()

                    if not raw:
                        continue

                    response = json.loads(raw)

                    # Ignore unrelated CDP events.
                    if response.get("id") != command_id:
                        continue

                    self.metrics[
                        "actions"
                    ] += 1

                    self.metrics[
                        "last_action"
                    ] = method

                    self.metrics[
                        "last_action_time"
                    ] = time.time()

                    return response

                raise TimeoutError(
                    f"CDP timeout: {method}"
                )

        except Exception as e:

            logger.warn(
                f"CDP command failed: {method}: {e}"
            )

            self.is_connected = False

            try:
                self.ws.close()
            except Exception:
                pass

            self.ws = None

            if retry:

                time.sleep(0.5)

                if self.connect(
                    retry=False
                ):

                    return self.send_command(
                        method,
                        params,
                        retry=False
                    )

            return {
                "error": {
                    "message": str(e)
                }
            }

    # ========================================================
    # SAFE JS STRING
    # ========================================================

    @staticmethod
    def _js_string(value):

        return json.dumps(
            str(value),
            ensure_ascii=False
        )

    # ========================================================
    # EVALUATE
    # ========================================================

    def _evaluate(
        self,
        expression,
        timeout=None
    ):

        if timeout is None:
            timeout = self.ACTION_TIMEOUT

        result = self.send_command(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            }
        )

        if "error" in result:
            return None

        runtime_result = (
            result
            .get("result", {})
            .get("result", {})
        )

        if runtime_result.get(
            "subtype"
        ) == "error":

            return None

        return runtime_result.get(
            "value"
        )

    # ========================================================
    # PAGE READY
    # ========================================================

    def _wait_for_load(
        self,
        timeout=15
    ):

        start = time.time()

        while (
            time.time() - start
            < timeout
        ):

            state = self._evaluate(
                "document.readyState"
            )

            if state in (
                "interactive",
                "complete"
            ):
                return True

            time.sleep(0.2)

        return False

    # ========================================================
    # HUMAN HANDOFF DETECTION
    # ========================================================

    def _requires_human(self):

        text = self.get_page_text()

        if not text:
            return False

        lower = text.lower()

        for indicator in self.HUMAN_INDICATORS:

            if indicator in lower:

                logger.warn(
                    f"Human verification detected: {indicator}"
                )

                return True

        return False

    def detect_indicators(self):

        text = self.get_page_text()

        lower = text.lower()

        found = {
            "captcha": [],
            "login": [],
            "security": [],
            "payment": [],
            "otp": [],
            "errors": [],
        }

        groups = {
            "captcha": [
                "captcha",
                "recaptcha",
                "hcaptcha"
            ],
            "login": [
                "sign in",
                "login",
                "log in"
            ],
            "security": [
                "security check",
                "verify you are human",
                "identity verification"
            ],
            "payment": [
                "payment verification",
                "billing verification"
            ],
            "otp": [
                "otp",
                "one-time password",
                "two-factor",
                "2fa"
            ],
            "errors": [
                "error",
                "something went wrong",
                "access denied"
            ],
        }

        for group, words in groups.items():

            for word in words:

                if word in lower:
                    found[group].append(word)

        requires_human = bool(
            found["captcha"]
            or found["security"]
            or found["payment"]
            or found["otp"]
        )

        return self._result(
            True,
            "detect_indicators",
            {
                "indicators": found,
                "requires_human": requires_human,
            },
            requires_human=requires_human
        )

    # ========================================================
    # NAVIGATE
    # ========================================================

    def navigate(self, url):

        if not isinstance(url, str):
            return self._result(
                False,
                "navigate",
                error="Invalid URL"
            )

        url = url.strip()

        if not re.match(
            r"^https?://",
            url,
            re.IGNORECASE
        ):
            return self._result(
                False,
                "navigate",
                error="Only http/https URLs are allowed."
            )

        logger.info(
            f"Navigate: {url}"
        )

        result = self.send_command(
            "Page.navigate",
            {
                "url": url
            }
        )

        if "error" in result:

            return self._result(
                False,
                "navigate",
                error=result["error"]
            )

        self._wait_for_load(
            self.PAGE_TIMEOUT
        )

        self._save_session()

        return self._result(
            True,
            "navigate",
            {
                "url": url
            }
        )

    # ========================================================
    # PAGE TEXT
    # ========================================================

    def get_text(self):

        value = self._evaluate(
            """
            (() => {
                try {
                    return document.body
                        ? document.body.innerText
                        : "";
                } catch(e) {
                    return "";
                }
            })()
            """
        )

        return str(value or "")

    def get_page_text(self):

        return self.get_text()

    # ========================================================
    # PAGE INFO
    # ========================================================

    def get_page_info(self):

        value = self._evaluate(
            """
            (() => ({
                url: location.href,
                title: document.title || "",
                ready_state: document.readyState,
                forms: document.forms.length,
                links: document.links.length,
                images: document.images.length,
                inputs: document.querySelectorAll(
                    "input, textarea, select"
                ).length,
                buttons: document.querySelectorAll(
                    "button, [role='button']"
                ).length
            }))()
            """
        )

        return self._result(
            True,
            "get_page_info",
            value or {}
        )

    # ========================================================
    # SCAN PAGE
    # ========================================================

    def scan_page(self):

        value = self._evaluate(
            """
            (() => {
                const visible = el => {
                    const s = getComputedStyle(el);
                    const r = el.getBoundingClientRect();

                    return (
                        s.display !== "none" &&
                        s.visibility !== "hidden" &&
                        r.width > 0 &&
                        r.height > 0
                    );
                };

                const clean = el => ({
                    tag: el.tagName.toLowerCase(),
                    text: (
                        el.innerText ||
                        el.value ||
                        el.getAttribute("aria-label") ||
                        ""
                    ).trim().slice(0, 300),
                    id: el.id || "",
                    name: el.getAttribute("name") || "",
                    placeholder:
                        el.getAttribute("placeholder") || "",
                    type:
                        el.getAttribute("type") || "",
                    href:
                        el.href || ""
                });

                const buttons = [
                    ...document.querySelectorAll(
                        "button, a, [role='button'], input[type='submit']"
                    )
                ]
                .filter(visible)
                .slice(0, 150)
                .map(clean);

                const inputs = [
                    ...document.querySelectorAll(
                        "input, textarea, select"
                    )
                ]
                .filter(visible)
                .slice(0, 150)
                .map(clean);

                return {
                    url: location.href,
                    title: document.title || "",
                    text: (
                        document.body
                        ? document.body.innerText
                        : ""
                    ).slice(0, 20000),
                    buttons,
                    inputs
                };
            })()
            """
        )

        return self._result(
            True,
            "scan_page",
            value or {}
        )

    # ========================================================
    # EXTRACT TEXT
    # ========================================================

    def extract_text(
        self,
        selector=None
    ):

        if selector:

            selector_js = self._js_string(
                selector
            )

            expression = f"""
            (() => {{
                const el = document.querySelector(
                    {selector_js}
                );

                return el
                    ? (el.innerText || el.textContent || "")
                    : "";
            }})()
            """

        else:

            expression = """
            document.body
                ? document.body.innerText
                : ""
            """

        value = self._evaluate(
            expression
        )

        return self._result(
            bool(value is not None),
            "extract_text",
            str(value or "")[:30000]
        )

    # ========================================================
    # FIND BY TEXT
    # ========================================================

    def find_by_text(self, text):

        needle = self._js_string(
            text
        )

        expression = f"""
        (() => {{
            const needle = {needle}.toLowerCase();

            const elements = [
                ...document.querySelectorAll(
                    "button, a, input, textarea, "
                    "select, [role='button'], "
                    "[role='link'], label"
                )
            ];

            const visible = el => {{
                const r = el.getBoundingClientRect();
                const s = getComputedStyle(el);

                return (
                    r.width > 0 &&
                    r.height > 0 &&
                    s.display !== "none" &&
                    s.visibility !== "hidden"
                );
            }};

            return elements
                .filter(visible)
                .filter(el => {{
                    const value = (
                        el.innerText ||
                        el.value ||
                        el.getAttribute("aria-label") ||
                        ""
                    ).toLowerCase();

                    return value.includes(needle);
                }})
                .slice(0, 20)
                .map(el => ({{
                    tag: el.tagName.toLowerCase(),
                    text: (
                        el.innerText ||
                        el.value ||
                        el.getAttribute("aria-label") ||
                        ""
                    ).trim().slice(0, 300),
                    id: el.id || "",
                    name: el.getAttribute("name") || "",
                    placeholder:
                        el.getAttribute("placeholder") || ""
                }}));
        }})()
        """

        data = self._evaluate(
            expression
        )

        return self._result(
            True,
            "find_by_text",
            data or []
        )

    # ========================================================
    # FIND ELEMENT
    # ========================================================

    def find_element(
        self,
        selector
    ):

        selector_js = self._js_string(
            selector
        )

        expression = f"""
        (() => {{
            const el = document.querySelector(
                {selector_js}
            );

            if (!el) {{
                return null;
            }}

            const r = el.getBoundingClientRect();

            return {{
                tag: el.tagName.toLowerCase(),
                text: (
                    el.innerText ||
                    el.value ||
                    el.getAttribute("aria-label") ||
                    ""
                ).trim().slice(0, 500),
                id: el.id || "",
                name: el.getAttribute("name") || "",
                placeholder:
                    el.getAttribute("placeholder") || "",
                visible:
                    r.width > 0 &&
                    r.height > 0
            }};
        }})()
        """

        data = self._evaluate(
            expression
        )

        return self._result(
            bool(data),
            "find_element",
            data,
            error=None if data else "Element not found"
        )

    # ========================================================
    # CLICK
    # ========================================================

    def click(self, selector):

        logger.info(
            f"Click selector: {selector}"
        )

        selector_js = self._js_string(
            selector
        )

        expression = f"""
        (() => {{
            const el = document.querySelector(
                {selector_js}
            );

            if (!el) {{
                return {{
                    success: false,
                    error: "Element not found"
                }};
            }}

            const r = el.getBoundingClientRect();

            if (r.width <= 0 || r.height <= 0) {{
                return {{
                    success: false,
                    error: "Element is not visible"
                }};
            }}

            el.scrollIntoView({{
                block: "center",
                inline: "center"
            }});

            el.click();

            return {{
                success: true
            }};
        }})()
        """

        data = self._evaluate(
            expression
        )

        if not data or not data.get(
            "success"
        ):

            return self._result(
                False,
                "click",
                data,
                error=(
                    data.get("error")
                    if isinstance(data, dict)
                    else "Click failed"
                )
            )

        time.sleep(0.5)

        return self._result(
            True,
            "click",
            data
        )

    # ========================================================
    # CLICK BY TEXT
    # ========================================================

    def click_by_text(self, text):

        logger.info(
            f"Click text: {text}"
        )

        text_js = self._js_string(
            text
        )

        expression = f"""
        (() => {{
            const needle = {text_js}.toLowerCase();

            const elements = [
                ...document.querySelectorAll(
                    "button, a, "
                    "input[type='button'], "
                    "input[type='submit'], "
                    "[role='button'], "
                    "[role='link']"
                )
            ];

            const visible = el => {{
                const r = el.getBoundingClientRect();

                return (
                    r.width > 0 &&
                    r.height > 0
                );
            }};

            const match = elements.find(el => {{
                if (!visible(el)) return false;

                const value = (
                    el.innerText ||
                    el.value ||
                    el.getAttribute("aria-label") ||
                    ""
                ).trim().toLowerCase();

                return (
                    value === needle ||
                    value.includes(needle)
                );
            }});

            if (!match) {{
                return {{
                    success: false,
                    error: "Text element not found"
                }};
            }}

            match.scrollIntoView({{
                block: "center"
            }});

            match.click();

            return {{
                success: true,
                text: (
                    match.innerText ||
                    match.value ||
                    ""
                ).trim()
            }};
        }})()
        """

        data = self._evaluate(
            expression
        )

        if not data or not data.get(
            "success"
        ):

            return self._result(
                False,
                "click_by_text",
                data,
                error=(
                    data.get("error")
                    if isinstance(data, dict)
                    else "Click failed"
                )
            )

        time.sleep(0.5)

        return self._result(
            True,
            "click_by_text",
            data
        )

    # ========================================================
    # TYPE TEXT
    # ========================================================

    def type_text(
        self,
        selector,
        text
    ):

        logger.info(
            f"Type into: {selector}"
        )

        selector_js = self._js_string(
            selector
        )

        text_js = self._js_string(
            text
        )

        expression = f"""
        (() => {{
            const el = document.querySelector(
                {selector_js}
            );

            if (!el) {{
                return {{
                    success: false,
                    error: "Element not found"
                }};
            }}

            el.focus();

            const value = {text_js};

            const prototype =
                Object.getPrototypeOf(el);

            const descriptor =
                Object.getOwnPropertyDescriptor(
                    prototype,
                    "value"
                );

            if (
                descriptor &&
                descriptor.set
            ) {{
                descriptor.set.call(
                    el,
                    value
                );
            }} else {{
                el.value = value;
            }}

            el.dispatchEvent(
                new Event(
                    "input",
                    {{ bubbles: true }}
                )
            );

            el.dispatchEvent(
                new Event(
                    "change",
                    {{ bubbles: true }}
                )
            );

            return {{
                success: true
            }};
        }})()
        """

        data = self._evaluate(
            expression
        )

        if not data or not data.get(
            "success"
        ):

            return self._result(
                False,
                "type_text",
                data,
                error=(
                    data.get("error")
                    if isinstance(data, dict)
                    else "Typing failed"
                )
            )

        return self._result(
            True,
            "type_text",
            {
                "characters":
                len(str(text))
            }
        )

    # ========================================================
    # TYPE BY PLACEHOLDER
    # ========================================================

    def type_by_placeholder(
        self,
        placeholder,
        text
    ):

        placeholder_js = self._js_string(
            placeholder
        )

        text_js = self._js_string(
            text
        )

        expression = f"""
        (() => {{
            const needle =
                {placeholder_js}.toLowerCase();

            const elements = [
                ...document.querySelectorAll(
                    "input, textarea"
                )
            ];

            const el = elements.find(
                x => (
                    x.placeholder || ""
                ).toLowerCase().includes(
                    needle
                )
            );

            if (!el) {{
                return {{
                    success: false,
                    error:
                        "Placeholder not found"
                }};
            }}

            el.focus();

            const value = {text_js};

            const prototype =
                Object.getPrototypeOf(el);

            const descriptor =
                Object.getOwnPropertyDescriptor(
                    prototype,
                    "value"
                );

            if (
                descriptor &&
                descriptor.set
            ) {{
                descriptor.set.call(
                    el,
                    value
                );
            }} else {{
                el.value = value;
            }}

            el.dispatchEvent(
                new Event(
                    "input",
                    {{ bubbles: true }}
                )
            );

            el.dispatchEvent(
                new Event(
                    "change",
                    {{ bubbles: true }}
                )
            );

            return {{
                success: true
            }};
        }})()
        """

        data = self._evaluate(
            expression
        )

        return self._result(
            bool(
                data
                and data.get("success")
            ),
            "type_by_placeholder",
            data,
            error=(
                None
                if data and data.get("success")
                else (
                    data.get("error")
                    if isinstance(data, dict)
                    else "Typing failed"
                )
            )
        )

    # ========================================================
    # WAIT FOR TEXT
    # ========================================================

    def wait_for_text(
        self,
        text,
        timeout=15,
        interval=0.25
    ):

        needle = str(text).lower()
        start = time.time()

        while (
            time.time() - start
            < timeout
        ):

            page_text = self.get_page_text()

            if needle in page_text.lower():

                return self._result(
                    True,
                    "wait_for_text",
                    {
                        "text": text,
                        "found": True
                    }
                )

            time.sleep(interval)

        return self._result(
            False,
            "wait_for_text",
            {
                "text": text,
                "found": False
            },
            error="Timeout waiting for text"
        )

    # ========================================================
    # WAIT FOR SELECTOR
    # ========================================================

    def wait_for_selector(
        self,
        selector,
        timeout=15,
        interval=0.25
    ):

        start = time.time()

        selector_js = self._js_string(
            selector
        )

        expression = f"""
        Boolean(
            document.querySelector(
                {selector_js}
            )
        )
        """

        while (
            time.time() - start
            < timeout
        ):

            if self._evaluate(
                expression
            ):

                return self._result(
                    True,
                    "wait_for_selector",
                    {
                        "selector": selector
                    }
                )

            time.sleep(interval)

        return self._result(
            False,
            "wait_for_selector",
            {
                "selector": selector
            },
            error="Timeout waiting for selector"
        )

    # ========================================================
    # SCREENSHOT
    # ========================================================

    def screenshot(
        self,
        path="smart_hands_screenshot.png"
    ):

        try:

            result = self.send_command(
                "Page.captureScreenshot",
                {
                    "format": "png",
                    "fromSurface": True
                }
            )

            data = (
                result
                .get("result", {})
                .get("data")
            )

            if not data:
                return self._result(
                    False,
                    "screenshot",
                    error="Screenshot data unavailable"
                )

            import base64

            with open(
                path,
                "wb"
            ) as f:
                f.write(
                    base64.b64decode(data)
                )

            return self._result(
                True,
                "screenshot",
                {
                    "path": path
                }
            )

        except Exception as e:

            return self._result(
                False,
                "screenshot",
                error=str(e)
            )

    # ========================================================
    # SCAN TASKS
    # ========================================================

    def scan_tasks(
        self,
        min_filled=70
    ):

        text = self.get_page_text()

        tasks = []

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            match = re.search(
                r"(\d+)\s*/\s*(\d+)",
                line
            )

            if not match:
                continue

            filled = int(
                match.group(1)
            )

            total = int(
                match.group(2)
            )

            if total <= 0:
                continue

            percent = (
                filled / total
            ) * 100

            if percent >= min_filled:

                tasks.append({
                    "title":
                        line[:150],
                    "filled":
                        filled,
                    "total":
                        total,
                    "percent":
                        round(percent, 2),
                    "detected_at":
                        datetime.now().isoformat()
                })

        logger.info(
            f"Found {len(tasks)} tasks."
        )

        return tasks

    # ========================================================
    # GENERIC TASK EXECUTION
    # ========================================================

    def execute_task(
        self,
        task,
        verify=True
    ):

        started = time.time()

        if self.stop_requested:

            return self._result(
                False,
                "execute_task",
                error="Stop requested"
            )

        if self.pause_requested:

            return self._result(
                False,
                "execute_task",
                error="Automation paused"
            )

        # --------------------------------------------
        # Human verification gate
        # --------------------------------------------

        indicators = self.detect_indicators()

        if indicators.get(
            "requires_human"
        ):

            result = self._result(
                False,
                "execute_task",
                {
                    "task": task,
                    "reason":
                        "Human verification required"
                },
                requires_human=True
            )

            self._save_checkpoint(
                task,
                result
            )

            return result

        title = ""

        if isinstance(task, dict):
            title = str(
                task.get(
                    "title",
                    ""
                )
            )
        else:
            title = str(task)

        title_lower = title.lower()

        logger.info(
            f"Executing task: {title[:100]}"
        )

        # --------------------------------------------
        # Supported generic patterns
        # --------------------------------------------

        action_result = None

        # Search/query task.
        search_match = re.search(
            r"(?:search|google)\s+(?:for\s+)?(.+)",
            title,
            re.IGNORECASE
        )

        if search_match:

            query = search_match.group(
                1
            ).strip()

            if query:

                encoded = urllib.parse.quote_plus(
                    query
                )

                action_result = self.navigate(
                    "https://www.google.com/search?q="
                    + encoded
                )

        # Open URL task.
        url_match = re.search(
            r"https?://[^\s]+",
            title
        )

        if (
            action_result is None
            and url_match
        ):

            action_result = self.navigate(
                url_match.group(0)
            )

        # If no known generic action was detected,
        # observe the task instead of pretending success.
        if action_result is None:

            page = self.scan_page()

            action_result = self._result(
                False,
                "execute_task",
                {
                    "task": task,
                    "page": page.get(
                        "data",
                        {}
                    ),
                    "message":
                        "Task detected, but no safe "
                        "generic execution rule matched."
                },
                error="No safe execution rule matched"
            )

        elapsed = time.time() - started

        self.metrics[
            "task_times"
        ].append(elapsed)

        if len(
            self.metrics["task_times"]
        ) > 100:

            self.metrics[
                "task_times"
            ] = self.metrics[
                "task_times"
            ][-100:]

        # --------------------------------------------
        # Verification
        # --------------------------------------------

        if (
            action_result.get("success")
            and verify
        ):

            if self._requires_human():

                action_result[
                    "requires_human"
                ] = True

                action_result[
                    "success"
                ] = False

                action_result[
                    "error"
                ] = (
                    "Human verification detected "
                    "after action."
                )

        if action_result.get(
            "success"
        ):

            self.success_count += 1

            self.metrics[
                "success_count"
            ] = self.success_count

        else:

            self.fail_count += 1

            self.metrics[
                "fail_count"
            ] = self.fail_count

        self._update_success_rate()

        self._save_checkpoint(
            task,
            action_result
        )

        return action_result

    # Compatibility aliases for main.py v7+

    def perform_task(
        self,
        task,
        verify=True
    ):
        return self.execute_task(
            task,
            verify=verify
        )

    def run_task(
        self,
        task,
        verify=True
    ):
        return self.execute_task(
            task,
            verify=verify
        )

    # ========================================================
    # HUMAN DELAY
    # ========================================================

    def human_delay(
        self,
        min_sec=0.2,
        max_sec=0.8
    ):

        min_sec = max(
            0,
            float(min_sec)
        )

        max_sec = max(
            min_sec,
            float(max_sec)
        )

        time.sleep(
            (min_sec + max_sec) / 2
        )

    def human_type(
        self,
        text,
        speed_wpm=None
    ):

        # Kept as compatibility helper.
        # Does not attempt to disguise automation.
        if speed_wpm is None:
            speed_wpm = 45

        speed_wpm = max(
            10,
            float(speed_wpm)
        )

        chars_per_second = (
            speed_wpm * 5
        ) / 60

        delay = 1 / max(
            chars_per_second,
            0.1
        )

        for _ in str(text):

            time.sleep(
                min(delay, 0.15)
            )

        return str(text)

    # ========================================================
    # LOGIN HELPERS
    # ========================================================

    def _login_common(
        self,
        platform,
        url,
        email,
        password,
        sign_in_text=("Sign In", "Log In", "Login")
    ):

        logger.info(
            f"Starting {platform} login."
        )

        for attempt in range(
            1,
            self.max_retries + 1
        ):

            try:

                result = self.navigate(
                    url
                )

                if not result.get(
                    "success"
                ):
                    continue

                # Human/security gate before credentials.
                gate = self.detect_indicators()

                if gate.get(
                    "requires_human"
                ):

                    return self._result(
                        False,
                        "login",
                        {
                            "platform":
                                platform
                        },
                        error=
                            "Human verification required.",
                        requires_human=True
                    )

                clicked = False

                for text in sign_in_text:

                    result = self.click_by_text(
                        text
                    )

                    if result.get(
                        "success"
                    ):

                        clicked = True
                        break

                if not clicked:
                    logger.warn(
                        "Login button not found."
                    )

                self.human_delay(
                    0.5,
                    1.0
                )

                email_result = (
                    self.type_by_placeholder(
                        "Email",
                        email
                    )
                )

                if not email_result.get(
                    "success"
                ):

                    # Some sites use name/id selectors.
                    email_result = (
                        self.type_text(
                            "input[type='email']",
                            email
                        )
                    )

                if not email_result.get(
                    "success"
                ):
                    continue

                password_result = (
                    self.type_by_placeholder(
                        "Password",
                        password
                    )
                )

                if not password_result.get(
                    "success"
                ):

                    password_result = (
                        self.type_text(
                            "input[type='password']",
                            password
                        )
                    )

                if not password_result.get(
                    "success"
                ):
                    continue

                login_clicked = False

                for text in (
                    "Login",
                    "Log In",
                    "Sign In",
                    "Continue",
                    "Next"
                ):

                    result = self.click_by_text(
                        text
                    )

                    if result.get(
                        "success"
                    ):

                        login_clicked = True
                        break

                if not login_clicked:

                    logger.warn(
                        "Final login button not found."
                    )

                self.human_delay(
                    1,
                    2
                )

                gate = self.detect_indicators()

                if gate.get(
                    "requires_human"
                ):

                    return self._result(
                        False,
                        "login",
                        {
                            "platform":
                                platform
                        },
                        error=
                            "Human verification required.",
                        requires_human=True
                    )

                self._save_session()

                return self._result(
                    True,
                    "login",
                    {
                        "platform":
                            platform,
                        "attempt":
                            attempt
                    }
                )

            except Exception as e:

                logger.warn(
                    f"{platform} login attempt "
                    f"{attempt} failed: {e}"
                )

                time.sleep(
                    min(
                        attempt,
                        3
                    )
                )

        return self._result(
            False,
            "login",
            {
                "platform":
                    platform
            },
            error="Login failed after bounded retries."
        )

    # ========================================================
    # PLATFORM LOGIN METHODS
    # ========================================================

    def rapidworkers_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "rapidworkers",
            self.PLATFORM_URLS[
                "rapidworkers"
            ],
            email,
            password,
            (
                "Sign In",
                "Log In",
                "Login"
            )
        )

    def timebucks_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "timebucks",
            self.PLATFORM_URLS[
                "timebucks"
            ],
            email,
            password
        )

    def freecash_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "freecash",
            self.PLATFORM_URLS[
                "freecash"
            ],
            email,
            password
        )

    def swagbucks_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "swagbucks",
            self.PLATFORM_URLS[
                "swagbucks"
            ],
            email,
            password
        )

    def ysense_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "ysense",
            self.PLATFORM_URLS[
                "ysense"
            ],
            email,
            password
        )

    def prizerebel_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "prizerebel",
            self.PLATFORM_URLS[
                "prizerebel"
            ],
            email,
            password
        )

    def grabpoints_login(
        self,
        email,
        password
    ):

        return self._login_common(
            "grabpoints",
            self.PLATFORM_URLS[
                "grabpoints"
            ],
            email,
            password
        )

    # ========================================================
    # GENERIC PLATFORM LOGIN
    # ========================================================

    def platform_login(
        self,
        platform,
        email,
        password
    ):

        platform = (
            str(platform)
            .strip()
            .lower()
        )

        logins = {
            "rapidworkers":
                self.rapidworkers_login,

            "timebucks":
                self.timebucks_login,

            "freecash":
                self.freecash_login,

            "swagbucks":
                self.swagbucks_login,

            "ysense":
                self.ysense_login,

            "prizerebel":
                self.prizerebel_login,

            "grabpoints":
                self.grabpoints_login,
        }

        handler = logins.get(
            platform
        )

        if not handler:

            return self._result(
                False,
                "platform_login",
                error=
                    f"Unsupported platform: {platform}"
            )

        return handler(
            email,
            password
        )

    # ========================================================
    # SESSION
    # ========================================================

    def _load_saved_ua(self):

        try:

            if not os.path.exists(
                self.state_file
            ):
                return None

            with open(
                self.state_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            return data.get(
                "ua"
            )

        except Exception:
            return None

    def _load_session(self):

        try:

            if not os.path.exists(
                self.state_file
            ):
                return

            with open(
                self.state_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.session_cookies = data.get(
                "cookies",
                {}
            )

            saved_ua = data.get(
                "ua"
            )

            if saved_ua:
                self.current_ua = saved_ua

        except Exception as e:

            logger.warn(
                f"Session load failed: {e}"
            )

    def _save_session(self):

        try:

            # Keep only explicitly stored session metadata.
            data = {
                "ua": self.current_ua,
                "updated_at":
                    datetime.now().isoformat()
            }

            with open(
                self.state_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=2
                )

        except Exception as e:

            logger.warn(
                f"Session save failed: {e}"
            )

    def _restore_cookies(self):

        # Intentionally does not export or replay
        # arbitrary authentication cookies.

        return True

    # ========================================================
    # MEMORY
    # ========================================================

    def _load_memory(self):

        try:

            with open(
                self.memory_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            if not isinstance(
                data,
                dict
            ):
                return {
                    "patterns": {}
                }

            data.setdefault(
                "patterns",
                {}
            )

            return data

        except Exception:

            return {
                "patterns": {}
            }

    def _save_memory(self):

        try:

            with open(
                self.memory_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.memory,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception as e:

            logger.warn(
                f"Memory save failed: {e}"
            )

    # ========================================================
    # OPTIMIZATION
    # ========================================================

    def _load_optimization_data(self):

        try:

            with open(
                self.optimization_file,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            return (
                data
                if isinstance(data, dict)
                else {"strategies": {}}
            )

        except Exception:

            return {
                "strategies": {}
            }

    def _save_optimization_data(self):

        try:

            with open(
                self.optimization_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    self.optimization_data,
                    f,
                    indent=2
                )

        except Exception:
            pass

    # ========================================================
    # CHECKPOINT
    # ========================================================

    def _save_checkpoint(
        self,
        task,
        result
    ):

        try:

            checkpoint = {
                "version":
                    self.VERSION,

                "timestamp":
                    datetime.now().isoformat(),

                "url":
                    self._current_url(),

                "title":
                    self._current_title(),

                "task":
                    task,

                "last_result":
                    result,

                "stop_requested":
                    self.stop_requested,

                "pause_requested":
                    self.pause_requested,
            }

            with open(
                self.checkpoint_file,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    checkpoint,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception as e:

            logger.warn(
                f"Checkpoint save failed: {e}"
            )

    def load_checkpoint(self):

        try:

            with open(
                self.checkpoint_file,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            return None

    def clear_checkpoint(self):

        try:

            if os.path.exists(
                self.checkpoint_file
            ):
                os.remove(
                    self.checkpoint_file
                )

        except Exception:
            pass

    # ========================================================
    # METRICS
    # ========================================================

    def _update_success_rate(self):

        total = (
            self.success_count
            + self.fail_count
        )

        self.metrics[
            "success_rate"
        ] = (
            self.success_count / total
            if total
            else 0
        )

    def _start_metrics_thread(self):

        def collect():

            while not self.closed:

                time.sleep(30)

                try:
                    self._update_success_rate()
                except Exception:
                    pass

        thread = threading.Thread(
            target=collect,
            daemon=True,
            name="SmartHandsMetrics"
        )

        thread.start()

    def get_metrics(self):

        self._update_success_rate()

        return dict(
            self.metrics
        )

    # ========================================================
    # STOP / PAUSE / RESUME
    # ========================================================

    def stop(self):

        self.stop_requested = True

        logger.info(
            "Stop requested."
        )

        return self._result(
            True,
            "stop"
        )

    def pause(self):

        self.pause_requested = True

        logger.info(
            "Automation paused."
        )

        return self._result(
            True,
            "pause"
        )

    def resume(self):

        self.pause_requested = False
        self.stop_requested = False

        logger.info(
            "Automation resumed."
        )

        return self._result(
            True,
            "resume"
        )

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        if self.closed:
            return

        self.closed = True

        try:
            self._save_session()
        except Exception:
            pass

        try:
            self._save_memory()
        except Exception:
            pass

        try:
            self._save_optimization_data()
        except Exception:
            pass

        try:

            if self.ws:

                try:
                    self.ws.close()
                except Exception:
                    pass

                self.ws = None

        except Exception:
            pass

        self.is_connected = False

        self._kill_process()

        if (
            self.temp_profile
            and os.path.exists(
                self.temp_profile
            )
        ):

            try:

                shutil.rmtree(
                    self.temp_profile,
                    ignore_errors=True
                )

            except Exception:
                pass

        self.temp_profile = None

        logger.info(
            "SmartHands closed cleanly."
        )

    # ========================================================
    # MAIN RUN
    # ========================================================

    def run(
        self,
        email,
        password,
        max_tasks=5,
        parallel=False,
        use_ai_scoring=False
    ):

        logger.info("=" * 60)
        logger.info(
            f"STARTING SMART HANDS v{self.VERSION}"
        )
        logger.info("=" * 60)

        self.stop_requested = False
        self.pause_requested = False
        self.closed = False

        if not self.connect():

            return (
                "Browser connection failed. "
                "Check Chrome/Chromium availability."
            )

        try:

            login_result = (
                self.rapidworkers_login(
                    email,
                    password
                )
            )

            if isinstance(
                login_result,
                dict
            ):

                if login_result.get(
                    "requires_human"
                ):

                    return (
                        "Human verification required "
                        "during login."
                    )

                if not login_result.get(
                    "success"
                ):

                    return "Login failed."

            elif not login_result:

                return "Login failed."

            tasks = self.scan_tasks()

            if not tasks:

                return "No tasks found."

            tasks = tasks[
                :max(
                    1,
                    int(max_tasks)
                )
            ]

            completed = 0
            failed = 0
            human_required = 0

            for task in tasks:

                if self.stop_requested:
                    break

                while self.pause_requested:

                    time.sleep(1)

                    if self.stop_requested:
                        break

                if self.stop_requested:
                    break

                result = self.execute_task(
                    task,
                    verify=True
                )

                if result.get(
                    "requires_human"
                ):

                    human_required += 1
                    break

                if result.get(
                    "success"
                ):

                    completed += 1

                else:

                    failed += 1

            total = len(tasks)

            return (
                "\n"
                + "=" * 60
                + "\n"
                + "SMART HANDS RESULT"
                + "\n"
                + "=" * 60
                + "\n"
                + f"Tasks selected: {total}\n"
                + f"Completed: {completed}\n"
                + f"Failed: {failed}\n"
                + f"Human handoff: {human_required}\n"
                + f"Success rate: "
                + (
                    f"{completed / total * 100:.0f}%"
                    if total
                    else "0%"
                )
                + "\n"
                + f"Engine version: {self.VERSION}\n"
                + "=" * 60
            )

        except Exception as e:

            logger.error(
                f"Run error: {e}"
            )

            return f"Run error: {e}"

        finally:

            self.close()


# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    print(
        "=" * 60
    )

    print(
        f"SmartHands v{SmartHands.VERSION}"
    )

    print(
        "Browser Execution Engine"
    )

    print(
        "=" * 60
    )

    hands = SmartHands(
        headless=True
    )

    try:

        if hands.connect():

            print(
                "\nBrowser connected."
            )

            print(
                "\nPAGE INFO:"
            )

            print(
                json.dumps(
                    hands.get_page_info(),
                    indent=2,
                    ensure_ascii=False
                )
            )

            print(
                "\nPAGE SCAN:"
            )

            scan = hands.scan_page()

            print(
                json.dumps(
                    scan,
                    indent=2,
                    ensure_ascii=False
                )[:5000]
            )

        else:

            print(
                "\nBrowser connection failed."
            )

    finally:

        hands.close()
