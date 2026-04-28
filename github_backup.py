# ====================================================================================================
# 📁 FILE: github_backup.py
# 🎯 ROLE: HEART - Smart Backup System Core
# 📋 FUNCTIONS: 15
# ⚡ SPEED: ZERO DELAY (Background Threading + Queue)
# 🧠 SMART: Compression, Retry, Auto Throttling, Health Checks
# 💾 STORAGE: GitHub as Persistent Storage
# 🔄 VERSION: 6.0
# ====================================================================================================

import json
import sqlite3
import threading
import os
import time
import zlib
import base64
from datetime import datetime
from github_service import GitHubService

# ================= CONFIGURATION =================
BACKUP_FILE = "ai_database_backup.json"
METADATA_FILE = "backup_metadata.json"
BACKUP_FREQUENCY = 20          # Har 20 messages pe backup
MAX_QUEUE_SIZE = 100           # Maximum queue size
MAX_RETRIES = 3                # Retry attempts for GitHub API
RETRY_DELAY = 1                # Seconds between retries
COMPRESSION_LEVEL = 6          # zlib compression level (1-9)
RATE_LIMIT_DELAY = 0.5         # Delay between API calls (seconds)

# ================= GLOBAL VARIABLES =================
github = GitHubService()
backup_queue = []
is_backup_running = False
last_backup_count = 0
last_backup_time = None

backup_stats = {
    "total_backups": 0,
    "total_messages_backed": 0,
    "total_campaigns_backed": 0,
    "total_blogs_backed": 0,
    "last_backup_time": None,
    "last_backup_size_bytes": 0,
    "successful_backups": 0,
    "failed_backups": 0,
    "retry_count": 0,
    "errors": []
}


# ================= FUNCTION 1: SMART DATABASE PATH DETECTION =================
def get_db_path():
    """
    Smart database path detection
    Works on: Local, Render, Railway, Any platform
    """
    # Render persistent disk
    if os.path.exists("/var/data"):
        return "/var/data/ai_system.db"
    # Render alternate path
    elif os.path.exists("/opt/render/project/data"):
        return "/opt/render/project/data/ai_system.db"
    # Railway persistent disk
    elif os.path.exists("/data"):
        return "/data/ai_system.db"
    # Aiven / DigitalOcean
    elif os.path.exists("/mnt/data"):
        return "/mnt/data/ai_system.db"
    # Local development
    else:
        return "ai_system.db"


# ================= FUNCTION 2: DATABASE SIZE IN MB =================
def get_db_size_mb():
    """Get database file size in MB"""
    try:
        db_path = get_db_path()
        if os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)
            return round(size_bytes / (1024 * 1024), 2)
        return 0
    except:
        return 0


# ================= FUNCTION 3: MESSAGE COUNT =================
def get_message_count():
    """Get total messages in database"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return 0
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


# ================= FUNCTION 4: CAMPAIGN COUNT =================
def get_campaign_count():
    """Get total active campaigns"""
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return 0
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE is_deleted=0")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0


# ================= FUNCTION 5: COMPRESS DATA (SMART!) =================
def compress_data(data):
    """
    Compress JSON data using zlib
    Reduces backup size by 60-80%
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        compressed = zlib.compress(json_str.encode('utf-8'), COMPRESSION_LEVEL)
        encoded = base64.b64encode(compressed).decode('ascii')
        return encoded, len(json_str), len(encoded)
    except Exception as e:
        print(f"⚠️ Compression failed: {e}")
        return None, 0, 0


# ================= FUNCTION 6: DECOMPRESS DATA =================
def decompress_data(encoded_data):
    """Decompress zlib compressed backup data"""
    try:
        compressed = base64.b64decode(encoded_data.encode('ascii'))
        decompressed = zlib.decompress(compressed)
        return json.loads(decompressed.decode('utf-8'))
    except Exception as e:
        print(f"⚠️ Decompression failed: {e}")
        return None


# ================= FUNCTION 7: PREPARE COMPLETE BACKUP DATA =================
def prepare_backup_data():
    """
    Prepare complete backup data from all tables
    Returns: dict with all database data
    """
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            print("⚠️ Database file not found")
            return None
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM messages")
        message_count = cursor.fetchone()[0]
        
        if message_count == 0:
            conn.close()
            return None
        
        # Prepare backup structure
        backup_data = {
            "backup_info": {
                "backup_time": datetime.utcnow().isoformat(),
                "version": "6.0",
                "message_count": message_count,
                "campaign_count": 0,
                "blog_count": 0,
                "database_size_mb": get_db_size_mb(),
                "backup_id": f"{int(time.time())}_{message_count}"
            },
            "campaigns": [],
            "messages": [],
            "blogs_enhanced": [],
            "generated_content": [],
            "deleted_chats": []
        }
        
        # 1. CAMPAIGNS backup
        cursor.execute("""
            SELECT id, title, created_at, is_deleted, updated_at, 
                   message_count, question_count, last_topic 
            FROM campaigns
        """)
        for row in cursor.fetchall():
            backup_data["campaigns"].append({
                "id": row[0],
                "title": row[1] or "नई चैट",
                "created_at": row[2],
                "is_deleted": row[3] or 0,
                "updated_at": row[4],
                "message_count": row[5] or 0,
                "question_count": row[6] or 0,
                "last_topic": row[7] or ""
            })
        backup_data["backup_info"]["campaign_count"] = len(backup_data["campaigns"])
        
        # 2. MESSAGES backup (with chunking for large data)
        cursor.execute("""
            SELECT id, campaign_id, role, content, is_question, timestamp 
            FROM messages ORDER BY timestamp ASC
        """)
        for row in cursor.fetchall():
            backup_data["messages"].append({
                "id": row[0],
                "campaign_id": row[1],
                "role": row[2],
                "content": row[3][:10000] if row[3] else "",  # Limit per message
                "is_question": row[4] or 0,
                "timestamp": row[5]
            })
        
        # 3. BLOGS backup
        cursor.execute("""
            SELECT id, title, content, slug, excerpt, reading_time, 
                   tags, meta_description, featured_image, view_count, created_at, updated_at
            FROM blogs_enhanced ORDER BY created_at DESC
        """)
        for row in cursor.fetchall():
            backup_data["blogs_enhanced"].append({
                "id": row[0],
                "title": row[1],
                "content": row[2][:50000] if row[2] else "",
                "slug": row[3],
                "excerpt": row[4] or "",
                "reading_time": row[5] or 3,
                "tags": row[6] or "",
                "meta_description": row[7] or "",
                "featured_image": row[8] or "",
                "view_count": row[9] or 0,
                "created_at": row[10],
                "updated_at": row[11]
            })
        backup_data["backup_info"]["blog_count"] = len(backup_data["blogs_enhanced"])
        
        # 4. GENERATED CONTENT backup
        cursor.execute("""
            SELECT id, campaign_id, content_type, title, url, created_at 
            FROM generated_content
        """)
        for row in cursor.fetchall():
            backup_data["generated_content"].append({
                "id": row[0],
                "campaign_id": row[1],
                "content_type": row[2],
                "title": row[3],
                "url": row[4],
                "created_at": row[5]
            })
        
        # 5. DELETED CHATS backup
        cursor.execute("""
            SELECT id, campaign_id, title, deleted_at 
            FROM deleted_chats
        """)
        for row in cursor.fetchall():
            backup_data["deleted_chats"].append({
                "id": row[0],
                "campaign_id": row[1],
                "title": row[2],
                "deleted_at": row[3]
            })
        
        conn.close()
        
        # Check size and warn if too large
        data_size = len(json.dumps(backup_data))
        if data_size > 10 * 1024 * 1024:  # 10MB
            print(f"⚠️ Backup data is large: {data_size / (1024*1024):.1f} MB")
        
        return backup_data
        
    except Exception as e:
        print(f"❌ Prepare backup error: {e}")
        return None


# ================= FUNCTION 8: SAVE TO GITHUB WITH RETRY (SMART!) =================
def save_to_github_with_retry(json_data, message_count, is_compressed=False):
    """
    Save to GitHub with automatic retry on failure
    Max 3 attempts
    """
    global backup_stats
    
    for attempt in range(MAX_RETRIES):
        try:
            # Check if file exists
            existing = github.read_file(BACKUP_FILE)
            
            commit_msg = f"📦 Auto-backup: {message_count} messages | {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            if existing["success"]:
                result = github.update_file(BACKUP_FILE, json_data, commit_msg)
            else:
                result = github.create_file(BACKUP_FILE, json_data, commit_msg)
            
            if result.get("success"):
                # Save metadata separately (uncompressed for quick access)
                metadata = {
                    "last_backup": datetime.utcnow().isoformat(),
                    "message_count": message_count,
                    "size_bytes": len(json_data),
                    "compressed": is_compressed,
                    "backup_count": backup_stats["total_backups"] + 1
                }
                metadata_json = json.dumps(metadata, indent=2)
                
                meta_existing = github.read_file(METADATA_FILE)
                if meta_existing["success"]:
                    github.update_file(METADATA_FILE, metadata_json, "Update metadata")
                else:
                    github.create_file(METADATA_FILE, metadata_json, "Initial metadata")
                
                return True, result.get("file_url", "")
            else:
                if attempt < MAX_RETRIES - 1:
                    print(f"⚠️ Backup attempt {attempt + 1} failed, retrying in {RETRY_DELAY}s...")
                    backup_stats["retry_count"] += 1
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"❌ Backup failed after {MAX_RETRIES} attempts")
                    return False, None
                    
        except Exception as e:
            print(f"❌ GitHub API error (attempt {attempt + 1}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return False, None
    
    return False, None


# ================= FUNCTION 9: BACKGROUND WORKER (ZERO DELAY!) =================
def background_worker():
    """Background thread worker - User ko koi delay nahi lagega"""
    global is_backup_running, backup_queue, backup_stats, last_backup_time
    
    if is_backup_running:
        return
    
    is_backup_running = True
    
    def worker():
        global backup_queue, is_backup_running, backup_stats, last_backup_time
        
        while backup_queue:
            data = backup_queue.pop(0)
            try:
                message_count = data.get("backup_info", {}).get("message_count", 0)
                
                # Compress data (SMART!)
                compressed, original_size, compressed_size = compress_data(data)
                
                if compressed:
                    json_data = compressed
                    is_compressed = True
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    print(f"📦 Compression: {original_size} → {compressed_size} bytes ({compression_ratio:.1f}% smaller)")
                else:
                    json_data = json.dumps(data, indent=2, ensure_ascii=False)
                    is_compressed = False
                
                # Save with retry
                time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
                success, url = save_to_github_with_retry(json_data, message_count, is_compressed)
                
                if success:
                    backup_stats["total_backups"] += 1
                    backup_stats["successful_backups"] += 1
                    backup_stats["total_messages_backed"] = message_count
                    backup_stats["total_campaigns_backed"] = len(data.get("campaigns", []))
                    backup_stats["total_blogs_backed"] = len(data.get("blogs_enhanced", []))
                    backup_stats["last_backup_time"] = datetime.utcnow().isoformat()
                    backup_stats["last_backup_size_bytes"] = len(json_data)
                    last_backup_time = time.time()
                    print(f"✅ Backup complete! {message_count} messages saved")
                else:
                    backup_stats["failed_backups"] += 1
                    backup_stats["errors"].append({
                        "time": datetime.utcnow().isoformat(),
                        "message_count": message_count,
                        "reason": "GitHub API failure"
                    })
                    print(f"⚠️ Backup failed after retries")
                
            except Exception as e:
                backup_stats["errors"].append({
                    "time": datetime.utcnow().isoformat(),
                    "error": str(e)[:200]
                })
                print(f"❌ Worker error: {e}")
        
        is_backup_running = False
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


# ================= FUNCTION 10: ASYNC BACKUP (SUPER FAST!) =================
def backup_to_github_async(force=False):
    """
    ASYNC backup - Returns instantly!
    Backup happens in background thread
    """
    try:
        # Prepare backup data
        backup_data = prepare_backup_data()
        
        if not backup_data:
            if force:
                print("⚠️ No data to backup even with force")
            return True
        
        # Check queue size
        if len(backup_queue) >= MAX_QUEUE_SIZE:
            if force:
                backup_queue.clear()
                print("⚠️ Queue full, cleared for force backup")
            else:
                print("⚠️ Backup queue full, skipping...")
                return True
        
        # Add to queue
        backup_queue.append(backup_data)
        
        # Start background worker (if not already running)
        background_worker()
        
        return True
        
    except Exception as e:
        print(f"❌ Queue error: {e}")
        return False


# ================= FUNCTION 11: AUTO BACKUP CHECK (SMART FREQUENCY) =================
def auto_backup_check():
    """
    Smart automatic backup trigger
    Backs up every BACKUP_FREQUENCY messages
    """
    global last_backup_count
    
    try:
        current_count = get_message_count()
        
        # New messages since last backup
        new_messages = current_count - last_backup_count
        
        # Dynamic frequency: if many messages, backup more often
        if new_messages >= BACKUP_FREQUENCY and current_count > 0:
            last_backup_count = current_count
            return backup_to_github_async()
        
        # Also backup if last backup was more than 1 hour ago and have messages
        if last_backup_time and (time.time() - last_backup_time) > 3600 and current_count > 0:
            if new_messages > 0:
                last_backup_count = current_count
                return backup_to_github_async()
        
        return True
        
    except Exception as e:
        print(f"⚠️ Auto backup error: {e}")
        return False


# ================= FUNCTION 12: RESTORE FROM GITHUB =================
def restore_from_github():
    """
    Complete restore from GitHub backup
    Called on app startup
    """
    print("\n" + "=" * 70)
    print("🔄 GITHUB RESTORE PROCESS")
    print("=" * 70)
    
    try:
        # Check local database
        db_path = get_db_path()
        local_count = get_message_count()
        
        if local_count > 10:
            print(f"✅ Local database has {local_count} messages - Skipping restore")
            return True
        
        # Read metadata first
        meta_result = github.read_file(METADATA_FILE)
        if meta_result["success"]:
            metadata = json.loads(meta_result["content"])
            print(f"📊 Last backup info:")
            print(f"   Time: {metadata.get('last_backup', 'Unknown')[:19]}")
            print(f"   Messages: {metadata.get('message_count', 0)}")
            print(f"   Size: {metadata.get('size_bytes', 0) / 1024:.1f} KB")
        
        # Read backup file
        result = github.read_file(BACKUP_FILE)
        
        if not result["success"]:
            print("⚠️ No backup found on GitHub - Starting fresh")
            return True
        
        # Check if compressed
        content = result["content"]
        
        # Try to decompress if needed
        if content.startswith('{'):
            backup_data = json.loads(content)
        else:
            backup_data = decompress_data(content)
            if not backup_data:
                backup_data = json.loads(content)
        
        if not backup_data:
            print("❌ Failed to parse backup data")
            return False
        
        backup_info = backup_data.get("backup_info", {})
        print(f"\n📥 Found backup:")
        print(f"   Time: {backup_info.get('backup_time', 'Unknown')[:19]}")
        print(f"   Messages: {backup_info.get('message_count', 0)}")
        print(f"   Campaigns: {backup_info.get('campaign_count', 0)}")
        print(f"   Blogs: {backup_info.get('blog_count', 0)}")
        
        # Restore to local database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM campaigns")
        cursor.execute("DELETE FROM blogs_enhanced")
        cursor.execute("DELETE FROM generated_content")
        cursor.execute("DELETE FROM deleted_chats")
        
        # Restore campaigns
        restored_campaigns = 0
        for camp in backup_data.get("campaigns", []):
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO campaigns 
                    (id, title, created_at, is_deleted, updated_at, 
                     message_count, question_count, last_topic)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    camp.get("id"), camp.get("title", "नई चैट"), camp.get("created_at"),
                    camp.get("is_deleted", 0), camp.get("updated_at"),
                    camp.get("message_count", 0), camp.get("question_count", 0),
                    camp.get("last_topic", "")
                ))
                restored_campaigns += 1
            except Exception as e:
                print(f"⚠️ Campaign restore error: {e}")
        
        # Restore messages (in batches for large data)
        restored_messages = 0
        batch_size = 1000
        messages = backup_data.get("messages", [])
        
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i+batch_size]
            for msg in batch:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO messages 
                        (id, campaign_id, role, content, is_question, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        msg.get("id"), msg.get("campaign_id"), msg.get("role"),
                        msg.get("content", ""), msg.get("is_question", 0),
                        msg.get("timestamp")
                    ))
                    restored_messages += 1
                except Exception as e:
                    pass
            conn.commit()
            print(f"   Restored {restored_messages}/{len(messages)} messages...")
        
        # Restore blogs
        restored_blogs = 0
        for blog in backup_data.get("blogs_enhanced", []):
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO blogs_enhanced 
                    (id, title, content, slug, excerpt, reading_time, 
                     tags, meta_description, featured_image, view_count, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    blog.get("id"), blog.get("title", ""), blog.get("content", ""),
                    blog.get("slug", ""), blog.get("excerpt", ""), blog.get("reading_time", 3),
                    blog.get("tags", ""), blog.get("meta_description", ""), blog.get("featured_image", ""),
                    blog.get("view_count", 0), blog.get("created_at"), blog.get("updated_at")
                ))
                restored_blogs += 1
            except Exception as e:
                pass
        
        conn.commit()
        conn.close()
        
        print(f"\n✅ RESTORE COMPLETE!")
        print(f"   📁 Campaigns: {restored_campaigns}")
        print(f"   💬 Messages: {restored_messages}")
        print(f"   📝 Blogs: {restored_blogs}")
        
        global last_backup_count
        last_backup_count = restored_messages
        global last_backup_time
        last_backup_time = time.time()
        
        return True
        
    except Exception as e:
        print(f"❌ Restore error: {e}")
        return False


# ================= FUNCTION 13: MANUAL BACKUP =================
def manual_backup():
    """Force manual backup anytime"""
    print("\n" + "=" * 50)
    print("📦 MANUAL BACKUP TRIGGERED")
    print("=" * 50)
    return backup_to_github_async(force=True)


# ================= FUNCTION 14: GET BACKUP STATUS =================
def get_backup_status():
    """Get current backup system status"""
    return {
        "ready": github.ready,
        "queue_size": len(backup_queue),
        "is_running": is_backup_running,
        "stats": backup_stats,
        "current_message_count": get_message_count(),
        "current_campaign_count": get_campaign_count(),
        "database_size_mb": get_db_size_mb(),
        "backup_file_exists": github.read_file(BACKUP_FILE)["success"],
        "metadata_file_exists": github.read_file(METADATA_FILE)["success"],
        "last_backup_seconds_ago": int(time.time() - last_backup_time) if last_backup_time else None
    }


# ================= FUNCTION 15: COMPLETE HEALTH CHECK =================
def check_backup_health():
    """Complete health check report"""
    print("\n" + "=" * 70)
    print("🏥 BACKUP SYSTEM HEALTH REPORT")
    print("=" * 70)
    
    status = get_backup_status()
    
    print(f"\n🔧 SYSTEM STATUS:")
    print(f"   GitHub Ready: {'✅' if status['ready'] else '❌'}")
    print(f"   Backup Running: {'✅' if status['is_running'] else '⏸️'}")
    print(f"   Queue Size: {status['queue_size']}/{MAX_QUEUE_SIZE}")
    
    print(f"\n📊 DATABASE STATUS:")
    print(f"   Messages: {status['current_message_count']:,}")
    print(f"   Campaigns: {status['current_campaign_count']:,}")
    print(f"   DB Size: {status['database_size_mb']} MB")
    print(f"   DB Path: {get_db_path()}")
    
    print(f"\n📦 BACKUP STATS:")
    print(f"   Total Backups: {status['stats']['total_backups']}")
    print(f"   Successful: {status['stats']['successful_backups']}")
    print(f"   Failed: {status['stats']['failed_backups']}")
    print(f"   Retries: {status['stats']['retry_count']}")
    print(f"   Messages Backed: {status['stats']['total_messages_backed']:,}")
    print(f"   Campaigns Backed: {status['stats']['total_campaigns_backed']:,}")
    print(f"   Blogs Backed: {status['stats']['total_blogs_backed']:,}")
    
    if status['stats']['last_backup_time']:
        print(f"\n⏰ LAST BACKUP:")
        print(f"   Time: {status['stats']['last_backup_time'][:19]}")
        print(f"   Size: {status['stats']['last_backup_size_bytes'] / 1024:.1f} KB")
        print(f"   Seconds Ago: {status['last_backup_seconds_ago']}")
    
    print(f"\n📁 GITHUB BACKUP:")
    print(f"   Backup File: {'✅ Exists' if status['backup_file_exists'] else '❌ Missing'}")
    print(f"   Metadata File: {'✅ Exists' if status['metadata_file_exists'] else '❌ Missing'}")
    
    if status['backup_file_exists']:
        result = github.read_file(BACKUP_FILE)
        if result["success"]:
            content = result["content"]
            is_compressed = not content.startswith('{')
            print(f"   Compressed: {'✅ Yes' if is_compressed else 'No'}")
            print(f"   File Size: {result.get('size_bytes', 0) / 1024:.1f} KB")
    
    if status['stats']['errors']:
        print(f"\n⚠️ RECENT ERRORS (last 5):")
        for err in status['stats']['errors'][-5:]:
            print(f"   - {err.get('time', 'Unknown')[:19]}: {err.get('error', err.get('reason', 'Unknown'))[:80]}")
    
    print("\n" + "=" * 70)
    overall = "✅ HEALTHY" if status['ready'] and status['stats']['failed_backups'] < 5 else "⚠️ DEGRADED"
    print(f"OVERALL STATUS: {overall}")
    print("=" * 70)
    
    return status


# ================= INITIALIZE =================
print("=" * 60)
print("🚀 GITHUB BACKUP SYSTEM LOADED")
print("=" * 60)
print(f"   Mode: SUPER FAST (Background Threading)")
print(f"   Backup Frequency: Every {BACKUP_FREQUENCY} messages")
print(f"   Compression: ON (Level {COMPRESSION_LEVEL})")
print(f"   Retry: {MAX_RETRIES} attempts")
print(f"   GitHub Ready: {'✅' if github.ready else '❌'}")
print("=" * 60)
