# ====================================================================
# 📁 FILE: github_service.py
# 🎯 ROLE: GitHub API Operations - ENHANCED with confirmation & batch ops
# 🔗 USED BY: ai_service.py (Brain)
# 🔑 TOKEN: Render Environment Variables se leta hai
# 📋 TOTAL FUNCTIONS: 12 (7 old + 5 new)
# 🆕 NEW: Delete confirmation, Batch operations, Rate limit handling
# ====================================================================

import os
import requests
import base64
import time
from datetime import datetime

from config import GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH


class GitHubService:
    """
    GitHub Service Class - ENHANCED VERSION
    GitHub Repo ke saath saare operations handle karta hai
    """
    
    def __init__(self):
        """Initialize GitHub Service"""
        self.token = os.environ.get("GITHUB_TOKEN")
        self.owner = GITHUB_OWNER
        self.repo = GITHUB_REPO
        self.branch = GITHUB_BRANCH
        self.pending_delete = None  # For confirmation
        
        if not self.token:
            print("⚠️ WARNING: GITHUB_TOKEN not found!")
            self.ready = False
        else:
            print("✅ GitHub Service Ready")
            self.ready = True
        
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.api_url = "https://api.github.com"
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = 0
    
    # ================= EXISTING METHODS (SAME) =================
    
    def test_connection(self):
        """Check if GitHub connection is working"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            self._update_rate_limit(response.headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "message": f"✅ Connected to {data['full_name']}",
                    "repo_url": data['html_url'],
                    "private": data['private'],
                    "stars": data['stargazers_count']
                }
            elif response.status_code == 401:
                return {"success": False, "error": "❌ Invalid Token!"}
            elif response.status_code == 404:
                return {"success": False, "error": f"❌ Repository not found"}
            else:
                return {"success": False, "error": f"❌ HTTP Error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Connection error: {str(e)}"}
    
    def create_file(self, file_name, content, commit_message=None):
        """Create a new file in GitHub Repo"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        if self._check_rate_limit():
            return {"success": False, "error": "Rate limit exceeded. Please try later."}
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"🤖 Auto-created {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        check = requests.get(url, headers=self.headers)
        if check.status_code == 200:
            return {"success": False, "error": f"⚠️ File '{file_name}' already exists!"}
        
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        data = {"message": commit_message, "content": encoded_content, "branch": self.branch}
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            self._update_rate_limit(response.headers)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "message": f"✅ File created: {file_name}",
                    "file_url": result["content"]["html_url"],
                    "file_name": file_name
                }
            else:
                return {"success": False, "error": f"❌ Failed: {response.json()}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    def read_file(self, file_name, max_lines=None):
        """Read file content - with optional line limit"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        try:
            response = requests.get(url, headers=self.headers)
            self._update_rate_limit(response.headers)
            
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                
                # Limit lines if requested
                if max_lines:
                    lines = content.split('\n')
                    if len(lines) > max_lines:
                        content = '\n'.join(lines[:max_lines]) + f"\n\n... (file has {len(lines)} lines, showing first {max_lines})"
                
                return {
                    "success": True,
                    "content": content,
                    "sha": data["sha"],
                    "file_url": data["html_url"],
                    "file_name": file_name,
                    "size_bytes": data["size"]
                }
            elif response.status_code == 404:
                return {"success": False, "error": f"❌ File '{file_name}' not found"}
            else:
                return {"success": False, "error": f"❌ HTTP Error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    def update_file(self, file_name, new_content, commit_message=None):
        """Update an existing file"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        read_result = self.read_file(file_name)
        if not read_result["success"]:
            return read_result
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"✏️ Auto-updated {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
        
        data = {
            "message": commit_message,
            "content": encoded_content,
            "sha": read_result["sha"],
            "branch": self.branch
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            self._update_rate_limit(response.headers)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "message": f"✅ File updated: {file_name}",
                    "file_url": result["content"]["html_url"],
                    "file_name": file_name
                }
            else:
                return {"success": False, "error": f"❌ Failed: {response.json()}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    # ================= 🆕 ENHANCED DELETE WITH CONFIRMATION =================
    def delete_file(self, file_name, confirm=False, commit_message=None):
        """
        Delete a file - REQUIRES CONFIRMATION
        Set confirm=True to actually delete
        """
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        # Check if we need confirmation
        if not confirm:
            return {
                "success": False, 
                "need_confirm": True,
                "message": f"⚠️ Kya aap '{file_name}' delete karna chahte ho?",
                "file_name": file_name
            }
        
        read_result = self.read_file(file_name)
        if not read_result["success"]:
            return read_result
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"🗑️ Deleted {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        data = {"message": commit_message, "sha": read_result["sha"], "branch": self.branch}
        
        try:
            response = requests.delete(url, headers=self.headers, json=data)
            self._update_rate_limit(response.headers)
            
            if response.status_code == 200:
                return {"success": True, "message": f"✅ File deleted: {file_name}", "file_name": file_name}
            else:
                return {"success": False, "error": f"❌ Failed: {response.json()}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    def list_files(self, folder_path=""):
        """List all files in a folder"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{folder_path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            self._update_rate_limit(response.headers)
            
            if response.status_code == 200:
                files = []
                for item in response.json():
                    files.append({
                        "name": item["name"],
                        "type": "📁" if item["type"] == "dir" else "📄",
                        "url": item["html_url"],
                        "size": item.get("size", 0)
                    })
                return {"success": True, "files": files, "count": len(files), "folder": folder_path or "root"}
            else:
                return {"success": False, "error": f"❌ HTTP Error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    def create_test_file(self):
        """Create a test file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""# GitHub Connection Test
Created: {timestamp}
Owner: {self.owner}
Repo: {self.repo}
✅ Connection Successful!
"""
        return self.create_file("test_connection.txt", content, f"🤖 Test at {timestamp}")
    
    def get_repo_info(self):
        """Get repository information"""
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            self._update_rate_limit(response.headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "name": data["full_name"],
                    "url": data["html_url"],
                    "description": data.get("description", "No description"),
                    "stars": data["stargazers_count"],
                    "forks": data["forks_count"],
                    "language": data.get("language", "Unknown"),
                    "private": data["private"],
                    "created": data["created_at"],
                    "updated": data["updated_at"]
                }
            else:
                return {"success": False, "error": f"❌ HTTP Error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"❌ Error: {str(e)}"}
    
    # ================= 🆕 NEW METHOD 1: BATCH CREATE FILES =================
    def batch_create_files(self, files_list):
        """
        Create multiple files at once
        files_list = [{"name": "file1.py", "content": "code"}, ...]
        """
        results = []
        for file_info in files_list:
            result = self.create_file(file_info["name"], file_info["content"])
            results.append(result)
            time.sleep(0.5)  # Avoid rate limit
        return results
    
    # ================= 🆕 NEW METHOD 2: RATE LIMIT HANDLING =================
    def _update_rate_limit(self, headers):
        """Update rate limit info from response headers"""
        if 'X-RateLimit-Remaining' in headers:
            self.rate_limit_remaining = int(headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in headers:
            self.rate_limit_reset = int(headers['X-RateLimit-Reset'])
    
    def _check_rate_limit(self):
        """Check if rate limit is exceeded"""
        if self.rate_limit_remaining <= 10:
            wait_time = self.rate_limit_reset - time.time()
            if wait_time > 0:
                return True
        return False
    
    def get_rate_limit_status(self):
        """Get current rate limit status"""
        return {
            "remaining": self.rate_limit_remaining,
            "reset_time": datetime.fromtimestamp(self.rate_limit_reset).isoformat() if self.rate_limit_reset else None,
            "ready": self.rate_limit_remaining > 10
        }
    
    # ================= 🆕 NEW METHOD 3: GET FILE METRICS =================
    def get_file_metrics(self, file_name):
        """Get metrics about a file without reading full content"""
        result = self.read_file(file_name, max_lines=10)
        if not result["success"]:
            return result
        
        content = result.get("content", "")
        return {
            "success": True,
            "file_name": file_name,
            "size_bytes": result.get("size_bytes", 0),
            "line_count": len(content.split('\n')) if content else 0,
            "function_count": content.count('def ') + content.count('async def '),
            "class_count": content.count('class '),
            "import_count": content.count('import ') + content.count('from '),
            "url": result.get("file_url")
        }
    
    # ================= 🆕 NEW METHOD 4: BATCH DELETE =================
    def batch_delete_files(self, file_names, confirm=False):
        """Delete multiple files at once"""
        if not confirm:
            return {
                "success": False,
                "need_confirm": True,
                "message": f"⚠️ Kya aap ye {len(file_names)} files delete karna chahte ho?",
                "files": file_names
            }
        
        results = []
        for fname in file_names:
            result = self.delete_file(fname, confirm=True)
            results.append(result)
            time.sleep(0.5)
        return {"success": True, "results": results}
    
    # ================= 🆕 NEW METHOD 5: FILE EXISTS CHECK =================
    def file_exists(self, file_name):
        """Check if file exists in repository"""
        result = self.read_file(file_name)
        return result["success"]
