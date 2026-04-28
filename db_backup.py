# ====================================================================================================
# 📁 FILE: db_backup.py
# 🎯 ROLE: BRIDGE - db.py ke liye backup functions export
# 📋 EXPORTS: 5 functions
# ====================================================================================================

from github_backup import (
    auto_backup_check,
    restore_from_github,
    manual_backup,
    check_backup_health,
    get_backup_status
)

# Export all functions for db.py to use
__all__ = [
    'auto_backup_check',
    'restore_from_github', 
    'manual_backup',
    'check_backup_health',
    'get_backup_status'
]

print("✅ DB Backup Bridge Loaded")
print(f"   Available: {', '.join(__all__)}")
