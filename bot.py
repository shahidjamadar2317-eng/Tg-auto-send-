import os
import shutil

# ---------- FORCE CACHE CLEAR ----------
def force_clear_cache():
    try:
        # Sabhi session files delete
        for f in os.listdir('.'):
            if f.endswith('.session') or f.endswith('.session-journal'):
                os.remove(f)
                print(f"[+] Deleted: {f}")
        
        # Pyrogram storage delete
        storage_path = '.venv/lib/python3.11/site-packages/pyrogram/storage/'
        if os.path.exists(storage_path):
            for f in os.listdir(storage_path):
                if f.endswith('.db') or f.endswith('.db-journal'):
                    os.remove(os.path.join(storage_path, f))
                    print(f"[+] Deleted storage: {f}")
        
        print("✅ Cache cleared successfully!")
    except Exception as e:
        print(f"[-] Cache clear error: {e}")

print("🗑️ Force clearing cache...")
force_clear_cache()
print("✅ Done!")
# ------------------------------------------------
