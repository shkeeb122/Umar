#!/usr/bin/env python
# ====================================================================================================
# 📁 FILE: backup_restore.py
# 🎯 ROLE: CLI TOOL - Manual backup/restore operations
# 🚀 RUN: python backup_restore.py [backup|restore|status|health|monitor]
# ====================================================================================================

import sys
import time
import os
from github_backup import manual_backup, restore_from_github, check_backup_health, get_backup_status, backup_to_github_async

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️ {text}{Colors.ENDC}")

def show_menu():
    print_header("🔄 BACKUP MANAGEMENT TOOL")
    print(f"""
{Colors.GREEN}Commands:{Colors.ENDC}
  {Colors.BOLD}backup{Colors.ENDC}   - Force manual backup
  {Colors.BOLD}restore{Colors.ENDC}  - Restore from GitHub backup  
  {Colors.BOLD}status{Colors.ENDC}   - Show backup system status
  {Colors.BOLD}health{Colors.ENDC}   - Full health check report
  {Colors.BOLD}monitor{Colors.ENDC}  - Real-time backup monitor
  {Colors.BOLD}exit{Colors.ENDC}     - Exit tool

{Colors.WARNING}Tip: Use 'python backup_restore.py <command>' directly{Colors.ENDC}
""")

def cmd_backup():
    """Manual backup command"""
    print_header("📦 MANUAL BACKUP")
    print_info("Starting manual backup...")
    result = manual_backup()
    if result:
        print_success("Backup completed successfully!")
    else:
        print_error("Backup failed!")

def cmd_restore():
    """Manual restore command"""
    print_header("🔄 MANUAL RESTORE")
    print_warning("This will restore data from GitHub backup!")
    print_info("Current database will be overwritten.")
    
    confirm = input("Are you sure? (yes/no): ").strip().lower()
    if confirm == 'yes':
        result = restore_from_github()
        if result:
            print_success("Restore completed successfully!")
        else:
            print_error("Restore failed!")
    else:
        print_info("Restore cancelled.")

def cmd_status():
    """Show backup status"""
    print_header("📊 BACKUP SYSTEM STATUS")
    status = get_backup_status()
    
    print(f"\n{Colors.BOLD}System Status:{Colors.ENDC}")
    print(f"  GitHub Ready: {'✅' if status['ready'] else '❌'}")
    print(f"  Backup Running: {'✅' if status['is_running'] else '⏸️'}")
    print(f"  Queue Size: {status['queue_size']}")
    
    print(f"\n{Colors.BOLD}Database:{Colors.ENDC}")
    print(f"  Messages: {status['current_message_count']:,}")
    print(f"  Campaigns: {status['current_campaign_count']:,}")
    print(f"  Size: {status['database_size_mb']} MB")
    
    print(f"\n{Colors.BOLD}Backup Stats:{Colors.ENDC}")
    print(f"  Total Backups: {status['stats']['total_backups']}")
    print(f"  Successful: {status['stats']['successful_backups']}")
    print(f"  Failed: {status['stats']['failed_backups']}")
    print(f"  Messages Backed: {status['stats']['total_messages_backed']:,}")
    
    if status['stats']['last_backup_time']:
        print(f"\n{Colors.BOLD}Last Backup:{Colors.ENDC}")
        print(f"  Time: {status['stats']['last_backup_time'][:19]}")
        print(f"  Size: {status['stats']['last_backup_size_bytes'] / 1024:.1f} KB")
        
    print(f"\n{Colors.BOLD}GitHub:{Colors.ENDC}")
    print(f"  Backup File: {'✅ Exists' if status['backup_file_exists'] else '❌ Missing'}")
    print(f"  Metadata File: {'✅ Exists' if status['metadata_file_exists'] else '❌ Missing'}")

def cmd_health():
    """Full health check"""
    check_backup_health()

def cmd_monitor():
    """Real-time backup monitor"""
    print_header("📡 REAL-TIME BACKUP MONITOR")
    print_info("Press Ctrl+C to stop monitoring\n")
    
    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            print_header("BACKUP MONITOR - LIVE")
            
            status = get_backup_status()
            
            print(f"\n{Colors.CYAN}Time: {time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.ENDC}")
            
            # Progress bar for queue
            queue_percent = (status['queue_size'] / 100) * 100 if status['queue_size'] > 0 else 0
            bar_length = 30
            filled = int(bar_length * queue_percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\nQueue: [{bar}] {status['queue_size']}/100")
            
            print(f"\n{Colors.BOLD}Messages:{Colors.ENDC} {status['current_message_count']:,}")
            print(f"{Colors.BOLD}Backups:{Colors.ENDC} {status['stats']['total_backups']}")
            print(f"{Colors.BOLD}Success Rate:{Colors.ENDC} ", end="")
            total = status['stats']['successful_backups'] + status['stats']['failed_backups']
            if total > 0:
                rate = (status['stats']['successful_backups'] / total) * 100
                print(f"{rate:.1f}%")
            else:
                print("N/A")
            
            if status['stats']['last_backup_time']:
                print(f"{Colors.BOLD}Last Backup:{Colors.ENDC} {status['stats']['last_backup_time'][:19]}")
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print_info("\nMonitoring stopped.")

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ["backup", "b"]:
            cmd_backup()
        elif command in ["restore", "r"]:
            cmd_restore()
        elif command in ["status", "s"]:
            cmd_status()
        elif command in ["health", "h"]:
            cmd_health()
        elif command in ["monitor", "m"]:
            cmd_monitor()
        else:
            print_error(f"Unknown command: {command}")
            print_info("Available: backup, restore, status, health, monitor")
        return
    
    # Interactive mode
    while True:
        show_menu()
        choice = input(f"\n{Colors.GREEN}Enter command{Colors.ENDC}: ").strip().lower()
        
        if choice in ["backup", "b", "1"]:
            cmd_backup()
        elif choice in ["restore", "r", "2"]:
            cmd_restore()
        elif choice in ["status", "s", "3"]:
            cmd_status()
        elif choice in ["health", "h", "4"]:
            cmd_health()
        elif choice in ["monitor", "m", "5"]:
            cmd_monitor()
        elif choice in ["exit", "quit", "e", "q", "0"]:
            print_info("Goodbye! 👋")
            break
        else:
            print_error(f"Invalid command: {choice}")
        
        input(f"\n{Colors.WARNING}Press Enter to continue...{Colors.ENDC}")

if __name__ == "__main__":
    main()
