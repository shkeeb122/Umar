import requests, time
from config import *
from db import cursor

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        start_time = time.time()
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=50)
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."

        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"AI Response time: {time.time() - start_time:.2f}s")
        return response.strip() if response else "I'm not sure how to respond."

    except Exception as e:
        print(f"AI Error: {e}")
        return "❌ Error occurred. Please try again."
