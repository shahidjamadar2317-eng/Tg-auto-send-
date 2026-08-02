import os
import shutil
import sys

# ---------- 🔥 HARD DATABASE RESET ----------
def hard_reset():
    """Pyrogram ki poori database delete karo"""
    try:
        # 1. Session files delete
        for f in os.listdir('.'):
            if f.endswith('.session') or f.endswith('.session-journal'):
                os.remove(f)
                print(f"[+] Deleted: {f}")
        
        # 2. Storage database delete
        storage_path = '.venv/lib/python3.11/site-packages/pyrogram/storage/'
        if os.path.exists(storage_path):
            for f in os.listdir(storage_path):
                if f.endswith('.db') or f.endswith('.db-journal'):
                    os.remove(os.path.join(storage_path, f))
                    print(f"[+] Deleted storage: {f}")
        
        # 3. __pycache__ delete
        for root, dirs, files in os.walk('.'):
            if '__pycache__' in dirs:
                shutil.rmtree(os.path.join(root, '__pycache__'))
                print(f"[+] Deleted: __pycache__")
        
        print("✅ HARD RESET COMPLETE!")
    except Exception as e:
        print(f"[-] Reset error: {e}")

print("🗑️ HARD RESET STARTING...")
hard_reset()
print("✅ Database cleared! Starting bot...")
# ------------------------------------------------
