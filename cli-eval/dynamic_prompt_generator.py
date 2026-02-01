#!/usr/bin/env python3
"""
Dynamic Prompt Generator for iFlow CLI

Automatically generates the initial context prompt based on PR workspace data.
The prompt is dynamically adapted for any PR being evaluated.
"""

import json
from pathlib import Path

class DynamicPromptGenerator:
    """Generates dynamic initial prompts based on PR workspace data."""
    
    def __init__(self, pr_workspace_dir):
        self.pr_workspace_dir = Path(pr_workspace_dir)
        self.pr_info = None
        self.repo_name = None
        self.pr_number = None
        
    def load_pr_metadata(self):
        """Load PR metadata from workspace."""
        # Find PR info file
        pr_info_files = list(self.pr_workspace_dir.glob("pr_*_info.json"))
        if not pr_info_files:
            raise FileNotFoundError("No PR info file found in workspace")
        
        with open(pr_info_files[0]) as f:
            self.pr_info = json.load(f)
        
        self.repo_name = self.pr_info.get('repo', 'unknown')
        self.pr_number = self.pr_info.get('pr_number', 'unknown')
        
        return self.pr_info
    
    def find_workspace_files(self):
        """Find all relevant files in the workspace."""
        files = {
            'pr_desc': None,
            'pr_diff': None,
            'pr_context': None,
            'pr_files': None,
            'repo_dir': None
        }
        
        # Find PR description/context file
        context_files = list(self.pr_workspace_dir.glob("pr_*_context.md"))
        if context_files:
            files['pr_context'] = context_files[0].name
        
        # Find PR diff file
        diff_files = list(self.pr_workspace_dir.glob("pr_*.diff"))
        if diff_files:
            files['pr_diff'] = diff_files[0].name
        
        # Find PR files list
        files_list = list(self.pr_workspace_dir.glob("pr_*_files.json"))
        if files_list:
            files['pr_files'] = files_list[0].name
        
        # Find repository directory
        repo_dir = self.pr_workspace_dir / self.repo_name
        if repo_dir.exists():
            files['repo_dir'] = self.repo_name
        
        return files
    
    def get_changed_files_list(self):
        """Get list of changed files from PR files JSON."""
        files_list = list(self.pr_workspace_dir.glob("pr_*_files.json"))
        if not files_list:
            return []
        
        try:
            with open(files_list[0]) as f:
                files_data = json.load(f)
            
            changed_files = []
            for file_info in files_data:
                if isinstance(file_info, dict) and 'filename' in file_info:
                    changed_files.append(file_info['filename'])
                elif isinstance(file_info, str):
                    changed_files.append(file_info)
            
            return changed_files[:10]  # Limit to first 10 files for prompt brevity
        except:
            return []
    
    def generate_dynamic_prompt(self):
        """Generate the dynamic initial context prompt."""
        # Load metadata
        self.load_pr_metadata()
        files = self.find_workspace_files()
        changed_files = self.get_changed_files_list()
        
        # Get repository info
        owner = self.pr_info.get('owner', 'unknown')
        repo = self.pr_info.get('repo', 'unknown')
        pr_title = self.pr_info.get('title', 'Unknown PR')
        
        # Build the dynamic prompt with local file paths (files will be copied to repo directory)
        prompt = f"""You are helping me evaluate GitHub pull request {owner}/{repo} #{self.pr_number}.

**PR Title:** {pr_title}

**Your Task:**
1. First, read the file `{files['pr_context']}` to understand the PR context
2. Then, read the file `{files['pr_diff']}` to see what changed  
3. Based on the diff, examine the actual changed files in the current directory

**Key files that were changed in this PR:**"""

        # Add changed files list with correct paths
        if changed_files:
            for i, file_path in enumerate(changed_files, 1):
                prompt += f"\n{i}. {file_path}"
        else:
            prompt += f"\n(Use the diff file to identify changed files)"

        prompt += f"""

**File locations:**
- PR context: `{files['pr_context']}` (in current directory)
- PR diff: `{files['pr_diff']}` (in current directory)
- Repository: `{files['repo_dir']}/` (complete repository codebase)
- Changed files: Look in `{files['repo_dir']}/` using paths from diff

**Instructions:**
- Explore the complete repository when needed for thorough answers
- Look at related files, tests, documentation, and examples
- Provide specific details: file paths, function names, code snippets
- Connect changes to broader codebase context
- Use ONLY the local files in this repository
- Only say "I don't know" after thorough exploration

**When ready to answer questions, reply with exactly:**
READY_FOR_QUESTIONS"""

        return prompt
    
    def save_generated_prompt(self, output_file):
        """Generate and save the dynamic prompt to a file."""
        prompt = self.generate_dynamic_prompt()
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(prompt)
        
        print(f"✅ Generated dynamic prompt saved to: {output_file}")
        return prompt
    
    def get_prompt_summary(self):
        """Get a summary of the generated prompt."""
        self.load_pr_metadata()
        files = self.find_workspace_files()
        changed_files = self.get_changed_files_list()
        
        return {
            'repo': f"{self.pr_info.get('owner', 'unknown')}/{self.pr_info.get('repo', 'unknown')}",
            'pr_number': self.pr_number,
            'pr_title': self.pr_info.get('title', 'Unknown'),
            'repo_dir': files['repo_dir'],
            'context_file': files['pr_context'],
            'diff_file': files['pr_diff'],
            'changed_files_count': len(changed_files),
            'changed_files': changed_files
        }


def main():
    """Test the dynamic prompt generator."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate dynamic initial prompt for iFlow CLI")
    parser.add_argument("--workspace", required=True,
                       help="PR workspace directory")
    parser.add_argument("--output", 
                       help="Output file for generated prompt")
    parser.add_argument("--summary", action="store_true",
                       help="Show prompt summary only")
    
    args = parser.parse_args()
    
    try:
        generator = DynamicPromptGenerator(args.workspace)
        
        if args.summary:
            summary = generator.get_prompt_summary()
            print("📋 Dynamic Prompt Summary:")
            print(f"  Repository: {summary['repo']}")
            print(f"  PR: #{summary['pr_number']} - {summary['pr_title']}")
            print(f"  Repo Directory: @{summary['repo_dir']}")
            print(f"  Context File: @{summary['context_file']}")
            print(f"  Diff File: @{summary['diff_file']}")
            print(f"  Changed Files: {summary['changed_files_count']}")
            for i, file_path in enumerate(summary['changed_files'][:5], 1):
                print(f"    {i}. {file_path}")
        else:
            if args.output:
                prompt = generator.save_generated_prompt(args.output)
            else:
                prompt = generator.generate_dynamic_prompt()
                print("Generated Dynamic Prompt:")
                print("=" * 60)
                print(prompt)
                print("\n🚀 Next step: Run iflow_pr_benchmark.py")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
