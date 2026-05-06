# solve.py - Captcha solving script

import requests
import base64
import sys
import os

BACKEND_URL = "https://umar-k20u.onrender.com"
CAPTCHA_API_URL = f"{BACKEND_URL}/api/captcha/solve"

def solve_captcha(image_path):
    try:
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return None
        
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode()
        
        print(f"📤 Sending captcha...")
        
        response = requests.post(CAPTCHA_API_URL, json={"image": image_base64}, timeout=30)
        data = response.json()
        
        if data.get("success"):
            solution = data.get("solution")
            print(f"✅ SOLVED: {solution}")
            return solution
        else:
            print(f"❌ Failed: {data.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    print("="*40)
    print("🤖 CAPTCHA SOLVER")
    print("="*40)
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = input("Image path: ").strip()
    
    result = solve_captcha(image_path)
    
    if result:
        print(f"\n🎉 COPY: {result}")
