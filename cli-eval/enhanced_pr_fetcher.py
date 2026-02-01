#!/usr/bin/env python3
"""
Enhanced GitHub PR Fetcher - Clone entire repository and fetch PR information.

This script:
1. Clones the entire repository (so iFlow can make changes)
2. Checks out the PR branch
3. Fetches PR metadata and context
4. Creates comprehensive context files
5. Sets up ground truth questions for testing
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
import requests
import shutil

class EnhancedGitHubPRFetcher:
    """Enhanced fetcher that clones the full repository."""
    
    def __init__(self, repo_url, pr_number, output_dir):
        self.repo_url = repo_url
        self.pr_number = pr_number
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse repo info
        if repo_url.startswith('https://github.com/'):
            repo_path = repo_url.replace('https://github.com/', '').rstrip('/')
        else:
            repo_path = repo_url
        
        self.owner, self.repo_name = repo_path.split('/')
        self.api_base = f"https://api.github.com/repos/{self.owner}/{self.repo_name}"
        self.clone_url = f"https://github.com/{self.owner}/{self.repo_name}.git"
        self.repo_dir = self.output_dir / self.repo_name
        
        print(f"📋 Enhanced PR fetching for #{pr_number} from {self.owner}/{self.repo_name}")
    
    def run_git_command(self, cmd, cwd=None, show_progress=False):
        """Run a git command and handle errors."""
        if cwd is None:
            cwd = self.repo_dir
        
        print(f"  🔧 Running: {cmd}")
        
        if show_progress:
            # For long-running commands, show clean progress like normal terminal
            try:
                import sys
                import time
                
                # Run command and capture output line by line
                process = subprocess.Popen(
                    cmd, shell=True, cwd=cwd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    universal_newlines=True, bufsize=1
                )
                
                last_progress_line = ""
                
                last_update_time = time.time()
                
                while True:
                    line = process.stdout.readline()
                    
                    if line:
                        line = line.strip()
                        
                        # Skip empty lines
                        if not line:
                            continue
                        
                        current_time = time.time()
                        
                        # Handle git progress lines (show clean updates with throttling)
                        if any(keyword in line.lower() for keyword in [
                            'receiving objects:', 'resolving deltas:', 
                            'counting objects:', 'compressing objects:'
                        ]):
                            # Only update progress every 2 seconds to avoid spam
                            if current_time - last_update_time >= 2.0:
                                # Clear previous progress line and show new one
                                if last_progress_line:
                                    print(f"\r{' ' * 100}", end='')  # Clear line
                                print(f"\r  📦 {line}", end='', flush=True)
                                last_progress_line = line
                                last_update_time = current_time
                        elif 'cloning into' in line.lower():
                            if last_progress_line:
                                print()  # New line after progress
                                last_progress_line = ""
                            print(f"  📥 {line}")
                        elif 'done.' in line.lower():
                            if last_progress_line:
                                print()  # New line after progress
                            print(f"  ✅ {line}")
                            last_progress_line = ""
                        elif line and not any(skip in line.lower() for skip in ['warning:', 'note:', 'remote:']):
                            # Other important output (skip remote messages)
                            if last_progress_line:
                                print()  # New line after progress
                                last_progress_line = ""
                            print(f"  📝 {line}")
                    
                    # Check if process is done
                    if process.poll() is not None:
                        if last_progress_line:
                            print()  # Final newline after progress
                        break
                    
                    time.sleep(0.05)  # Faster polling
                
                return_code = process.returncode
                
                if return_code != 0:
                    raise subprocess.CalledProcessError(return_code, cmd)
                
                return "Command completed successfully"
                
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Git command failed: {e}")
                raise
        else:
            # For quick commands, capture output normally
            try:
                result = subprocess.run(
                    cmd, shell=True, cwd=cwd, check=True, 
                    capture_output=True, text=True
                )
                return result.stdout.strip()
            except subprocess.CalledProcessError as e:
                print(f"  ❌ Git command failed: {e}")
                print(f"  Error output: {e.stderr}")
                raise
    
    def clone_repository(self):
        """Clone the repository if it doesn't exist."""
        if self.repo_dir.exists():
            print(f"📁 Repository already exists at {self.repo_dir}")
            print(f"🔄 Updating existing repository...")
            # Update existing repo
            self.run_git_command("git -c http.sslVerify=false fetch origin", show_progress=True)
            return
        
        print(f"📥 Cloning repository to {self.repo_dir}...")
        print(f"🌐 Clone URL: {self.clone_url}")
        print(f"⚠️  Note: Large repositories may take several minutes to clone...")
        
        try:
            # Use optimized cloning with better performance and SSL bypass for sandbox
            clone_cmd = f"git -c http.sslVerify=false clone --progress --depth 1 --single-branch {self.clone_url} {self.repo_name}"
            self.run_git_command(
                clone_cmd, 
                cwd=self.output_dir,
                show_progress=True
            )
            
            # Skip full history fetch for now - we'll fetch only what we need for the PR
            print("✅ Shallow clone completed successfully")
            print("💡 Skipping full history fetch to keep it fast - will fetch PR branch only")
            print(f"✅ Repository cloned successfully")
        except Exception as e:
            print(f"❌ Failed to clone repository: {e}")
            print(f"💡 Tip: Check if the repository URL is correct and accessible")
            raise
    
    def fetch_pr_info(self):
        """Fetch PR information from GitHub API."""
        print("🔍 Fetching PR information...")
        print(f"📡 API URL: {self.api_base}/pulls/{self.pr_number}")
        
        pr_url = f"{self.api_base}/pulls/{self.pr_number}"
        print("⏳ Making API request...")
        response = requests.get(pr_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch PR: {response.status_code} - {response.text}")
        
        pr_data = response.json()
        
        # Enhanced PR info with branch details
        pr_info = {
            'pr_number': self.pr_number,
            'title': pr_data['title'],
            'body': pr_data['body'] or '',
            'state': pr_data['state'],
            'created_at': pr_data['created_at'],
            'updated_at': pr_data['updated_at'],
            'user': pr_data['user']['login'],
            'base_branch': pr_data['base']['ref'],
            'head_branch': pr_data['head']['ref'],
            'head_sha': pr_data['head']['sha'],
            'base_sha': pr_data['base']['sha'],
            'commits': pr_data['commits'],
            'additions': pr_data['additions'],
            'deletions': pr_data['deletions'],
            'changed_files': pr_data['changed_files'],
            'owner': self.owner,
            'repo': self.repo_name,
            'clone_url': self.clone_url
        }
        
        # Save to file
        pr_info_file = self.output_dir / f"pr_{self.pr_number}_info.json"
        with open(pr_info_file, 'w') as f:
            json.dump(pr_info, f, indent=2)
        
        print(f"✅ PR info saved to {pr_info_file}")
        return pr_info
    
    def checkout_pr_branch(self, pr_info):
        """Checkout the PR branch in the cloned repository."""
        print(f"🔀 Checking out PR branch...")
        print(f"🎯 Target branch: {pr_info['head_branch']}")
        print(f"🎯 Target SHA: {pr_info['head_sha']}")
        
        try:
            # For shallow repos, we need to fetch the specific PR branch
            print(f"📥 Fetching PR branch for #{self.pr_number}...")
            
            # First try to fetch just the PR branch
            pr_ref = f"pull/{self.pr_number}/head:pr-{self.pr_number}"
            print(f"🎯 Fetching PR reference: {pr_ref}")
            self.run_git_command(f"git -c http.sslVerify=false fetch --depth=50 origin {pr_ref}", show_progress=True)
            
            # Checkout the PR branch
            print(f"🔄 Switching to PR branch...")
            self.run_git_command(f"git checkout pr-{self.pr_number}")
            
            # Verify we're on the right commit
            print(f"🔍 Verifying checkout...")
            current_sha = self.run_git_command("git rev-parse HEAD")
            if current_sha != pr_info['head_sha']:
                print(f"⚠️  Warning: Expected SHA {pr_info['head_sha']}, got {current_sha}")
            else:
                print(f"✅ SHA verification passed")
            
            print(f"✅ Checked out PR branch: pr-{self.pr_number}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to checkout PR branch: {e}")
            # Fallback: try to checkout the head branch directly
            try:
                self.run_git_command(f"git checkout {pr_info['head_branch']}")
                print(f"✅ Checked out head branch: {pr_info['head_branch']}")
                return True
            except Exception as e2:
                print(f"❌ Fallback also failed: {e2}")
                return False
    
    def fetch_pr_diff(self):
        """Fetch PR diff."""
        print("📝 Fetching PR diff...")
        
        diff_url = f"{self.api_base}/pulls/{self.pr_number}"
        headers = {'Accept': 'application/vnd.github.v3.diff'}
        response = requests.get(diff_url, headers=headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch diff: {response.status_code}")
        
        diff_content = response.text
        
        # Save diff
        diff_file = self.output_dir / f"pr_{self.pr_number}.diff"
        with open(diff_file, 'w') as f:
            f.write(diff_content)
        
        print(f"✅ Diff saved to {diff_file}")
        return diff_content
    
    def fetch_changed_files_list(self):
        """Fetch list of changed files from GitHub API."""
        print("📁 Fetching changed files list...")
        
        files_url = f"{self.api_base}/pulls/{self.pr_number}/files"
        response = requests.get(files_url)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch files: {response.status_code}")
        
        files_data = response.json()
        changed_files = []
        
        for file_info in files_data:
            changed_files.append({
                'filename': file_info['filename'],
                'status': file_info['status'],  # added, modified, deleted
                'additions': file_info.get('additions', 0),
                'deletions': file_info.get('deletions', 0),
                'patch': file_info.get('patch', '')
            })
        
        # Save changed files list
        files_list_file = self.output_dir / f"pr_{self.pr_number}_files.json"
        with open(files_list_file, 'w') as f:
            json.dump(changed_files, f, indent=2)
        
        print(f"✅ Changed files list saved to {files_list_file}")
        return changed_files
    
    def create_comprehensive_context(self, pr_info, changed_files):
        """Create comprehensive context file for iFlow."""
        print("📝 Creating comprehensive context file...")
        
        context_content = f"""# {self.owner}/{self.repo_name} - PR #{self.pr_number} Context

## Repository Information
- **Repository:** {self.owner}/{self.repo_name}
- **Clone URL:** {self.clone_url}
- **Local Path:** {self.repo_dir}
- **Current Branch:** pr-{self.pr_number}

## PR Information
**Title:** {pr_info['title']}
**Author:** {pr_info['user']}
**Status:** {pr_info['state']}
**Base Branch:** {pr_info['base_branch']} → **Head Branch:** {pr_info['head_branch']}

**Statistics:**
- Commits: {pr_info['commits']}
- Files Changed: {pr_info['changed_files']}
- Additions: +{pr_info['additions']} lines
- Deletions: -{pr_info['deletions']} lines

## PR Description
{pr_info['body']}

## Changed Files Summary
"""
        
        for file_info in changed_files:
            status_emoji = {'added': '🆕', 'modified': '✏️', 'deleted': '🗑️'}.get(file_info['status'], '📝')
            context_content += f"- {status_emoji} **{file_info['filename']}** ({file_info['status']})\n"
            if file_info['additions'] or file_info['deletions']:
                context_content += f"  - +{file_info['additions']} -{file_info['deletions']} lines\n"
        
        context_content += f"""

## Repository Access
You have full access to the cloned repository at: `{self.repo_name}/`

### Available Capabilities:
1. **File Operations:**
   - `read_file {self.repo_name}/path/to/file.java` - Read any file in the repository
   - `list_dir {self.repo_name}/src/` - List directory contents
   - `grep -r "pattern" {self.repo_name}/` - Search through all files

2. **Git Operations:**
   - `run_terminal_cmd git log --oneline -10` - View recent commits
   - `run_terminal_cmd git show HEAD` - Show latest commit
   - `run_terminal_cmd git diff HEAD~1` - Show changes in latest commit

3. **Code Analysis:**
   - `run_terminal_cmd find {self.repo_name} -name "*.java" | head -10` - Find Java files
   - `run_terminal_cmd wc -l {self.repo_name}/path/to/file.java` - Count lines
   - `run_terminal_cmd grep -n "class.*Plugin" {self.repo_name}/src/**/*.java` - Find classes

4. **Build/Test Operations:**
   - `run_terminal_cmd cd {self.repo_name} && ./gradlew test` - Run tests (if applicable)
   - `run_terminal_cmd cd {self.repo_name} && mvn compile` - Compile (if applicable)

## Ground Truth Questions
The system will use questions from `ground_truth_questions.md` to test your understanding of this PR.

## Instructions for iFlow
1. **Use the full repository**: You have access to the complete codebase, not just changed files
2. **Read actual files**: Use read_file to examine specific code when asked
3. **Run commands**: Use terminal commands for analysis, searching, and testing
4. **Make changes if requested**: You can modify files and run tests
5. **Provide detailed answers**: Base responses on actual code examination

Please acknowledge that you understand this PR context and your full repository access. Reply with: READY FOR COMPREHENSIVE ANALYSIS
"""
        
        context_file = self.output_dir / f"pr_{self.pr_number}_context.md"
        with open(context_file, 'w') as f:
            f.write(context_content)
        
        print(f"✅ Comprehensive context file created: {context_file}")
        return context_file
    
    def fix_file_permissions(self):
        """Fix file permissions by removing macOS extended attributes."""
        print("🔧 Fixing file permissions...")
        try:
            # Remove extended attributes that can block iFlow file access
            subprocess.run(["xattr", "-cr", str(self.output_dir)], 
                         capture_output=True, check=False)
            print("✅ Fixed file permissions (removed extended attributes)")
        except Exception as e:
            print(f"⚠️  Could not fix file permissions: {e}")
            pass  # Not critical if this fails
    
    def copy_ground_truth_questions(self):
        """Copy ground truth questions to the PR directory."""
        print("📋 Setting up ground truth questions...")
        
        source_file = Path(__file__).parent / "ground_truth_questions.md"
        if source_file.exists():
            dest_file = self.output_dir / "ground_truth_questions.md"
            shutil.copy2(source_file, dest_file)
            print(f"✅ Ground truth questions copied to {dest_file}")
        else:
            print("⚠️  Ground truth questions file not found - creating placeholder")
            placeholder_file = self.output_dir / "ground_truth_questions.md"
            with open(placeholder_file, 'w') as f:
                f.write("# Ground Truth Questions\n\nAdd your ground truth questions here.\n")


def main():
    """Main function to fetch PR data and clone repository."""
    parser = argparse.ArgumentParser(description="Enhanced GitHub PR fetcher with full repository cloning")
    parser.add_argument("--repo", required=True, 
                       help="GitHub repository (owner/repo or full URL)")
    parser.add_argument("--pr", type=int, required=True,
                       help="Pull request number")
    parser.add_argument("--output-dir", default="pr_workspace",
                       help="Output directory for PR workspace")
    
    args = parser.parse_args()
    
    try:
        # Create enhanced fetcher
        fetcher = EnhancedGitHubPRFetcher(args.repo, args.pr, args.output_dir)
        
        # Step 1: Clone repository
        fetcher.clone_repository()
        
        # Step 2: Fetch PR information
        pr_info = fetcher.fetch_pr_info()
        
        # Step 3: Checkout PR branch
        checkout_success = fetcher.checkout_pr_branch(pr_info)
        if not checkout_success:
            print("⚠️  Warning: Could not checkout PR branch, using default branch")
        
        # Step 4: Fetch additional PR data
        fetcher.fetch_pr_diff()
        changed_files = fetcher.fetch_changed_files_list()
        
        # Step 5: Create comprehensive context
        context_file = fetcher.create_comprehensive_context(pr_info, changed_files)
        
        # Step 6: Fix file permissions (CRITICAL FIX)
        fetcher.fix_file_permissions()
        
        # Step 7: Set up ground truth questions
        fetcher.copy_ground_truth_questions()
        
        print(f"\n🎉 Enhanced PR workspace ready!")
        print(f"📁 Workspace directory: {fetcher.output_dir}")
        print(f"📂 Repository cloned to: {fetcher.repo_dir}")
        print(f"📝 Context file: {context_file}")
        print(f"📋 Ground truth questions: {fetcher.output_dir}/ground_truth_questions.md")
        print(f"\n🚀 Next step: Run dynamic_prompt_generator.py")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error setting up PR workspace: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
