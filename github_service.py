# ====================================================================
# 📁 FILE: github_service.py
# 🎯 ROLE: GitHub API Operations - Create, Read, Update, Delete Files
# 🔗 USED BY: ai_service.py (Brain)
# 🔑 TOKEN: Render Environment Variables se leta hai
# 📋 TOTAL FUNCTIONS: 7
# ====================================================================

import os
import requests
import base64
from datetime import datetime

# config.py se settings import karo
from config import GITHUB_OWNER, GITHUB_REPO, GITHUB_BRANCH


class GitHubService:
    """
    GitHub Service Class
    GitHub Repo ke saath saare operations handle karta hai
    """
    
    def __init__(self):
        """Initialize GitHub Service"""
        # Token Render Environment Variables se lo
        self.token = os.environ.get("GITHUB_TOKEN")
        self.owner = GITHUB_OWNER
        self.repo = GITHUB_REPO
        self.branch = GITHUB_BRANCH
        
        # Check if token exists
        if not self.token:
            print("⚠️ WARNING: GITHUB_TOKEN not found in Environment Variables!")
            self.ready = False
        else:
            print("✅ GitHub Service Ready")
            self.ready = True
        
        # GitHub API Headers
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # GitHub API Base URL
        self.api_url = "https://api.github.com"
    
    # ====================================================================
    # 1️⃣ TEST CONNECTION
    # ====================================================================
    
    def test_connection(self):
        """Check if GitHub connection is working"""
        
        if not self.ready:
            return {
                "success": False,
                "error": "GitHub Token not configured in Render Environment"
            }
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
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
                return {
                    "success": False,
                    "error": "❌ Invalid Token! Please check GITHUB_TOKEN"
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": f"❌ Repository '{self.owner}/{self.repo}' not found"
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Connection error: {str(e)}"
            }
    
    # ====================================================================
    # 2️⃣ CREATE FILE
    # ====================================================================
    
    def create_file(self, file_name, content, commit_message=None):
        """
        Create a new file in GitHub Repo
        
        Parameters:
        - file_name: Name of the file (e.g., 'payment.py')
        - content: File content as string
        - commit_message: Optional commit message
        """
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"🤖 Auto-created {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        # Check if file already exists
        check = requests.get(url, headers=self.headers)
        if check.status_code == 200:
            return {
                "success": False,
                "error": f"⚠️ File '{file_name}' already exists! Use update_file() to modify."
            }
        
        # Encode content to base64
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        # Prepare data
        data = {
            "message": commit_message,
            "content": encoded_content,
            "branch": self.branch
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "message": f"✅ File created: {file_name}",
                    "file_url": result["content"]["html_url"],
                    "commit_url": result["commit"]["html_url"],
                    "file_name": file_name
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ Failed: {response.json()}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    # ====================================================================
    # 3️⃣ READ FILE
    # ====================================================================
    
    def read_file(self, file_name):
        """
        Read file content from GitHub Repo
        
        Parameters:
        - file_name: Name of the file to read
        """
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                return {
                    "success": True,
                    "content": content,
                    "sha": data["sha"],
                    "file_url": data["html_url"],
                    "file_name": file_name,
                    "size_bytes": data["size"]
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": f"❌ File '{file_name}' not found"
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    # ====================================================================
    # 4️⃣ UPDATE FILE
    # ====================================================================
    
    def update_file(self, file_name, new_content, commit_message=None):
        """
        Update an existing file in GitHub Repo
        
        Parameters:
        - file_name: Name of the file to update
        - new_content: New content for the file
        - commit_message: Optional commit message
        """
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        # First read the file to get SHA
        read_result = self.read_file(file_name)
        if not read_result["success"]:
            return read_result
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"✏️ Auto-updated {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        # Encode new content
        encoded_content = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
        
        # Prepare data
        data = {
            "message": commit_message,
            "content": encoded_content,
            "sha": read_result["sha"],
            "branch": self.branch
        }
        
        try:
            response = requests.put(url, headers=self.headers, json=data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    "success": True,
                    "message": f"✅ File updated: {file_name}",
                    "file_url": result["content"]["html_url"],
                    "commit_url": result["commit"]["html_url"],
                    "file_name": file_name
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ Failed: {response.json()}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    # ====================================================================
    # 5️⃣ DELETE FILE
    # ====================================================================
    
    def delete_file(self, file_name, commit_message=None):
        """
        Delete a file from GitHub Repo
        
        Parameters:
        - file_name: Name of the file to delete
        - commit_message: Optional commit message
        """
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        # First read the file to get SHA
        read_result = self.read_file(file_name)
        if not read_result["success"]:
            return read_result
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            commit_message = f"🗑️ Auto-deleted {file_name} at {timestamp}"
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{file_name}"
        
        # Prepare data
        data = {
            "message": commit_message,
            "sha": read_result["sha"],
            "branch": self.branch
        }
        
        try:
            response = requests.delete(url, headers=self.headers, json=data)
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"✅ File deleted: {file_name}",
                    "file_name": file_name
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ Failed: {response.json()}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    # ====================================================================
    # 6️⃣ LIST FILES
    # ====================================================================
    
    def list_files(self, folder_path=""):
        """
        List all files in a folder
        
        Parameters:
        - folder_path: Folder path (empty for root)
        """
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}/contents/{folder_path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                files = []
                for item in response.json():
                    files.append({
                        "name": item["name"],
                        "type": "📁" if item["type"] == "dir" else "📄",
                        "url": item["html_url"],
                        "size": item.get("size", 0)
                    })
                return {
                    "success": True,
                    "files": files,
                    "count": len(files),
                    "folder": folder_path or "root"
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }
    
    # ====================================================================
    # 7️⃣ CREATE TEST FILE
    # ====================================================================
    
    def create_test_file(self):
        """Create a test file to verify everything works"""
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        content = f"""# GitHub Connection Test
========================
Created: {timestamp}
Owner: {self.owner}
Repo: {self.repo}
Branch: {self.branch}

✅ Connection Successful!

This file confirms that:
1. GitHub Token is valid
2. Repository access is working
3. File creation is successful

Your GitHub Automation is ready!
"""
        
        return self.create_file(
            "test_connection.txt",
            content,
            f"🤖 Test connection at {timestamp}"
        )
    
    # ====================================================================
    # 8️⃣ GET REPO INFO
    # ====================================================================
    
    def get_repo_info(self):
        """Get repository information"""
        
        if not self.ready:
            return {"success": False, "error": "GitHub Token not configured"}
        
        url = f"{self.api_url}/repos/{self.owner}/{self.repo}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
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
                return {
                    "success": False,
                    "error": f"❌ HTTP Error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"❌ Error: {str(e)}"
            }


# ====================================================================
# DIRECT TEST (जब सीधे run करो)
# ====================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 GITHUB SERVICE - DIRECT TEST")
    print("="*60)
    
    # Initialize service
    github = GitHubService()
    
    if not github.ready:
        print("\n❌ Cannot proceed!")
        print("   Please add GITHUB_TOKEN to Render Environment Variables")
        print("\n   Steps:")
        print("   1. Go to Render Dashboard")
        print("   2. Select umar-k20u service")
        print("   3. Environment tab")
        print("   4. Add GITHUB_TOKEN variable")
    else:
        # Test 1: Connection
        print("\n1️⃣ Testing connection...")
        conn = github.test_connection()
        if conn["success"]:
            print(f"   {conn['message']}")
            print(f"   🔗 {conn['repo_url']}")
        else:
            print(f"   {conn['error']}")
        
        # Test 2: Repo Info
        print("\n2️⃣ Getting repo info...")
        info = github.get_repo_info()
        if info["success"]:
            print(f"   📁 {info['name']}")
            print(f"   ⭐ {info['stars']} stars")
            print(f"   📝 {info['language']}")
        
        # Test 3: Create test file
        print("\n3️⃣ Creating test file...")
        result = github.create_test_file()
        if result["success"]:
            print(f"   {result['message']}")
            print(f"   📁 {result['file_url']}")
        else:
            print(f"   {result['error']}")
        
        # Test 4: List files
        print("\n4️⃣ Listing files...")
        files = github.list_files()
        if files["success"]:
            print(f"   📂 Found {files['count']} files:")
            for f in files["files"][:5]:
                print(f"      {f['type']} {f['name']}")
    
    print("\n" + "="*60)
    print("✅ Test Complete!")
    print("="*60)
