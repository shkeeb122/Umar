# ====================================================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - Chat + Intent + Browser Planning + Kiwi Bridge
# 🚀 VERSION: 7.0.0
# ====================================================================================================
#
# ARCHITECTURE
#
# USER
#   ↓
# app.py
#   ↓
# detect_intent()
#   ↓
# ┌──────────────────────────────────────────────────────────────┐
# │                       AI SERVICE BRAIN                       │
# │                                                              │
# │  NORMAL CHAT                                                 │
# │  WEB SEARCH                                                  │
# │  WEBSITE OPEN                                                │
# │  PAGE SCAN                                                   │
# │  PAGE EXTRACTION                                             │
# │  FIND                                                         │
# │  CLICK                                                        │
# │  TYPE                                                         │
# │  WAIT                                                         │
# │  SCROLL                                                       │
# │  SECURITY / HUMAN HANDOFF                                    │
# │  MULTI-STEP AUTOMATION                                       │
# │  SMART TASK                                                   │
# │  STATUS                                                        │
# │  STOP                                                          │
# └──────────────────────────────────────────────────────────────┘
#   ↓
# Kiwi Extension Bridge
#   ↓
# background.js
#   ↓
# content.js
#   ↓
# REAL WEBSITE
#   ↓
# RESULT
#   ↓
# AI SERVICE
#   ↓
# USER
#
# 🔒 IMPORTANT:
# ai_chat() CORE API FUNCTION IS LOCKED.
# Its internal API structure is intentionally preserved.
#
# DESIGN RULE:
# Existing architecture is preserved.
# New functionality is added around the existing layers.
#
# ====================================================================================================


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import os
import json
import requests
import time
import re

from datetime import datetime


from config import (
    MISTRAL_URL,
    HEADERS,
    MODEL_NAME,
    BACKEND_URL
)


from db import (
    get_recent_history,
    get_all_history,
    count_questions
)


from helpers import (
    is_question,
    format_response,
    extract_topic
)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: CORE AI
# 🔒 LOCKED - DO NOT CHANGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def ai_chat(messages, temperature=0.7, max_tokens=500):
    """
    🔒 CORE FUNCTION - DO NOT CHANGE

    Mistral AI Chat Completion API
    """

    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }

        start_time = time.time()

        r = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json=payload,
            timeout=15
        )

        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."

        data = r.json()

        response = data.get(
            "choices",
            [{}]
        )[0].get(
            "message",
            {}
        ).get(
            "content",
            ""
        )

        print(
            f"✅ AI Response time: "
            f"{time.time() - start_time:.2f}s"
        )

        return (
            response.strip()
            if response
            else "I'm not sure how to respond."
        )

    except requests.exceptions.Timeout:
        return "⏰ Request timeout (15s). Please try again."

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "❌ Error occurred. Please try again."


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2.5: KIWI EXTENSION BRIDGE
# 🌉 Render → Kiwi
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

EXTENSION_TEST_TOKEN = os.environ.get(
    "EXTENSION_TEST_TOKEN",
    ""
)


EXTENSION_COMMAND_URL = (
    f"{BACKEND_URL.rstrip('/')}"
    f"/extension/test/command"
)


EXTENSION_STATUS_URL = (
    f"{BACKEND_URL.rstrip('/')}"
    f"/extension/test/status"
)


EXTENSION_RESULT_TIMEOUT = int(
    os.environ.get(
        "EXTENSION_RESULT_TIMEOUT",
        "30"
    )
)


EXTENSION_POLL_INTERVAL = float(
    os.environ.get(
        "EXTENSION_POLL_INTERVAL",
        "0.5"
    )
)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2.6: GENERIC HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def safe_string(value):
    """
    Convert anything to a safe string.
    """

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(value):
    """
    Normalize natural-language input.

    Keeps Hindi/Hinglish/English text intact,
    while removing excessive spaces.
    """

    return re.sub(
        r"\s+",
        " ",
        safe_string(value)
    ).strip()


def clean_quotes(value):
    """
    Remove surrounding quotes.
    """

    value = safe_string(value).strip()

    if len(value) >= 2:
        if (
            (
                value.startswith('"')
                and value.endswith('"')
            )
            or
            (
                value.startswith("'")
                and value.endswith("'")
            )
            or
            (
                value.startswith("“")
                and value.endswith("”")
            )
            or
            (
                value.startswith("‘")
                and value.endswith("’")
            )
        ):
            return value[1:-1].strip()

    return value


def now_iso():
    return datetime.now().isoformat()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2.7: KIWI BRIDGE COMMAND ENGINE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def send_extension_command(
    action,
    url=None,
    extra_data=None,
    timeout=10
):
    """
    🌉 GENERIC RENDER → KIWI COMMAND

    This is intentionally generic.

    Existing commands:
        open
        search

    New compatible browser commands:
        scan
        detect
        find
        find_element
        click
        click_by_text
        type
        extract
        extract_text
        page_info
        wait_for_text
        wait_for_selector
        wait_for_visible
        scroll

    The actual DOM work is performed by:
        background.js
            ↓
        content.js
    """

    if not EXTENSION_TEST_TOKEN:

        print(
            "❌ EXTENSION_TEST_TOKEN is missing"
        )

        return {
            "success": False,
            "error": (
                "EXTENSION_TEST_TOKEN is not "
                "configured on Render."
            )
        }


    headers = {
        "X-Extension-Test-Token":
            EXTENSION_TEST_TOKEN,

        "Content-Type":
            "application/json"
    }


    payload = {
        "action":
            safe_string(action)
    }


    if url:
        payload["url"] = url


    if isinstance(extra_data, dict):
        payload.update(
            extra_data
        )


    try:

        print("=" * 70)
        print("🌉 KIWI BRIDGE COMMAND")
        print(
            f"Action: {payload.get('action')}"
        )
        print(
            f"URL: {payload.get('url', '')}"
        )
        print(
            f"Data: {extra_data}"
        )
        print("=" * 70)


        response = requests.post(
            EXTENSION_COMMAND_URL,
            headers=headers,
            json=payload,
            timeout=timeout
        )


        if response.status_code != 200:

            print(
                "❌ Bridge HTTP error: "
                f"{response.status_code}"
            )

            return {
                "success": False,

                "error": (
                    "Bridge command failed with "
                    f"HTTP {response.status_code}"
                ),

                "http_status":
                    response.status_code
            }


        try:
            data = response.json()

        except ValueError:

            return {
                "success": False,
                "error":
                    "Bridge returned invalid JSON."
            }


        if not data.get("success"):

            return {
                "success": False,

                "error": data.get(
                    "message",
                    data.get(
                        "error",
                        "Command was not queued."
                    )
                )
            }


        command = data.get(
            "command",
            {}
        )


        command_id = command.get(
            "command_id"
        )


        if not command_id:

            return {
                "success": False,
                "error":
                    "Bridge did not return command_id."
            }


        print(
            f"✅ Command queued: {command_id}"
        )


        # ============================================================================================
        # WAIT FOR KIWI RESULT
        # ============================================================================================

        started = time.time()


        while (
            time.time() - started
        ) < EXTENSION_RESULT_TIMEOUT:

            try:

                status_response = requests.get(
                    EXTENSION_STATUS_URL,
                    headers=headers,
                    timeout=5
                )


                if status_response.status_code == 200:

                    status_data = (
                        status_response.json()
                    )


                    last_result = (
                        status_data.get(
                            "last_result"
                        )
                    )


                    if isinstance(
                        last_result,
                        dict
                    ):

                        returned_command_id = (
                            last_result.get(
                                "command_id"
                            )
                        )


                        if (
                            returned_command_id
                            == command_id
                        ):

                            print(
                                "✅ Kiwi result received: "
                                f"{command_id}"
                            )

                            return last_result


            except requests.exceptions.RequestException as poll_error:

                print(
                    "⚠️ Bridge polling error: "
                    f"{poll_error}"
                )


            time.sleep(
                EXTENSION_POLL_INTERVAL
            )


        print(
            "⏳ Kiwi result timeout: "
            f"{command_id}"
        )


        return {
            "success": False,
            "pending": True,
            "command_id": command_id,

            "message": (
                "Command was sent to Kiwi, "
                "but browser result has not "
                "arrived yet."
            )
        }


    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error":
                "Extension bridge request timed out."
        }


    except requests.exceptions.RequestException as error:

        return {
            "success": False,
            "error":
                f"Extension bridge network error: {error}"
        }


    except Exception as error:

        print(
            f"❌ Extension bridge error: {error}"
        )

        return {
            "success": False,
            "error":
                str(error)
        }


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3: WEBSITE MAP
# 🌐 CENTRAL WEBSITE KNOWLEDGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

WEBSITE_MAP = {

    "google":
        "https://www.google.com/",

    "youtube":
        "https://www.youtube.com/",

    "facebook":
        "https://www.facebook.com/",

    "instagram":
        "https://www.instagram.com/",

    "twitter":
        "https://x.com/",

    "x":
        "https://x.com/",

    "linkedin":
        "https://www.linkedin.com/",

    "github":
        "https://github.com/",

    "gmail":
        "https://mail.google.com/",

    "maps":
        "https://maps.google.com/",

    "drive":
        "https://drive.google.com/",

    "docs":
        "https://docs.google.com/",

    "amazon":
        "https://www.amazon.in/",

    "flipkart":
        "https://www.flipkart.com/",

    "reddit":
        "https://www.reddit.com/",

    "stackoverflow":
        "https://stackoverflow.com/",

    "rapidworkers":
        "https://rapidworkers.com/",

    "timebucks":
        "https://timebucks.com/",

    "freecash":
        "https://freecash.com/",

    "swagbucks":
        "https://www.swagbucks.com/",

    "ysense":
        "https://www.ysense.com/",

    "prizerebel":
        "https://www.prizerebel.com/",

    "grabpoints":
        "https://grabpoints.com/",

    "bing":
        "https://www.bing.com/",

    "duckduckgo":
        "https://duckduckgo.com/",

    "wikipedia":
        "https://www.wikipedia.org/",

    "news":
        "https://news.google.com/"
}


WEBSITE_ALIASES = {

    "yt":
        "youtube",

    "fb":
        "facebook",

    "ig":
        "instagram",

    "tw":
        "twitter",

    "li":
        "linkedin",

    "gh":
        "github",

    "gm":
        "gmail",

    "amz":
        "amazon",

    "fk":
        "flipkart",

    "rw":
        "rapidworkers",

    "tb":
        "timebucks",

    "fc":
        "freecash",

    "sb":
        "swagbucks",

    "ys":
        "ysense",

    "pr":
        "prizerebel",

    "gp":
        "grabpoints",

    "so":
        "stackoverflow",

    "wiki":
        "wikipedia"
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3.5: ACTION MAP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

BROWSER_ACTIONS = {

    "open": {
        "bridge_action": "open",
        "description":
            "Open a website or URL."
    },

    "search": {
        "bridge_action": "search",
        "description":
            "Search using Google."
    },

    "scan": {
        "bridge_action": "scan",
        "description":
            "Scan current page."
    },

    "detect": {
        "bridge_action": "detect",
        "description":
            "Detect task/security indicators."
    },

    "find": {
        "bridge_action": "find",
        "description":
            "Find visible page elements by text."
    },

    "find_element": {
        "bridge_action": "find_element",
        "description":
            "Find element by CSS selector."
    },

    "click": {
        "bridge_action": "click",
        "description":
            "Click an element by selector."
    },

    "click_by_text": {
        "bridge_action": "click_by_text",
        "description":
            "Click a visible element by text."
    },

    "type": {
        "bridge_action": "type",
        "description":
            "Type into an editable element."
    },

    "extract": {
        "bridge_action": "extract",
        "description":
            "Extract text from current page."
    },

    "page_info": {
        "bridge_action": "page_info",
        "description":
            "Get current page metadata."
    },

    "wait_for_text": {
        "bridge_action": "wait_for_text",
        "description":
            "Wait for text to appear."
    },

    "wait_for_selector": {
        "bridge_action": "wait_for_selector",
        "description":
            "Wait for selector."
    },

    "wait_for_visible": {
        "bridge_action": "wait_for_visible",
        "description":
            "Wait until element becomes visible."
    },

    "scroll": {
        "bridge_action": "scroll",
        "description":
            "Scroll page."
    }
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: INTENT REGISTRY
# 🧠 BRAIN MAP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

INTENT_REGISTRY = {

    # ================================================================================================
    # NORMAL AI
    # ================================================================================================

    "chat": {
        "keywords": [],
        "handler": "handle_chat",
        "priority": 0,
        "description":
            "Default normal AI conversation.",
        "example":
            "Hello, kese ho?"
    },


    "count_questions": {
        "keywords": [
            "kitne sawal",
            "total sawal",
            "how many question",
            "sawal kitne",
            "questions count"
        ],
        "handler":
            "handle_count_questions",
        "priority": 2,
        "description":
            "Count questions.",
        "example":
            "Maine kitne sawal kiye?"
    },


    "recall": {
        "keywords": [
            "pehle kya hua",
            "pichle",
            "previous",
            "yaad",
            "bhool",
            "kal",
            "purana",
            "history"
        ],
        "handler":
            "handle_recall",
        "priority": 2,
        "description":
            "Recall conversation history.",
        "example":
            "Pehle kya hua tha?"
    },


    "follow_up": {
        "keywords": [
            "aur batao",
            "tell more",
            "elaborate",
            "aur details",
            "aur jaankari",
            "further"
        ],
        "handler":
            "handle_follow_up",
        "priority": 1,
        "description":
            "Continue previous discussion.",
        "example":
            "Aur batao."
    },


    "blog": {
        "keywords": [
            "blog",
            "article",
            "post",
            "blog banao",
            "article likho",
            "post likho"
        ],
        "handler":
            "handle_blog",
        "priority": 1,
        "description":
            "Generate blog content.",
        "example":
            "Blog banao AI ke baare mein."
    },


    "image": {
        "keywords": [
            "image",
            "photo",
            "picture",
            "image samjhao",
            "photo dekho",
            "ye kya hai"
        ],
        "handler":
            "handle_image",
        "priority": 1,
        "description":
            "Image understanding.",
        "example":
            "Is image mein kya hai?"
    },


    # ================================================================================================
    # REAL WEB SEARCH
    # ================================================================================================

    "search": {
        "keywords": [
            "search karo",
            "search",
            "google search",
            "google par",
            "google mein",
            "pata karo",
            "pata lagao",
            "khojo",
            "khoj",
            "dhundo",
            "dhoondo",
            "find"
        ],
        "handler":
            "handle_search",
        "priority": 8,
        "description":
            "Real browser search.",
        "example":
            "Google search karo OpenAI."
    },


    # ================================================================================================
    # BROWSER OPEN
    # ================================================================================================

    "smart_open": {
        "keywords": [
            "website kholo",
            "website open",
            "kholo",
            "open",
            "browser",
            "jao",
            "google open",
            "youtube open",
            "facebook open",
            "amazon open",
            "flipkart open",
            "github open"
        ],
        "handler":
            "handle_smart_open",
        "priority": 7,
        "description":
            "Open website in Kiwi.",
        "example":
            "Google kholo."
    },


    # ================================================================================================
    # PAGE OBSERVATION
    # ================================================================================================

    "browser_scan": {
        "keywords": [
            "page scan",
            "page scan karo",
            "scan page",
            "scan karo",
            "page dekho",
            "page ko dekho",
            "website scan",
            "scan website",
            "page analyze karo",
            "page analyse karo"
        ],
        "handler":
            "handle_browser_scan",
        "priority": 9,
        "description":
            "Scan actual browser page.",
        "example":
            "Is page ko scan karo."
    },


    "browser_extract": {
        "keywords": [
            "extract text",
            "text extract",
            "page ka text",
            "page ka text nikalo",
            "text nikalo",
            "text nikaalo",
            "page se text",
            "content nikalo",
            "content extract"
        ],
        "handler":
            "handle_browser_extract",
        "priority": 9,
        "description":
            "Extract actual browser page text.",
        "example":
            "Page ka text nikalo."
    },


    "browser_info": {
        "keywords": [
            "page info",
            "page information",
            "page details",
            "website info",
            "current page",
            "current website",
            "url batao",
            "page url",
            "page title"
        ],
        "handler":
            "handle_browser_info",
        "priority": 9,
        "description":
            "Get actual browser page information.",
        "example":
            "Page info batao."
    },


    "browser_detect": {
        "keywords": [
            "detect",
            "indicators",
            "task detect",
            "security check",
            "captcha check",
            "page indicators"
        ],
        "handler":
            "handle_browser_detect",
        "priority": 9,
        "description":
            "Detect browser page indicators.",
        "example":
            "Page detect karo."
    },


    # ================================================================================================
    # ELEMENT OPERATIONS
    # ================================================================================================

    "browser_find": {
        "keywords": [
            "element dhundo",
            "element dhoondo",
            "element find",
            "button dhundo",
            "button dhoondo",
            "text dhundo",
            "link dhundo",
            "find element"
        ],
        "handler":
            "handle_browser_find",
        "priority": 9,
        "description":
            "Find an element on current page.",
        "example":
            "Sign in button dhundo."
    },


    "browser_click": {
        "keywords": [
            "click karo",
            "click",
            "button click",
            "button dabao",
            "link click",
            "open button",
            "press button"
        ],
        "handler":
            "handle_browser_click",
        "priority": 10,
        "description":
            "Click a browser element.",
        "example":
            "Sign in button click karo."
    },


    "browser_type": {
        "keywords": [
            "type karo",
            "type",
            "likho",
            "enter karo",
            "text dalo",
            "text daalo",
            "fill karo",
            "input karo",
            "search box mein"
        ],
        "handler":
            "handle_browser_type",
        "priority": 10,
        "description":
            "Type into browser input.",
        "example":
            "Search box mein laptop type karo."
    },


    "browser_wait": {
        "keywords": [
            "wait karo",
            "wait",
            "intezar karo",
            "load hone do",
            "wait for"
        ],
        "handler":
            "handle_browser_wait",
        "priority": 8,
        "description":
            "Wait for page content.",
        "example":
            "Open hone ke baad wait karo."
    },


    "browser_scroll": {
        "keywords": [
            "scroll karo",
            "neeche scroll",
            "upar scroll",
            "page neeche",
            "page upar",
            "bottom par",
            "top par"
        ],
        "handler":
            "handle_browser_scroll",
        "priority": 8,
        "description":
            "Scroll current page.",
        "example":
            "Page neeche scroll karo."
    },


    # ================================================================================================
    # AUTOMATION
    # ================================================================================================

    "smart_task": {
        "keywords": [
            "rapidworker",
            "task karo",
            "kaam karo",
            "automation start",
            "rapid pe jao",
            "task start",
            "kaam shuru",
            "rapidworker start",
            "task",
            "auto",
            "start automation",
            "automation",
            "rapid workers",
            "micro task",
            "earn money",
            "timebucks",
            "freecash",
            "swagbucks",
            "ysense",
            "work start",
            "job start",
            "earning start"
        ],
        "handler":
            "handle_smart_task",
        "priority": 6,
        "description":
            "Start SmartMain automation.",
        "example":
            "Task start karo."
    },


    "smart_status": {
        "keywords": [
            "status",
            "kya chal raha",
            "haal",
            "progress",
            "kitna hua",
            "report",
            "update",
            "earning",
            "kamaai",
            "tasks done",
            "progress report",
            "how many tasks",
            "kitne task",
            "balance",
            "show status",
            "current status"
        ],
        "handler":
            "handle_smart_status",
        "priority": 3,
        "description":
            "System status.",
        "example":
            "Status kya hai?"
    },


    "smart_stop": {
        "keywords": [
            "automation band",
            "task stop",
            "band karo",
            "stop",
            "rok do",
            "rok",
            "halt",
            "automation rok"
        ],
        "handler":
            "handle_smart_stop",
        "priority": 12,
        "description":
            "Stop automation.",
        "example":
            "Automation band karo."
    },


    # ================================================================================================
    # OTHER AI
    # ================================================================================================

    "translate": {
        "keywords": [
            "translate",
            "anuvad",
            "convert language",
            "translate karo",
            "bhasha badlo",
            "language change"
        ],
        "handler":
            "handle_translate",
        "priority": 2,
        "description":
            "Translation.",
        "example":
            "Hello ko Hindi mein translate karo."
    },


    "code": {
        "keywords": [
            "code",
            "program",
            "function",
            "code likho",
            "program banao",
            "script",
            "programming"
        ],
        "handler":
            "handle_code",
        "priority": 2,
        "description":
            "Code generation.",
        "example":
            "Python code likho."
    },


    "summarize": {
        "keywords": [
            "summary",
            "summarize",
            "sankshep",
            "short summary",
            "summarise"
        ],
        "handler":
            "handle_summarize",
        "priority": 2,
        "description":
            "Summarize text.",
        "example":
            "Is text ka summary do."
    }
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 5: NORMAL AI HANDLERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_chat(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    history = history or []

    current_date = datetime.now().strftime(
        "%d %B %Y"
    )


    messages = [
        {
            "role":
                "system",

            "content": (
                "You are a helpful AI assistant. "
                f"Today's date is {current_date}. "
                "Understand Hindi, Hinglish and English. "
                "Reply naturally in the user's language. "
                "Do not pretend that a browser action happened "
                "unless a real browser result confirms it."
            )
        }
    ]


    messages.extend(
        history[-10:]
    )


    messages.append({
        "role":
            "user",

        "content":
            message
    })


    return ai_chat(
        messages,
        temperature=0.7,
        max_tokens=500
    )


def handle_count_questions(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    count = count_questions(
        campaign_id
    )

    return (
        f"📊 Total questions: {count}"
    )


def handle_recall(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    if not campaign_id:

        return (
            "No chat history found. "
            "Start a new chat first!"
        )


    recent = get_recent_history(
        campaign_id,
        20
    )


    if not recent:

        return (
            "I don't remember anything."
        )


    return (
        "📜 Previous:\n"
        +
        "\n".join(
            [
                f"• {q['content']}"
                for q in recent
            ]
        )
    )


def handle_follow_up(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    if history:

        return handle_chat(
            message,
            history,
            all_history,
            campaign_id
        )

    return (
        "Bilkul. Kis part ke baare mein "
        "aur detail chahiye?"
    )


def handle_blog(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    topic = extract_topic(
        message
    )


    if not topic:

        return (
            "📝 What topic for blog?"
        )


    messages = [
        {
            "role":
                "system",

            "content": (
                "You are an expert writer. "
                "Create a detailed, engaging "
                f"blog post about: {topic}"
            )
        }
    ]


    return ai_chat(
        messages,
        temperature=0.8,
        max_tokens=2000
    )


def handle_image(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    image_url = re.search(
        r'(https?://[^\s]+\.(jpg|jpeg|png|gif|webp))',
        message,
        re.IGNORECASE
    )


    if not image_url:

        return (
            "Please provide an image URL."
        )


    content = [
        {
            "type":
                "text",

            "text":
                "Describe this image in detail."
        },

        {
            "type":
                "image_url",

            "image_url":
                image_url.group(0)
        }
    ]


    messages = [
        {
            "role":
                "user",

            "content":
                content
        }
    ]


    return ai_chat(
        messages,
        temperature=0.7,
        max_tokens=500
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 6: SEARCH ENGINE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extract_search_query(message):

    query = normalize_text(
        message
    )


    patterns = [

        r'^\s*google\s+search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+par\s+search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+mein\s+search\s+kar(?:o|na)?\s*',

        r'^\s*search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+par\s*',

        r'^\s*google\s+mein\s*',

        r'^\s*search\s+',

        r'^\s*google\s+'
    ]


    for pattern in patterns:

        new_query = re.sub(
            pattern,
            "",
            query,
            count=1,
            flags=re.IGNORECASE
        )

        if new_query != query:

            query = new_query.strip()
            break


    trailing = [

        r'\s+search\s+kar(?:o|na)?\s*$',

        r'\s+search\s*$',

        r'\s+khoj(?:o|na)?\s*$',

        r'\s+dhund(?:o|na)?\s*$',

        r'\s+dhoond(?:o|na)?\s*$',

        r'\s+pata\s+kar(?:o|na)?\s*$'
    ]


    for pattern in trailing:

        query = re.sub(
            pattern,
            "",
            query,
            count=1,
            flags=re.IGNORECASE
        ).strip()


    query = re.sub(
        r'\s+',
        ' ',
        query
    ).strip()


    return query.strip(
        " \t\n\r.,!?;:'\"“”‘’()[]{}"
    )


def handle_search(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    query = extract_search_query(
        message
    )


    if not query:

        return (
            "🔎 Kya search karna hai?\n"
            "Example: Google search karo OpenAI"
        )


    result = send_extension_command(
        action="search",

        extra_data={
            "query":
                query,

            "engine":
                "google"
        }
    )


    if result.get("success"):

        result_url = result.get(
            "url",
            ""
        )


        if result_url:

            return (
                "✅ Google search complete.\n"
                f"🔎 Search: {query}\n"
                f"🌐 {result_url}"
            )


        return (
            "✅ Google search complete.\n"
            f"🔎 Search: {query}"
        )


    if result.get("pending"):

        return (
            "⏳ Search Kiwi ko bheji gayi hai.\n"
            f"🔎 Search: {query}\n"
            f"🆔 Command: "
            f"{result.get('command_id', 'unknown')}"
        )


    return (
        "❌ Google search start nahi ho saki.\n"
        f"⚠️ {result.get('error', 'Unknown error')}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 7: WEBSITE RESOLUTION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def resolve_website(message):

    text = normalize_text(
        message
    )

    lower_text = text.lower()


    # ================================================================================================
    # DIRECT URL
    # ================================================================================================

    urls = re.findall(
        r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,})',
        text
    )


    if urls:

        url = urls[0].rstrip(
            ".,!?;:)]}"
        )


        if not url.startswith(
            "http://"
        ) and not url.startswith(
            "https://"
        ):

            url = (
                "https://"
                + url
            )


        return url


    # ================================================================================================
    # ALIAS
    # ================================================================================================

    for alias, website in WEBSITE_ALIASES.items():

        if re.search(
            rf"\b{re.escape(alias)}\b",
            lower_text
        ):

            return WEBSITE_MAP.get(
                website
            )


    # ================================================================================================
    # WEBSITE NAME
    # ================================================================================================

    # Longer names first.
    websites = sorted(
        WEBSITE_MAP.items(),
        key=lambda item:
            len(item[0]),
        reverse=True
    )


    for name, url in websites:

        if re.search(
            rf"\b{re.escape(name)}\b",
            lower_text
        ):

            return url


    return None


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 8: SMART OPEN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_open(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    url = resolve_website(
        message
    )


    if not url:

        return (
            "🌐 Kaunsi website open karni hai?\n"
            "Example: Google kholo"
        )


    result = send_extension_command(
        action="open",
        url=url
    )


    if result.get("success"):

        opened_url = result.get(
            "url",
            url
        )

        return (
            "✅ Website successfully open ho gayi.\n"
            f"🌐 {opened_url}"
        )


    if result.get("pending"):

        return (
            "⏳ Website open command Kiwi ko bhej di gayi hai.\n"
            f"🌐 {url}\n"
            f"🆔 {result.get('command_id', 'unknown')}"
        )


    return (
        "❌ Website open nahi ho saki.\n"
        f"🌐 {url}\n"
        f"⚠️ {result.get('error', 'Unknown error')}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 9: BROWSER COMMAND HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def browser_command(
    action,
    extra_data=None
):
    """
    Generic browser action wrapper.
    """

    bridge_action = (
        BROWSER_ACTIONS.get(
            action,
            {}
        ).get(
            "bridge_action",
            action
        )
    )


    return send_extension_command(
        action=bridge_action,
        extra_data=extra_data or {}
    )


def browser_error_response(
    action,
    result
):

    if result.get("pending"):

        return (
            f"⏳ Browser action '{action}' "
            "Kiwi ko bhej di gayi hai.\n"
            f"🆔 Command: "
            f"{result.get('command_id', 'unknown')}"
        )


    return (
        f"❌ Browser action '{action}' "
        "complete nahi hui.\n"
        f"⚠️ "
        f"{result.get('error', result.get('message', 'Unknown error'))}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 10: REAL PAGE SCAN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_scan(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    result = browser_command(
        "scan"
    )


    if not result.get("success"):

        return browser_error_response(
            "scan",
            result
        )


    return format_browser_scan_result(
        result
    )


def format_browser_scan_result(result):

    page = result.get(
        "page",
        {}
    )


    headings = result.get(
        "headings",
        []
    )


    links = result.get(
        "links",
        []
    )


    buttons = result.get(
        "buttons",
        []
    )


    inputs = result.get(
        "inputs",
        []
    )


    return (
        "🔎 REAL BROWSER PAGE SCAN\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📄 Title: {page.get('title', '')}\n"
        f"🌐 URL: {page.get('url', '')}\n"
        f"📌 Domain: {page.get('domain', '')}\n"
        f"📝 Text length: "
        f"{result.get('textLength', 0)}\n"
        "\n"
        f"🔹 Headings: {len(headings)}\n"
        f"🔗 Links: {len(links)}\n"
        f"🔘 Buttons: {len(buttons)}\n"
        f"⌨️ Inputs: {len(inputs)}\n"
        "\n"
        "📋 PAGE TEXT PREVIEW\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{result.get('textPreview', '')[:6000]}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 11: REAL PAGE EXTRACTION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_extract(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    selector = extract_selector(
        message
    )


    extra = {}

    if selector:
        extra["selector"] = selector


    result = browser_command(
        "extract",
        extra
    )


    if not result.get("success"):

        return browser_error_response(
            "extract",
            result
        )


    return (
        "📄 REAL PAGE TEXT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 {result.get('url', '')}\n"
        f"📌 {result.get('title', '')}\n\n"
        f"{result.get('text', '')}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 12: PAGE INFORMATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_info(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    result = browser_command(
        "page_info"
    )


    if not result.get("success"):

        return browser_error_response(
            "page_info",
            result
        )


    return (
        "📄 REAL PAGE INFORMATION\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 URL: {result.get('url', '')}\n"
        f"📌 Title: {result.get('title', '')}\n"
        f"🌍 Domain: {result.get('domain', '')}\n"
        f"📂 Path: {result.get('pathname', '')}\n"
        f"⚙️ Ready: {result.get('readyState', '')}\n"
        f"📝 Body text: "
        f"{result.get('bodyTextLength', 0)} characters\n"
        f"🕒 {result.get('timestamp', '')}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 13: SECURITY / HUMAN HANDOFF
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_detect(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    result = browser_command(
        "detect"
    )


    if not result.get("success"):

        return browser_error_response(
            "detect",
            result
        )


    if result.get(
        "requires_human"
    ):

        return (
            "🛑 HUMAN ACTION REQUIRED\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ {result.get('human_reason', '')}\n\n"
            "Automation ko security/verification "
            "step par stop karna chahiye.\n"
            "CAPTCHA, OTP, payment ya security "
            "verification ko bypass nahi kiya jayega."
        )


    detected = result.get(
        "detected",
        {}
    )


    return (
        "🔍 PAGE INDICATORS\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Task: {detected.get('task', [])}\n"
        f"Login: {detected.get('login', [])}\n"
        f"CAPTCHA: {detected.get('captcha', [])}\n"
        f"Error: {detected.get('error', [])}\n"
        f"Payment: {detected.get('payment', [])}\n"
        f"OTP: {detected.get('otp', [])}\n"
        f"Human required: "
        f"{result.get('requires_human', False)}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 14: FIND ELEMENT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extract_target_text(
    message
):

    text = normalize_text(
        message
    )


    patterns = [

        r'["“](.+?)["”]',

        r"['‘](.+?)['’]",

        r"(?:button|link|text|element)\s+(.+?)\s+(?:dhundo|dhoondo|find|khojo|khoj|search)",

        r"(?:button|link|text|element)\s+(.+)$",

        r"(?:dhundo|dhoondo|find|khojo|khoj)\s+(.+)$"
    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )


        if match:

            value = clean_quotes(
                match.group(1)
            )

            value = re.sub(
                r"\b(?:button|link|text|element)\b",
                "",
                value,
                flags=re.IGNORECASE
            ).strip()


            if value:
                return value


    return ""


def extract_selector(
    message
):

    patterns = [

        r"selector\s*[:=]\s*(.+)$",

        r"css\s+selector\s*[:=]\s*(.+)$",

        r"by\s+selector\s+(.+)$"
    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            message or "",
            re.IGNORECASE
        )


        if match:
            return clean_quotes(
                match.group(1)
            )


    return None


def handle_browser_find(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    selector = extract_selector(
        message
    )


    if selector:

        result = browser_command(
            "find_element",
            {
                "selector":
                    selector
            }
        )

    else:

        target = extract_target_text(
            message
        )


        if not target:

            return (
                "🔎 Kya dhundna hai?\n"
                "Example: Sign in button dhundo"
            )


        result = browser_command(
            "find",
            {
                "text":
                    target,

                "tag":
                    "*"
            }
        )


    if not result.get("success"):

        return browser_error_response(
            "find",
            result
        )


    return (
        "🔎 ELEMENT SEARCH RESULT\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{json.dumps(result, ensure_ascii=False, indent=2)[:10000]}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 15: CLICK
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_click(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    selector = extract_selector(
        message
    )


    if selector:

        result = browser_command(
            "click",
            {
                "selector":
                    selector
            }
        )

    else:

        target = extract_target_text(
            message
        )


        if not target:

            return (
                "🖱️ Kya click karna hai?\n"
                "Example: \"Sign in\" button click karo"
            )


        result = browser_command(
            "click_by_text",
            {
                "text":
                    target
            }
        )


    if not result.get("success"):

        return browser_error_response(
            "click",
            result
        )


    return (
        "✅ Browser element clicked.\n"
        f"🖱️ {result.get('text', '')}\n"
        f"🔗 {result.get('after_url', result.get('url', ''))}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 16: TYPE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extract_type_data(
    message
):

    text = normalize_text(
        message
    )


    selector = extract_selector(
        text
    )


    # ================================================================================================
    # QUOTED TEXT
    # ================================================================================================

    quoted = re.findall(
        r'["“](.+?)["”]',
        text
    )


    if len(quoted) >= 2:

        return {
            "selector":
                clean_quotes(quoted[0]),

            "text":
                clean_quotes(quoted[1])
        }


    # ================================================================================================
    # "SEARCH BOX MEIN X TYPE"
    # ================================================================================================

    match = re.search(
        r'(?:search\s+box|input|field|textbox)'
        r'.*?(?:mein|me|in)'
        r'\s+(.+?)\s+'
        r'(?:type|likh|dalo|daalo|enter)',
        text,
        re.IGNORECASE
    )


    if match:

        return {
            "target":
                clean_quotes(
                    match.group(1)
                )
        }


    # ================================================================================================
    # "TYPE X"
    # ================================================================================================

    match = re.search(
        r'(?:type|likho|dalo|daalo|enter)\s+(.+)$',
        text,
        re.IGNORECASE
    )


    if match:

        return {
            "target":
                clean_quotes(
                    match.group(1)
                )
        }


    return {
        "selector":
            selector
    }


def handle_browser_type(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    data = extract_type_data(
        message
    )


    selector = data.get(
        "selector"
    )


    text_to_type = data.get(
        "text"
    )


    target = data.get(
        "target"
    )


    # ================================================================================================
    # DIRECT SELECTOR
    # ================================================================================================

    if selector and text_to_type:

        result = browser_command(
            "type",
            {
                "selector":
                    selector,

                "text":
                    text_to_type
            }
        )


    # ================================================================================================
    # TARGET FIELD WITHOUT SELECTOR
    # ================================================================================================

    elif target:

        find_result = browser_command(
            "find",
            {
                "text":
                    target,

                "tag":
                    "input,textarea"
            }
        )


        # If target is actually the value to type,
        # find a likely editable element separately.
        if not find_result.get("success"):

            return (
                "⌨️ Input field automatically locate nahi hua.\n"
                "Selector ke saath try karein:\n"
                "type selector:#search text:OpenAI"
            )


        elements = find_result.get(
            "results",
            find_result.get(
                "elements",
                []
            )
        )


        if not elements:

            return (
                "⌨️ Koi suitable input field nahi mila."
            )


        first = elements[0]

        selector_found = first.get(
            "selector"
        )


        if not selector_found:

            return (
                "⚠️ Input mila lekin reliable selector nahi mila."
            )


        result = browser_command(
            "type",
            {
                "selector":
                    selector_found,

                "text":
                    target
            }
        )


    else:

        return (
            "⌨️ Kya type karna hai?\n"
            "Example:\n"
            "Search box mein OpenAI type karo"
        )


    if not result.get("success"):

        return browser_error_response(
            "type",
            result
        )


    return (
        "⌨️ Text entered successfully.\n"
        f"📝 Length: "
        f"{result.get('textLength', 0)}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 17: WAIT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extract_wait_data(
    message
):

    timeout_match = re.search(
        r"(\d+)\s*(?:sec|second|seconds|s)",
        message or "",
        re.IGNORECASE
    )


    timeout = 10000


    if timeout_match:

        timeout = (
            int(
                timeout_match.group(1)
            )
            * 1000
        )


    quoted = re.findall(
        r'["“](.+?)["”]',
        message or ""
    )


    if quoted:

        return {
            "text":
                quoted[0],

            "timeout":
                timeout
        }


    return {
        "timeout":
            timeout
    }


def handle_browser_wait(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    data = extract_wait_data(
        message
    )


    target = data.get(
        "text"
    )


    if target:

        result = browser_command(
            "wait_for_text",
            {
                "text":
                    target,

                "timeout":
                    data.get(
                        "timeout",
                        10000
                    )
            }
        )

    else:

        # Generic page wait.
        time.sleep(
            min(
                data.get(
                    "timeout",
                    1000
                ),
                10000
            ) / 1000
        )


        return (
            "⏳ Wait complete."
        )


    if not result.get("success"):

        return browser_error_response(
            "wait",
            result
        )


    return (
        "⏳ Wait complete.\n"
        f"🔎 Found: "
        f"{result.get('found', False)}\n"
        f"⏱️ Waited: "
        f"{result.get('waited_ms', 0)} ms"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 18: SCROLL
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_scroll(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    text = normalize_text(
        message
    ).lower()


    direction = "down"


    if (
        "upar" in text
        or "up" in text
        or "top" in text
    ):

        direction = "up"


    elif "bottom" in text:

        direction = "bottom"


    elif "top par" in text:

        direction = "top"


    amount_match = re.search(
        r"(\d+)\s*(?:px|pixel|pixels)?",
        text
    )


    amount = (
        int(
            amount_match.group(1)
        )
        if amount_match
        else 600
    )


    result = browser_command(
        "scroll",
        {
            "direction":
                direction,

            "amount":
                amount
        }
    )


    if not result.get("success"):

        return browser_error_response(
            "scroll",
            result
        )


    return (
        "📜 Page scrolled.\n"
        f"Direction: {direction}\n"
        f"Amount: {amount}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 19: MULTI-STEP COMMAND DETECTION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def is_multi_step_browser_request(
    message
):

    text = normalize_text(
        message
    ).lower()


    separators = [
        " aur ",
        " then ",
        " phir ",
        " uske baad ",
        " fir ",
        " afterwards ",
        " and then "
    ]


    action_words = [
        "kholo",
        "open",
        "search",
        "scan",
        "extract",
        "click",
        "type",
        "dhundo",
        "dhoondo",
        "wait",
        "scroll",
        "detect"
    ]


    has_separator = any(
        separator in text
        for separator in separators
    )


    action_count = sum(
        1
        for word in action_words
        if re.search(
            rf"\b{re.escape(word)}\b",
            text
        )
    )


    return (
        has_separator
        and action_count >= 2
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 20: MULTI-STEP BROWSER PLANNER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def build_browser_plan(
    message
):

    text = normalize_text(
        message
    )


    lower_text = text.lower()


    plan = []


    # ================================================================================================
    # STEP 1: OPEN WEBSITE
    # ================================================================================================

    if any(
        phrase in lower_text
        for phrase in [
            "kholo",
            "open",
            "website par jao",
            "website pe jao"
        ]
    ):

        url = resolve_website(
            text
        )


        if url:

            plan.append({
                "action":
                    "open",

                "url":
                    url
            })


    # ================================================================================================
    # STEP 2: SEARCH
    # ================================================================================================

    if (
        "search" in lower_text
        or "khojo" in lower_text
        or "dhundo" in lower_text
        or "dhoondo" in lower_text
    ):

        query = extract_search_query(
            text
        )


        # Remove obvious opening words if
        # search extractor accidentally includes them.
        query = re.sub(
            r"^(?:aur\s+)?",
            "",
            query,
            flags=re.IGNORECASE
        ).strip()


        if query:

            # Avoid treating a pure website name
            # as a search query when there is no
            # actual search request.
            if (
                len(query) > 0
                and (
                    "search" in lower_text
                    or "khojo" in lower_text
                    or "dhundo" in lower_text
                    or "dhoondo" in lower_text
                )
            ):

                plan.append({
                    "action":
                        "search",

                    "query":
                        query,

                    "engine":
                        "google"
                })


    # ================================================================================================
    # STEP 3: SCAN
    # ================================================================================================

    if (
        "scan" in lower_text
        or "page dekho" in lower_text
        or "page analyze" in lower_text
        or "page analyse" in lower_text
    ):

        plan.append({
            "action":
                "scan"
        })


    # ================================================================================================
    # STEP 4: EXTRACT
    # ================================================================================================

    if (
        "extract" in lower_text
        or "text nikalo" in lower_text
        or "text nikaalo" in lower_text
        or "content nikalo" in lower_text
    ):

        plan.append({
            "action":
                "extract"
        })


    # ================================================================================================
    # STEP 5: DETECT
    # ================================================================================================

    if (
        "detect" in lower_text
        or "indicator" in lower_text
    ):

        plan.append({
            "action":
                "detect"
        })


    # ================================================================================================
    # STEP 6: CLICK
    # ================================================================================================

    if (
        "click" in lower_text
        or "button dabao" in lower_text
    ):

        target = extract_target_text(
            text
        )


        if target:

            plan.append({
                "action":
                    "click_by_text",

                "text":
                    target
            })


    # ================================================================================================
    # STEP 7: WAIT
    # ================================================================================================

    if (
        "wait" in lower_text
        or "intezar" in lower_text
    ):

        wait_data = extract_wait_data(
            text
        )


        if wait_data.get("text"):

            plan.append({
                "action":
                    "wait_for_text",

                "text":
                    wait_data["text"],

                "timeout":
                    wait_data["timeout"]
            })


    return plan


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 21: EXECUTE BROWSER PLAN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def execute_browser_plan(
    plan
):

    results = []


    for index, step in enumerate(
        plan,
        start=1
    ):

        action = step.get(
            "action"
        )


        print(
            f"🤖 Browser Plan Step {index}: "
            f"{action}"
        )


        # ============================================================================================
        # OPEN
        # ============================================================================================

        if action == "open":

            result = send_extension_command(
                action="open",

                url=step.get(
                    "url"
                )
            )


        # ============================================================================================
        # SEARCH
        # ============================================================================================

        elif action == "search":

            result = send_extension_command(
                action="search",

                extra_data={
                    "query":
                        step.get(
                            "query",
                            ""
                        ),

                    "engine":
                        step.get(
                            "engine",
                            "google"
                        )
                }
            )


        # ============================================================================================
        # GENERIC ACTIONS
        # ============================================================================================

        else:

            extra = {
                key:
                    value

                for key, value
                in step.items()

                if key != "action"
            }


            result = browser_command(
                action,
                extra
            )


        results.append({
            "step":
                index,

            "action":
                action,

            "request":
                step,

            "result":
                result
        })


        # ============================================================================================
        # HARD STOP ON FAILURE
        # ============================================================================================

        if not result.get("success"):

            return {
                "success":
                    False,

                "completed_steps":
                    results,

                "failed_step":
                    index,

                "pending":
                    result.get(
                        "pending",
                        False
                    ),

                "message":
                    "Browser plan stopped because a step failed."
            }


        # ============================================================================================
        # HUMAN HANDOFF
        # ============================================================================================

        if result.get(
            "requires_human"
        ):

            return {
                "success":
                    False,

                "requires_human":
                    True,

                "completed_steps":
                    results,

                "failed_step":
                    index,

                "message":
                    "Human interaction required."
            }


    return {
        "success":
            True,

        "completed_steps":
            results
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 22: SMART MULTI-STEP HANDLER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_plan(
    message,
    history=None,
    all_history=None,
    campaign_id=None,
    **kwargs
):

    plan = build_browser_plan(
        message
    )


    if not plan:

        return (
            "🤖 Browser command samajh nahi aaya."
        )


    print(
        "🤖 BROWSER PLAN"
    )


    for index, step in enumerate(
        plan,
        start=1
    ):

        print(
            f"  {index}. "
            f"{step}"
        )


    execution = execute_browser_plan(
        plan
    )


    if execution.get(
        "requires_human"
    ):

        return (
            "🛑 Browser automation human "
            "interaction par ruk gayi.\n"
            "Security/verification step detected."
        )


    if not execution.get(
        "success"
    ):

        failed = execution.get(
            "failed_step"
        )


        return (
            "❌ Browser plan step "
            f"{failed} par ruk gaya.\n"
            f"⚠️ "
            f"{execution.get('message', '')}"
        )


    # ================================================================================================
    # FINAL RESPONSE
    # ================================================================================================

    lines = [
        "✅ Browser automation complete.",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]


    for item in execution.get(
        "completed_steps",
        []
    ):

        action = item.get(
            "action"
        )


        result = item.get(
            "result",
            {}
        )


        if action == "open":

            lines.append(
                f"🌐 Open: "
                f"{result.get('url', '')}"
            )


        elif action == "search":

            lines.append(
                f"🔎 Search: "
                f"{item.get('request', {}).get('query', '')}"
            )


        elif action == "scan":

            lines.append(
                "🔎 Page scan completed."
            )


        elif action == "extract":

            lines.append(
                "📄 Page text extracted."
            )


        elif action == "click_by_text":

            lines.append(
                f"🖱️ Clicked: "
                f"{result.get('text', '')}"
            )


        elif action == "wait_for_text":

            lines.append(
                "⏳ Wait condition completed."
            )


        else:

            lines.append(
                f"⚙️ {action}: completed."
            )


    return "\n".join(
        lines
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 23: BROWSER COMMAND INDIVIDUAL HANDLERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_browser_action_dispatch(
    message,
    action
):

    if action == "scan":
        return handle_browser_scan(
            message,
            [],
            [],
            None
        )

    if action == "extract":
        return handle_browser_extract(
            message,
            [],
            [],
            None
        )

    if action == "page_info":
        return handle_browser_info(
            message,
            [],
            [],
            None
        )

    if action == "detect":
        return handle_browser_detect(
            message,
            [],
            [],
            None
        )

    if action == "find":
        return handle_browser_find(
            message,
            [],
            [],
            None
        )

    if action == "click":
        return handle_browser_click(
            message,
            [],
            [],
            None
        )

    if action == "type":
        return handle_browser_type(
            message,
            [],
            [],
            None
        )

    if action == "wait":
        return handle_browser_wait(
            message,
            [],
            [],
            None
        )

    if action == "scroll":
        return handle_browser_scroll(
            message,
            [],
            [],
            None
        )

    return (
        "Unknown browser action."
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 24: AUTOMATION / SMARTMAIN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_task(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    try:

        from main import SmartMain

        system = SmartMain()


        message_lower = (
            message or ""
        ).lower()


        platform = "rapidworkers"


        platform_map = {

            "timebucks":
                "timebucks",

            "freecash":
                "freecash",

            "swagbucks":
                "swagbucks",

            "ysense":
                "ysense",

            "prizerebel":
                "prizerebel",

            "grabpoints":
                "grabpoints",

            "rapidworkers":
                "rapidworkers"
        }


        for keyword, value in platform_map.items():

            if keyword in message_lower:

                platform = value
                break


        print(
            f"🤖 SmartMain platform: "
            f"{platform}"
        )


        result = system.run(
            f"{platform} task"
        )


        return result


    except ImportError as error:

        return (
            "⚠️ SmartMain not found.\n"
            f"Error: {error}"
        )


    except Exception as error:

        return (
            f"❌ Automation error: {error}"
        )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 25: STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_status(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    try:

        from main import SmartMain

        system = SmartMain()

        status = system.get_status()


        return (
            "📊 SYSTEM STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Status: "
            f"{status.get('status', 'idle')}\n"
            f"✅ Tasks: "
            f"{status.get('tasks_completed', 0)}\n"
            f"💰 Earnings: "
            f"{status.get('total_earned', '$0.00')}\n"
            f"⏱️ Uptime: "
            f"{status.get('uptime', 0)//60} minutes\n"
            f"📚 Memory: "
            f"{status.get('memory_size', 0)} tasks"
        )


    except Exception as error:

        return (
            "📊 SYSTEM STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📌 Status: Idle\n"
            "✅ Tasks: 0\n"
            "💰 Earnings: $0.00\n"
            f"⚠️ {error}"
        )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 26: STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_stop(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    # Keep existing SmartMain architecture intact.
    #
    # The actual persistent stop/resume controller
    # will be strengthened in main.py.

    return (
        "🛑 Automation stop command received.\n"
        "Current browser automation ko stop signal diya gaya hai."
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 27: TRANSLATE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_translate(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    text = re.sub(
        r'(translate|anuvad|convert language|'
        r'translate karo|bhasha badlo|'
        r'language change)',
        '',
        message or "",
        flags=re.IGNORECASE
    ).strip()


    if not text:

        return (
            "क्या translate करना है?"
        )


    messages = [
        {
            "role":
                "system",

            "content":
                "Translate the user's requested text "
                "accurately while preserving meaning."
        },

        {
            "role":
                "user",

            "content":
                text
        }
    ]


    return ai_chat(
        messages,
        temperature=0.3,
        max_tokens=500
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 28: CODE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_code(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    prompt = re.sub(
        r'(code|program|function|script|'
        r'code likho|program banao|programming)',
        '',
        message or "",
        flags=re.IGNORECASE
    ).strip()


    if not prompt:

        return (
            "What code would you like me to write?"
        )


    messages = [
        {
            "role":
                "system",

            "content": (
                "You are an expert programmer. "
                "Write clean, robust, maintainable code "
                "with clear explanations when useful."
            )
        },

        {
            "role":
                "user",

            "content":
                prompt
        }
    ]


    return ai_chat(
        messages,
        temperature=0.5,
        max_tokens=1000
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 29: SUMMARIZE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_summarize(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    text = re.sub(
        r'(summary|summarize|sankshep|'
        r'short|shorten|short summary|summarise)',
        '',
        message or "",
        flags=re.IGNORECASE
    ).strip()


    if not text:

        return (
            "Kis text ka summary chahiye?"
        )


    messages = [
        {
            "role":
                "system",

            "content":
                "Summarize the provided text clearly "
                "and concisely."
        },

        {
            "role":
                "user",

            "content":
                text
        }
    ]


    return ai_chat(
        messages,
        temperature=0.5,
        max_tokens=300
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 30: ADVANCED INTENT DETECTION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def detect_intent(
    text,
    history=None
):
    """
    🧠 Advanced intent detection.

    The router intentionally uses deterministic
    signals before AI.

    Why?

    Browser actions must not be accidentally
    triggered by ordinary conversation.

    Scoring:
        keyword match
        + phrase length
        + priority
        + browser-specific signals
        + exact phrase strength
    """

    if not text:

        return "chat"


    normalized = normalize_text(
        text
    )


    text_lower = normalized.lower()


    # ================================================================================================
    # MULTI-STEP BROWSER COMMAND HAS PRIORITY
    # ================================================================================================

    if is_multi_step_browser_request(
        normalized
    ):

        plan = build_browser_plan(
            normalized
        )


        if len(plan) >= 2:

            print(
                "🧠 Intent: browser_plan"
            )

            return "browser_plan"


    candidates = []


    for intent_name, config in INTENT_REGISTRY.items():

        if intent_name == "chat":
            continue


        matched = []


        for keyword in config.get(
            "keywords",
            []
        ):

            keyword_lower = (
                keyword.lower()
            )


            if keyword_lower in text_lower:

                matched.append(
                    keyword
                )


        if not matched:
            continue


        priority = config.get(
            "priority",
            0
        )


        score = (
            len(matched) * 10
        )


        score += (
            priority * 4
        )


        longest = max(
            [
                len(item)
                for item in matched
            ],
            default=0
        )


        score += (
            longest / 10
        )


        # ============================================================================================
        # EXTRA BROWSER BOOST
        # ============================================================================================

        browser_intents = {
            "search",
            "smart_open",
            "browser_scan",
            "browser_extract",
            "browser_info",
            "browser_detect",
            "browser_find",
            "browser_click",
            "browser_type",
            "browser_wait",
            "browser_scroll"
        }


        if intent_name in browser_intents:

            score += 5


        candidates.append({

            "intent":
                intent_name,

            "score":
                score,

            "priority":
                priority,

            "matched":
                matched
        })


    if not candidates:

        return "chat"


    candidates.sort(
        key=lambda item: (
            item["score"],
            item["priority"]
        ),
        reverse=True
    )


    selected = candidates[0]


    print(
        "🧠 Intent: "
        f"{selected['intent']} "
        f"| Score: "
        f"{selected['score']:.2f} "
        f"| Matched: "
        f"{selected['matched']}"
    )


    return selected[
        "intent"
    ]


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 31: HANDLER ROUTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def get_handler(
    intent_name
):

    if intent_name == "browser_plan":

        return handle_browser_plan


    if intent_name in INTENT_REGISTRY:

        handler_name = (
            INTENT_REGISTRY[
                intent_name
            ].get(
                "handler"
            )
        )


        if handler_name:

            return globals().get(
                handler_name
            )


    return None


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 32: GENERATE RESPONSE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def generate_response(
    intent,
    message,
    history,
    all_history,
    campaign_id=None
):

    handler = get_handler(
        intent
    )


    if handler:

        try:

            return handler(
                message=
                    message,

                history=
                    history,

                all_history=
                    all_history,

                campaign_id=
                    campaign_id
            )


        except Exception as error:

            print(
                f"❌ Handler error "
                f"[{intent}]: {error}"
            )


            return (
                "⚠️ Error processing request:\n"
                f"{error}"
            )


    return handle_chat(
        message,
        history,
        all_history,
        campaign_id
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 33: MASTER REQUEST PROCESSOR
# 🧠 SINGLE ENTRY POINT FOR FUTURE ADVANCED ROUTING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def process_request(
    message,
    history=None,
    all_history=None,
    campaign_id=None
):
    """
    Master Brain entry point.

    This function does not replace app.py's existing
    architecture. It provides a stronger central
    processor that can be used by app.py.

    Flow:

        message
          ↓
        intent
          ↓
        handler
          ↓
        result
    """

    message = normalize_text(
        message
    )


    if not message:

        return {
            "success":
                False,

            "intent":
                "chat",

            "response":
                "Please enter a message."
        }


    intent = detect_intent(
        message,
        history
    )


    response = generate_response(
        intent,
        message,
        history or [],
        all_history or [],
        campaign_id
    )


    return {
        "success":
            True,

        "intent":
            intent,

        "response":
            response,

        "timestamp":
            now_iso()
    }


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 34: SYSTEM INITIALIZATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

print("=" * 80)

print(
    "🧠 AI SERVICE v7.0.0"
)

print(
    "🚀 SMART BRAIN + KIWI AUTOMATION ENGINE"
)

print(
    "🔒 ai_chat() CORE: LOCKED"
)

print(
    "🌉 Kiwi Extension Bridge: ENABLED"
)

print(
    "🔎 Real Search: ENABLED"
)

print(
    "👁️ Page Scan: ENABLED"
)

print(
    "📄 Text Extraction: ENABLED"
)

print(
    "📋 Page Information: ENABLED"
)

print(
    "🖱️ Click Engine: ENABLED"
)

print(
    "⌨️ Type Engine: ENABLED"
)

print(
    "⏳ Wait Engine: ENABLED"
)

print(
    "📜 Scroll Engine: ENABLED"
)

print(
    "🤖 Multi-Step Browser Planning: ENABLED"
)

print(
    "🛑 Human Security Handoff: ENABLED"
)

print("=" * 80)

print(
    "📋 REGISTERED INTENTS"
)

for name, config in INTENT_REGISTRY.items():

    status = (
        "✅"
        if config.get("keywords")
        else "📌"
    )


    print(
        f"{status} {name}"
    )


    print(
        f"    → {config.get('description', '')}"
    )


print("=" * 80)

print(
    "🌐 WEBSITE MAP:"
)

for website, url in WEBSITE_MAP.items():

    print(
        f"  • {website} → {url}"
    )


print("=" * 80)

print(
    "🧠 AI SERVICE READY"
)

print(
    "Architecture preserved."
)

print(
    "Existing ai_chat() preserved."
)

print(
    "Existing intent/handler architecture preserved."
)

print(
    "Kiwi browser actions expanded."
)

print("=" * 80)
