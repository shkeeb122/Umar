# ====================================================================
# 📁 FILE: health_service.py
# 🎯 ROLE: DOCTOR - System health check, problem detection, auto-fix
# 🔗 USED BY: app.py (new routes)
# 🔗 USES: db.py, config.py
# 📋 TOTAL FUNCTIONS: 12
# 🏥 AUTO-DETECTS: Files, Functions, Tables, Columns, Routes, APIs
# ====================================================================

import os
import glob
import sqlite3
import time
import requests
import importlib
import inspect
from datetime import datetime

# ================= CONFIGURATION =================
try:
    from config import BACKEND_URL, MISTRAL_URL, DATABASE_FILE
except:
    BACKEND_URL = "http://localhost:5000"
    MISTRAL_URL = "https://api.mistral.ai"
    DATABASE_FILE = "ai_system.db"

# ================= CRITICAL REQUIREMENTS =================
# Sirf yeh manual batane padenge - Baaki sab automatic!

CRITICAL_FILES = ["app.py", "ai_service.py", "db.py", "config.py"]
CRITICAL_TABLES = ["campaigns", "messages"]
CRITICAL_COLUMNS = {
    "campaigns": ["id", "title", "created_at", "is_deleted"],
    "messages": ["id", "campaign_id", "role", "content", "timestamp"]
}
VALID_VALUES = {
    "messages.role": ["user", "assistant"],
    "campaigns.is_deleted": [0, 1]
}

# ================= AUTO-DISCOVERY FUNCTIONS =================

def discover_files():
    """Auto-discover all Python files"""
    return glob.glob("*.py")

def discover_functions(file_name):
    """Auto-discover all functions in a file"""
    try:
        module_name = file_name.replace('.py', '')
        module = importlib.import_module(module_name)
        functions = []
        for name, obj in inspect.getmembers(module):
            if inspect.isfunction(obj) and not name.startswith('_'):
                functions.append(name)
        return functions
    except:
        return []

def discover_tables():
    """Auto-discover all tables from database"""
    if not os.path.exists(DATABASE_FILE):
        return []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except:
        return []

def discover_columns(table_name):
    """Auto-discover all columns in a table"""
    if not os.path.exists(DATABASE_FILE):
        return []
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
        conn.close()
        return columns
    except:
        return []

def discover_routes():
    """Auto-discover all Flask routes"""
    try:
        import app
        routes = []
        for rule in app.app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    "path": rule.rule,
                    "methods": list(rule.methods - {'HEAD', 'OPTIONS'})
                })
        return routes
    except:
        return []

# ================= PROBLEM DETECTION FUNCTIONS =================

def check_file_problems(file_name):
    """Check individual file for problems"""
    problems = []
    
    if not os.path.exists(file_name):
        problems.append({
            "location": f"📁 {file_name}",
            "issue": "File missing",
            "severity": "critical",
            "fix": f"Restore {file_name} from backup"
        })
        return problems
    
    if os.path.getsize(file_name) == 0:
        problems.append({
            "location": f"📁 {file_name}",
            "issue": "File is empty (0 bytes)",
            "severity": "warning",
            "fix": f"Restore {file_name} content"
        })
    
    try:
        module_name = file_name.replace('.py', '')
        importlib.import_module(module_name)
    except SyntaxError as e:
        problems.append({
            "location": f"📁 {file_name} (line {e.lineno})",
            "issue": f"Syntax error: {str(e)[:50]}",
            "severity": "critical",
            "fix": f"Fix syntax at line {e.lineno}"
        })
    except Exception as e:
        problems.append({
            "location": f"📁 {file_name}",
            "issue": f"Import error: {str(e)[:50]}",
            "severity": "critical",
            "fix": "Check missing imports or dependencies"
        })
    
    return problems

def check_database_problems():
    """Check database for problems"""
    problems = []
    
    if not os.path.exists(DATABASE_FILE):
        problems.append({
            "location": "🗄️ Database",
            "issue": f"{DATABASE_FILE} file missing",
            "severity": "critical",
            "fix": "Run init_db() to recreate database"
        })
        return problems
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Check required tables
        existing_tables = discover_tables()
        for table in CRITICAL_TABLES:
            if table not in existing_tables:
                problems.append({
                    "location": f"🗄️ {table}",
                    "issue": "Required table missing",
                    "severity": "critical",
                    "fix": f"CREATE TABLE {table} (...)"
                })
        
        # Check required columns
        for table, req_cols in CRITICAL_COLUMNS.items():
            if table in existing_tables:
                cols = discover_columns(table)
                col_names = [c["name"] for c in cols]
                for req_col in req_cols:
                    if req_col not in col_names:
                        problems.append({
                            "location": f"🗄️ {table}.{req_col}",
                            "issue": "Required column missing",
                            "severity": "critical",
                            "fix": f"ALTER TABLE {table} ADD COLUMN {req_col}"
                        })
        
        # Check NULL values
        for table in existing_tables:
            cols = discover_columns(table)
            for col in cols:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col['name']} IS NULL")
                    null_count = cursor.fetchone()[0]
                    if null_count > 0:
                        problems.append({
                            "location": f"🗄️ {table}.{col['name']}",
                            "issue": f"{null_count} rows have NULL value",
                            "severity": "warning",
                            "fix": f"UPDATE {table} SET {col['name']}=DEFAULT WHERE {col['name']} IS NULL"
                        })
                except:
                    pass
        
        # Check invalid values
        for col_path, valid_list in VALID_VALUES.items():
            if '.' in col_path:
                table, col = col_path.split('.')
                if table in existing_tables:
                    placeholders = ','.join(['?']*len(valid_list))
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} NOT IN ({placeholders}) AND {col} IS NOT NULL", valid_list)
                        invalid_count = cursor.fetchone()[0]
                        if invalid_count > 0:
                            problems.append({
                                "location": f"🗄️ {table}.{col}",
                                "issue": f"{invalid_count} rows have invalid value (expected: {valid_list})",
                                "severity": "critical",
                                "fix": f"UPDATE {table} SET {col}='{valid_list[0]}' WHERE {col} NOT IN {valid_list}"
                            })
                    except:
                        pass
        
        conn.close()
    except Exception as e:
        problems.append({
            "location": "🗄️ Database",
            "issue": f"Connection error: {str(e)[:50]}",
            "severity": "critical",
            "fix": "Check database file permissions"
        })
    
    return problems

def check_api_problems():
    """Check external APIs"""
    problems = []
    
    # Check Backend
    try:
        start = time.time()
        r = requests.get(f"{BACKEND_URL}/ping", timeout=5)
        resp_time = (time.time() - start) * 1000
        
        if r.status_code != 200:
            problems.append({
                "location": "🌐 Backend API",
                "issue": f"Returned status {r.status_code}",
                "severity": "critical",
                "fix": "Check backend server logs"
            })
        elif resp_time > 2000:
            problems.append({
                "location": "🌐 Backend API",
                "issue": f"Slow response ({resp_time:.0f}ms)",
                "severity": "warning",
                "fix": "Check server load or network"
            })
    except:
        problems.append({
            "location": "🌐 Backend API",
            "issue": "Unreachable",
            "severity": "critical",
            "fix": "Start backend server"
        })
    
    return problems

# ================= AUTO-FIX FUNCTIONS =================

def auto_fix_all():
    """Auto-fix common issues"""
    fixes = []
    
    if not os.path.exists(DATABASE_FILE):
        return [{"status": "error", "message": "Database file missing, cannot auto-fix"}]
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        # Fix NULL titles
        cursor.execute("UPDATE campaigns SET title='Untitled Chat' WHERE title IS NULL OR title=''")
        if cursor.rowcount > 0:
            fixes.append(f"Fixed {cursor.rowcount} empty campaign titles")
        
        # Fix NULL is_deleted
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE is_deleted IS NULL")
        if cursor.rowcount > 0:
            fixes.append(f"Fixed {cursor.rowcount} NULL is_deleted values")
        
        # Fix invalid roles
        cursor.execute("UPDATE messages SET role='user' WHERE role NOT IN ('user','assistant')")
        if cursor.rowcount > 0:
            fixes.append(f"Fixed {cursor.rowcount} invalid message roles")
        
        conn.commit()
        conn.close()
    except Exception as e:
        fixes.append(f"Error: {str(e)[:50]}")
    
    return fixes

# ================= MAIN REPORT FUNCTION =================

def get_full_health_report():
    """Generate complete health report"""
    
    all_problems = []
    
    # Discover everything
    files = discover_files()
    tables = discover_tables()
    routes = discover_routes()
    
    # Check each file
    file_status = {}
    for file_name in files:
        problems = check_file_problems(file_name)
        all_problems.extend(problems)
        file_status[file_name] = {
            "exists": os.path.exists(file_name),
            "size": os.path.getsize(file_name) if os.path.exists(file_name) else 0,
            "functions": discover_functions(file_name),
            "problems": len(problems)
        }
    
    # Check database
    db_problems = check_database_problems()
    all_problems.extend(db_problems)
    
    # Check APIs
    api_problems = check_api_problems()
    all_problems.extend(api_problems)
    
    # Categorize problems
    critical = [p for p in all_problems if p["severity"] == "critical"]
    warnings = [p for p in all_problems if p["severity"] == "warning"]
    
    # Overall health
    if critical:
        overall, emoji = "critical", "🔴"
    elif warnings:
        overall, emoji = "warning", "🟡"
    else:
        overall, emoji = "healthy", "🟢"
    
    # Count stats
    total_functions = sum(len(discover_functions(f)) for f in files)
    total_columns = sum(len(discover_columns(t)) for t in tables)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "overall": f"{emoji} {overall.upper()}",
        "overall_status": overall,
        "overall_emoji": emoji,
        "stats": {
            "files": len(files),
            "functions": total_functions,
            "tables": len(tables),
            "columns": total_columns,
            "routes": len(routes),
            "healthy": len(files) + len(tables) - len(critical) - len(warnings),
            "warnings": len(warnings),
            "critical": len(critical)
        },
        "discovered": {
            "files": files,
            "tables": tables,
            "routes": [r["path"] for r in routes]
        },
        "file_details": file_status,
        "table_details": {t: {"columns": discover_columns(t)} for t in tables},
        "problems": {
            "critical": critical,
            "warnings": warnings,
            "all": all_problems
        }
    }

def get_quick_status():
    """Fast status check"""
    report = get_full_health_report()
    return {
        "status": report["overall_status"],
        "emoji": report["overall_emoji"],
        "message": f"Files: {report['stats']['files']}, Tables: {report['stats']['tables']}, Issues: {report['stats']['critical']}",
        "critical_count": report["stats"]["critical"]
    }

# ================= PRINT FUNCTION =================

def print_report():
    """Print readable report"""
    r = get_full_health_report()
    
    print("\n" + "="*60)
    print(f"🏥 SYSTEM HEALTH: {r['overall']}")
    print("="*60)
    print(f"📊 Files: {r['stats']['files']} | Functions: {r['stats']['functions']}")
    print(f"🗄️ Tables: {r['stats']['tables']} | Columns: {r['stats']['columns']}")
    print(f"🔴 Critical: {r['stats']['critical']} | 🟡 Warnings: {r['stats']['warnings']}")
    
    if r["problems"]["critical"]:
        print("\n🔴 CRITICAL:")
        for p in r["problems"]["critical"]:
            print(f"  {p['location']}: {p['issue']}")
    
    if r["problems"]["warnings"]:
        print("\n🟡 WARNINGS:")
        for p in r["problems"]["warnings"][:3]:
            print(f"  {p['location']}: {p['issue']}")
    
    print("="*60)

# ================= RUN =================
if __name__ == "__main__":
    print_report()
