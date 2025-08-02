import os
import requests
import subprocess

render_url = os.getenv("RENDER_URL")
railway_token = os.getenv("RAILWAY_TOKEN")

def is_render_alive(url):
    try:
        res = requests.get(url, timeout=10)
        return res.status_code == 200
    except:
        return False

if is_render_alive(render_url):
    print("✅ Render app live hai, kuch nahi karna.")
else:
    print("⚠ Render app down hai. Railway pe deploy kar rahe hain...")
    # Railway CLI command
    subprocess.run(f"npx railway up --service your-service-name --token {railway_token}", shell=True)
