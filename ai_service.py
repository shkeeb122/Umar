# ====================================================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - Intent Detection + Response Generation + Kiwi Browser Bridge
# ====================================================================================================
#
# ARCHITECTURE:
#
# USER
#   ↓
# app.py
#   ↓
# detect_intent()
#   ↓
# INTENT HANDLER
#   ↓
# Kiwi Extension Bridge (when browser action is needed)
#   ↓
# Kiwi Browser
#
# 🔒 ai_chat() CORE API FUNCTION IS LOCKED
#
# CURRENT BROWSER ACTIONS:
#   ✅ open
#   🆕 search (backend side ready; Kiwi background.js next)
#
# ====================================================================================================


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import os
import requests
import time
import re
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME, BACKEND_URL
from db import get_recent_history, get_all_history, count_questions
from helpers import is_question, format_response, extract_topic


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

EXTENSION_RESULT_TIMEOUT = 20
EXTENSION_POLL_INTERVAL = 0.5


def send_extension_command(
    action,
    url=None,
    extra_data=None
):
    """
    🌉 Render → Kiwi Extension Bridge

    Supported now:
        open
        search

    Example:

        send_extension_command(
            action="open",
            url="https://www.google.com/"
        )

    OR:

        send_extension_command(
            action="search",
            extra_data={
                "query": "OpenAI",
                "engine": "google"
            }
        )
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
        "X-Extension-Test-Token": (
            EXTENSION_TEST_TOKEN
        ),
        "Content-Type": "application/json"
    }

    payload = {
        "action": action
    }

    if url:
        payload["url"] = url

    if isinstance(extra_data, dict):
        payload.update(extra_data)

    try:

        print("=" * 60)
        print("🌉 KIWI EXTENSION BRIDGE")
        print(f"Action: {action}")
        print(f"URL: {url}")
        print(f"Extra: {extra_data}")
        print("=" * 60)

        response = requests.post(
            EXTENSION_COMMAND_URL,
            headers=headers,
            json=payload,
            timeout=10
        )

        if response.status_code != 200:

            print(
                f"❌ Extension command failed: "
                f"{response.status_code}"
            )

            return {
                "success": False,
                "error": (
                    "Bridge command failed with "
                    f"HTTP {response.status_code}"
                )
            }

        data = response.json()

        if not data.get("success"):

            return {
                "success": False,
                "error": data.get(
                    "message",
                    "Command was not queued."
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
                "error": (
                    "Bridge did not return "
                    "a command_id."
                )
            }

        print(
            f"✅ Command queued: {command_id}"
        )

        # ------------------------------------------------------------------
        # WAIT FOR KIWI RESULT
        # ------------------------------------------------------------------

        start_time = time.time()

        while (
            time.time() - start_time
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
                                "✅ Kiwi Extension "
                                "returned result."
                            )

                            return last_result

            except requests.exceptions.RequestException as poll_error:

                print(
                    "⚠️ Bridge status "
                    f"polling error: {poll_error}"
                )

            time.sleep(
                EXTENSION_POLL_INTERVAL
            )

        print(
            "⏳ Extension result timeout: "
            f"{command_id}"
        )

        return {
            "success": False,
            "pending": True,
            "command_id": command_id,
            "message": (
                "Command was sent to Kiwi, "
                "but browser result has "
                "not arrived yet."
            )
        }

    except requests.exceptions.Timeout:

        print(
            "⏰ Extension bridge "
            "request timed out."
        )

        return {
            "success": False,
            "error": (
                "Extension bridge "
                "request timed out."
            )
        }

    except requests.exceptions.RequestException as e:

        print(
            f"❌ Extension bridge "
            f"network error: {e}"
        )

        return {
            "success": False,
            "error": (
                f"Extension bridge "
                f"network error: {e}"
            )
        }

    except Exception as e:

        print(
            f"❌ Extension bridge error: {e}"
        )

        return {
            "success": False,
            "error": str(e)
        }


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3: INTENT REGISTRY
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

INTENT_REGISTRY = {

    # ================================================================================================
    # NORMAL AI
    # ================================================================================================

    "chat": {
        "keywords": [],
        "handler": "handle_chat",
        "priority": 0,
        "description": "Default normal AI chat",
        "example": "Hello, kese ho?"
    },

    "count_questions": {
        "keywords": [
            "kitne sawal",
            "total sawal",
            "how many question",
            "sawal kitne",
            "questions count"
        ],
        "handler": "handle_count_questions",
        "priority": 1,
        "description": "Count total questions",
        "example": "Maine kitne sawal kiye?"
    },

    "recall": {
        "keywords": [
            "pehle kya hua",
            "pichle",
            "previous",
            "yaad",
            "bhool",
            "kal",
            "aaj",
            "purana"
        ],
        "handler": "handle_recall",
        "priority": 1,
        "description": "Recall chat history",
        "example": "Pehle kya hua tha?"
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
        "handler": "handle_follow_up",
        "priority": 1,
        "description": "Follow-up response",
        "example": "Aur batao"
    },

    "blog": {
        "keywords": [
            "blog",
            "article",
            "post",
            "likh",
            "blog banao",
            "article likho",
            "post likho"
        ],
        "handler": "handle_blog",
        "priority": 1,
        "description": "Generate blog",
        "example": "Blog banao car ke baare mein"
    },

    "image": {
        "keywords": [
            "image",
            "photo",
            "picture",
            "dekho",
            "image samjhao",
            "photo dekho",
            "ye kya hai"
        ],
        "handler": "handle_image",
        "priority": 1,
        "description": "Image understanding",
        "example": "Is image mein kya hai?"
    },

    # ================================================================================================
    # REAL BROWSER SEARCH
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
        "handler": "handle_search",
        "priority": 5,
        "description": "Real web search through Kiwi Browser",
        "example": "Google search karo OpenAI"
    },

    "translate": {
        "keywords": [
            "translate",
            "anuvad",
            "convert language",
            "translate karo",
            "bhasha badlo",
            "language change"
        ],
        "handler": "handle_translate",
        "priority": 1,
        "description": "Language translation",
        "example": "Translate hello to Hindi"
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
        "handler": "handle_code",
        "priority": 1,
        "description": "Code generation",
        "example": "Python code likho calculator ke liye"
    },

    "summarize": {
        "keywords": [
            "summary",
            "summarize",
            "sankshep",
            "short",
            "shorten",
            "short summary",
            "summarise"
        ],
        "handler": "handle_summarize",
        "priority": 1,
        "description": "Summarize text",
        "example": "Is article ka summary do"
    },

    # ================================================================================================
    # SMART WEBSITE / AUTOMATION
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
        "handler": "handle_smart_task",
        "priority": 3,
        "description": "Automation trigger",
        "example": "Task start karo"
    },

    "smart_open": {
        "keywords": [
            "website kholo",
            "website open",
            "kholo",
            "open",
            "jao",
            "browser",
            "google open",
            "youtube open",
            "facebook open",
            "amazon open",
            "flipkart open",
            "github open"
        ],
        "handler": "handle_smart_open",
        "priority": 4,
        "description": "Open website through Kiwi",
        "example": "Google kholo"
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
        "handler": "handle_smart_status",
        "priority": 2,
        "description": "System status",
        "example": "Status kya hai?"
    },

    "smart_stop": {
        "keywords": [
            "automation band",
            "task stop",
            "band karo",
            "stop",
            "rok do",
            "rok",
            "halt"
        ],
        "handler": "handle_smart_stop",
        "priority": 6,
        "description": "Stop automation",
        "example": "Automation band karo"
    }
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: NORMAL AI HANDLERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_chat(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    if not history:
        history = []

    current_date = datetime.now().strftime(
        "%d %B %Y"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. "
                f"Today's date is {current_date}. "
                "Respond in Hindi or English."
            )
        }
    ]

    messages.extend(
        history[-10:]
    )

    messages.append({
        "role": "user",
        "content": message
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
        + "\n".join(
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

    return (
        "Tell me more about what "
        "you'd like to know."
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

    system = (
        "You are an expert writer. "
        "Create a detailed, engaging "
        f"blog post about: {topic}"
    )

    messages = [
        {
            "role": "system",
            "content": system
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
        message
    )

    if not image_url:
        return (
            "Please provide an image URL. "
            "Example: image samjhao "
            "https://example.com/photo.jpg"
        )

    content = [
        {
            "type": "text",
            "text": (
                "Describe this image in detail."
            )
        },
        {
            "type": "image_url",
            "image_url": image_url.group(0)
        }
    ]

    messages = [
        {
            "role": "user",
            "content": content
        }
    ]

    return ai_chat(
        messages,
        temperature=0.7,
        max_tokens=500
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 🔎 REAL SEARCH HANDLER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extract_search_query(message):
    """
    Advanced search query extractor.

    Examples:

        Google search karo OpenAI
        → OpenAI

        Search karo Python automation
        → Python automation

        OpenAI search karo
        → OpenAI

        Google par OpenAI khojo
        → OpenAI

        Google mein Python ke baare mein search karo
        → Python ke baare mein

    """

    if not message:
        return ""

    query = message.strip()

    # ------------------------------------------------------------------
    # Normalize spaces
    # ------------------------------------------------------------------

    query = re.sub(
        r'\s+',
        ' ',
        query
    ).strip()

    # ------------------------------------------------------------------
    # Strong command phrases FIRST
    # ------------------------------------------------------------------

    command_patterns = [

        r'^\s*google\s+search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+par\s+search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+mein\s+search\s+kar(?:o|na)?\s*',

        r'^\s*search\s+kar(?:o|na)?\s*',

        r'^\s*google\s+par\s*',

        r'^\s*google\s+mein\s*',

        r'^\s*google\s*',

    ]

    for pattern in command_patterns:

        new_query = re.sub(
            pattern,
            '',
            query,
            count=1,
            flags=re.IGNORECASE
        )

        if new_query != query:

            query = new_query.strip()
            break

    # ------------------------------------------------------------------
    # Trailing command phrases
    # ------------------------------------------------------------------

    trailing_patterns = [

        r'\s+google\s+par\s+search\s+kar(?:o|na)?\s*$',

        r'\s+google\s+mein\s+search\s+kar(?:o|na)?\s*$',

        r'\s+search\s+kar(?:o|na)?\s*$',

        r'\s+google\s+search\s*$',

        r'\s+search\s*$',

        r'\s+khoj(?:o|na)?\s*$',

        r'\s+dhund(?:o|na)?\s*$',

        r'\s+dhoond(?:o|na)?\s*$',

        r'\s+pata\s+kar(?:o|na)?\s*$',

        r'\s+find\s*$',

    ]

    for pattern in trailing_patterns:

        query = re.sub(
            pattern,
            '',
            query,
            count=1,
            flags=re.IGNORECASE
        ).strip()

    # ------------------------------------------------------------------
    # Standalone filler words
    # ------------------------------------------------------------------

    query = re.sub(
        r'\b(search|searching|google)\b',
        ' ',
        query,
        flags=re.IGNORECASE
    )

    # Hindi command fillers
    query = re.sub(
        r'\b(?:karo|karna|karein|kijiye)\b',
        ' ',
        query,
        flags=re.IGNORECASE
    )

    # ------------------------------------------------------------------
    # Clean punctuation
    # ------------------------------------------------------------------

    query = re.sub(
        r'\s+',
        ' ',
        query
    ).strip()

    query = query.strip(
        " \t\n\r.,!?;:'\"“”‘’()[]{}"
    )

    return query


def handle_search(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):
    """
    🔎 REAL KIWI SEARCH

    Render
      ↓
    search intent
      ↓
    extract query
      ↓
    Extension Bridge
      ↓
    Kiwi
      ↓
    Google
    """

    original_message = (
        message or ""
    )

    query = extract_search_query(
        original_message
    )

    if not query:

        return (
            "🔎 Kya search karna hai?\n"
            "Example: Google search karo OpenAI"
        )

    print("=" * 70)
    print("🔎 REAL KIWI SEARCH")
    print(f"Original message: {original_message}")
    print(f"Extracted query:  {query}")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Send real browser command
    # ------------------------------------------------------------------

    result = send_extension_command(
        action="search",
        extra_data={
            "query": query,
            "engine": "google"
        }
    )

    # ------------------------------------------------------------------
    # SUCCESS
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # PENDING
    # ------------------------------------------------------------------

    if result.get("pending"):

        command_id = result.get(
            "command_id",
            "unknown"
        )

        return (
            "⏳ Search command Kiwi ko "
            "bhej di gayi hai.\n"
            f"🔎 Search: {query}\n"
            f"🆔 Command: {command_id}\n"
            "⚠️ Browser result abhi "
            "receive nahi hua."
        )

    # ------------------------------------------------------------------
    # ERROR
    # ------------------------------------------------------------------

    error = result.get(
        "error",
        result.get(
            "message",
            "Unknown extension error."
        )
    )

    return (
        "❌ Google search start "
        "nahi ho saki.\n"
        f"🔎 Search: {query}\n"
        f"⚠️ {error}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# TRANSLATE
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
        message,
        flags=re.IGNORECASE
    ).strip()

    if not text:

        return (
            "क्या translate करना है? / "
            "What would you like to translate?"
        )

    return (
        f"🔤 Translation: '{text}'\n\n"
        "(Translation integration coming soon.)"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# CODE
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
        message,
        flags=re.IGNORECASE
    ).strip()

    if not prompt:

        return (
            "What code would you like me to write?\n"
            "Example: Python code likho "
            "calculator ke liye"
        )

    system = (
        "You are an expert programmer. "
        "Write clean, efficient, "
        "well-commented code for: "
        f"{prompt}"
    )

    messages = [
        {
            "role": "system",
            "content": system
        }
    ]

    return ai_chat(
        messages,
        temperature=0.5,
        max_tokens=1000
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# SUMMARIZE
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
        message,
        flags=re.IGNORECASE
    ).strip()

    if not text:

        return (
            "What would you like me to summarize?\n"
            "Example: Is article ka summary do: [text]"
        )

    system = (
        "Summarize the following text "
        "concisely and clearly:\n\n"
        f"{text}"
    )

    messages = [
        {
            "role": "user",
            "content": system
        }
    ]

    return ai_chat(
        messages,
        temperature=0.5,
        max_tokens=300
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4.5: SMART WEBSITE MASTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_task(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):
    """
    Existing SmartMain automation.

    ⚠️ Browser automation architecture will
    later move toward Kiwi Extension.
    """

    try:

        from main import SmartMain

        system = SmartMain()

        platform = "rapidworkers"

        message_lower = (
            message.lower()
        )

        if "timebucks" in message_lower:

            platform = "timebucks"

        elif "freecash" in message_lower:

            platform = "freecash"

        elif "swagbucks" in message_lower:

            platform = "swagbucks"

        elif "ysense" in message_lower:

            platform = "ysense"

        elif "prizerebel" in message_lower:

            platform = "prizerebel"

        elif "grabpoints" in message_lower:

            platform = "grabpoints"

        result = system.run(
            f"{platform} task"
        )

        return result

    except ImportError as e:

        return (
            "⚠️ SmartMain not found. "
            "Please ensure main.py is present. "
            f"Error: {e}"
        )

    except Exception as e:

        return (
            f"❌ Error: {str(e)}"
        )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# SMART OPEN → REAL KIWI BROWSER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_open(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):
    """
    🌐 Smart Website Open

    Render
      ↓
    Extension Bridge
      ↓
    Kiwi
      ↓
    Browser
    """

    message_lower = (
        message.lower()
    )

    # ------------------------------------------------------------------
    # 1. DIRECT URL
    # ------------------------------------------------------------------

    urls = re.findall(
        r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-z]{2,})',
        message
    )

    url = None

    if urls:

        url = urls[0]

        url = url.rstrip(
            ".,!?;:)]}"
        )

        if not url.startswith(
            "http"
        ):

            url = (
                "https://" + url
            )

    # ------------------------------------------------------------------
    # 2. WEBSITE MAP
    # ------------------------------------------------------------------

    if not url:

        website_map = {

            "google":
                "https://www.google.com/",

            "youtube":
                "https://www.youtube.com/",

            "facebook":
                "https://www.facebook.com/",

            "amazon":
                "https://www.amazon.in/",

            "flipkart":
                "https://www.flipkart.com/",

            "github":
                "https://github.com/",

            "rapidworkers":
                "https://rapidworkers.com/",

            "timebucks":
                "https://timebucks.com/",

            "freecash":
                "https://freecash.com/",

            "swagbucks":
                "https://www.swagbucks.com/",

            "ysense":
                "https://www.ysense.com/"
        }

        for (
            site_name,
            site_url
        ) in website_map.items():

            if site_name in message_lower:

                url = site_url
                break

    # ------------------------------------------------------------------
    # 3. URL NOT FOUND
    # ------------------------------------------------------------------

    if not url:

        return (
            "🌐 Kaunsi website open karni hai?\n"
            "Example: Google kholo"
        )

    print("=" * 60)
    print("🌐 SMART OPEN")
    print(f"Message: {message}")
    print(f"URL: {url}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 4. SEND TO KIWI
    # ------------------------------------------------------------------

    result = send_extension_command(
        action="open",
        url=url
    )

    # ------------------------------------------------------------------
    # 5. SUCCESS
    # ------------------------------------------------------------------

    if result.get("success"):

        opened_url = result.get(
            "url",
            url
        )

        return (
            "✅ Website successfully "
            "open ho gayi.\n"
            f"🌐 {opened_url}"
        )

    # ------------------------------------------------------------------
    # 6. PENDING
    # ------------------------------------------------------------------

    if result.get("pending"):

        command_id = result.get(
            "command_id",
            "unknown"
        )

        return (
            "⏳ Command Kiwi ko bhej di "
            "gayi hai.\n"
            f"🌐 {url}\n"
            f"🆔 Command: {command_id}\n"
            "⚠️ Browser result abhi "
            "receive nahi hua."
        )

    # ------------------------------------------------------------------
    # 7. ERROR
    # ------------------------------------------------------------------

    error = result.get(
        "error",
        result.get(
            "message",
            "Unknown extension error."
        )
    )

    return (
        "❌ Website open nahi ho saki.\n"
        f"🌐 {url}\n"
        f"⚠️ {error}"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# SMART STATUS
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

        return f"""
📊 **System Status**
━━━━━━━━━━━━━━━━━━━━
📌 Status: {status.get('status', 'idle')}
✅ Tasks Done: {status.get('tasks_completed', 0)}
💰 Earning: {status.get('total_earned', '$0.00')}
⏱️ Uptime: {status.get('uptime', 0)//60} minutes
📚 Memory: {status.get('memory_size', 0)} tasks
━━━━━━━━━━━━━━━━━━━━
"""

    except Exception as e:

        return f"""
📊 **System Status**
━━━━━━━━━━━━━━━━━━━━
📌 Status: Idle
✅ Tasks Done: 0
💰 Earning: $0.00
⏱️ Uptime: 0 minutes
━━━━━━━━━━━━━━━━━━━━
⚠️ Error: {str(e)}
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# SMART STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def handle_smart_stop(
    message,
    history,
    all_history,
    campaign_id=None,
    **kwargs
):

    return (
        "🛑 Automation stopped! "
        "(System will stop after current task.)"
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 5: SMART INTENT ROUTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def detect_intent(
    text,
    history=None
):
    """
    🧠 Advanced intent detection.

    Scoring:

        keyword matches
        +
        priority
        +
        keyword length

    Examples:

        Google kholo
        → smart_open

        Google search karo OpenAI
        → search

        Task start karo
        → smart_task
    """

    if not text:

        return "chat"

    text_lower = (
        text.lower()
        .strip()
    )

    candidates = []

    for (
        intent_name,
        config
    ) in INTENT_REGISTRY.items():

        if intent_name == "chat":
            continue

        keywords = config.get(
            "keywords",
            []
        )

        priority = config.get(
            "priority",
            0
        )

        matched_keywords = []

        for keyword in keywords:

            keyword_lower = (
                keyword.lower()
            )

            # Exact word/phrase matching
            if keyword_lower in text_lower:

                matched_keywords.append(
                    keyword
                )

        if not matched_keywords:

            continue

        # ------------------------------------------------------------------
        # SCORE
        # ------------------------------------------------------------------

        score = (
            len(matched_keywords)
            * 10
        )

        score += (
            priority * 2
        )

        longest_keyword = max(
            [
                len(k)
                for k in matched_keywords
            ],
            default=0
        )

        score += (
            longest_keyword / 100
        )

        candidates.append({

            "intent":
                intent_name,

            "score":
                score,

            "priority":
                priority,

            "matched":
                matched_keywords
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
# LAYER 5.5: HANDLER ROUTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def get_handler(
    intent_name
):

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
                message=message,
                history=history,
                all_history=all_history,
                campaign_id=campaign_id
            )

        except Exception as e:

            print(
                f"❌ Handler error: {e}"
            )

            return (
                "⚠️ Error processing "
                f"request: {str(e)}"
            )

    return handle_chat(
        message,
        history,
        all_history,
        campaign_id
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 6: INITIALIZATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print(
    "🧠 AI SERVICE LOADED - "
    "SMART INTENT REGISTRY ACTIVE"
)
print(
    "🌉 KIWI EXTENSION BRIDGE ENABLED"
)
print(
    "🔎 REAL SEARCH HANDLER ENABLED"
)
print("=" * 70)

print("📋 Registered Intents:")

for (
    name,
    config
) in INTENT_REGISTRY.items():

    status = (
        "✅"
        if config.get("keywords")
        else "📌"
    )

    print(
        f"  {status} {name}: "
        f"{config['description']}"
    )

    print(
        "      → "
        f"{config.get('example', 'No example')}"
    )

print("=" * 70)
print(
    "🔵 Add/Remove Intents: "
    "INTENT_REGISTRY + HANDLERS"
)
print(
    "🔒 Core (ai_chat): NEVER CHANGE"
)
print(
    "🌐 Smart Open: "
    "Render → Kiwi → Browser"
)
print(
    "🔎 Smart Search: "
    "Render → Kiwi → Google"
)
print("=" * 70)
