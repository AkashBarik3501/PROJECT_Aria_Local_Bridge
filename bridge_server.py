import os
import json
import uvicorn
import subprocess
import requests
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="PROJECT ARIA Local SSD Bridge & Telegram Notifier")
BASE_DIR = os.path.expanduser('~/PROJECT_ARIA')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------------------------------------------
# ⚠️ APNA TELEGRAM BOT TOKEN AUR CHAT ID YAHAN PASTE KARO
# -------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "8363085330:AAHNJpaJKLTWHgMMCe1MfVD8VDoSeYK0cuo"  # e.g. "7890123456:AAFx..."
TELEGRAM_CHAT_ID = "5495521412"      # e.g. "123456789"

def send_telegram_alert(message: str):
    """Telegram Bot API ke zariye phone par alert bhejta hai"""
    if TELEGRAM_BOT_TOKEN == "":
        print("⚠️ Telegram token missing! Notification skip ho gaya.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=payload, timeout=5)
        print("📲 [TELEGRAM] Alert sent to mobile successfully!")
    except Exception as e:
        print(f"❌ [TELEGRAM ERROR] Failed to send alert: {e}")

# Pre-approved Safe Actions
ALLOWED_ACTIONS = {
    "CHECK_DISK_SPACE": ["df", "-h", BASE_DIR],
    "LIST_OUTPUT_FILES": ["ls", "-la", OUTPUT_DIR],
    "GET_SYSTEM_UPTIME": ["uptime"],
    "GET_DATE_TIME": ["date"]
}

class ARIAPayload(BaseModel):
    filepath: str
    data: dict

def execute_safe_action(action_name: str) -> dict:
    if action_name not in ALLOWED_ACTIONS:
        print(f"⚠️ [SECURITY BLOCK] Unapproved action: {action_name}")
        send_telegram_alert(f"⚠️ *SECURITY BLOCK*\nUnapproved Action Blocked: `{action_name}`")
        return {"status": "BLOCKED", "reason": "Action not in whitelist"}

    command = ALLOWED_ACTIONS[action_name]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        print(f"✓ [ACTION EXECUTED] {action_name}")
        return {"status": "SUCCESS", "command": " ".join(command), "output": result.stdout.strip()}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

@app.post("/save_aria_log")
def save_log(payload: ARIAPayload):
    try:
        safe_filename = os.path.basename(payload.filepath)
        full_path = os.path.join(OUTPUT_DIR, safe_filename)
        
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(payload.data, f, indent=4, ensure_ascii=False)
            
        print(f"✓ [SSD WRITE SUCCESS] Struct log saved to: {full_path}")
        
        action_requested = payload.data.get("action_required", "NONE")
        response_text = payload.data.get("response", "No response text")
        action_result = None
        
        if action_requested != "NONE":
            action_result = execute_safe_action(action_requested)
            
        # 📲 Mobile Par Telegram Notification Bhejna
        action_status = action_result.get('status') if action_result else 'LOGGED'
        alert_msg = (
            f"🤖 *PROJECT ARIA ALERT*\n\n"
            f"*Response:* {response_text}\n"
            f"*Action Requested:* `{action_requested}`\n"
            f"*Execution Status:* `{action_status}`"
        )
        send_telegram_alert(alert_msg)
            
        return {"status": "success", "saved_path": full_path, "action_result": action_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)