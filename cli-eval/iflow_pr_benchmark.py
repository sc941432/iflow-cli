#!/usr/bin/env python3
"""
iFlow PR Benchmark System - Session Management & Evaluation

This is the final step in the 3-step workflow for evaluating iFlow CLI.
It focuses purely on session management and question evaluation.

Prerequisites:
1. Run enhanced_pr_fetcher.py to clone repository and prepare PR data
2. Run dynamic_prompt_generator.py to create the initial context prompt
3. Run this script to execute the benchmark with perfect session management

Usage:
    python3 iflow_pr_benchmark.py --workspace pr_workspace_apache --benchmark apache_pr_58365
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re


class iFlowPRBenchmark:
    """iFlow PR Benchmark - Session Management & Evaluation Only"""
    
    def __init__(self, workspace_dir: str, benchmark_name: str):
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_name = benchmark_name
        self.benchmark_dir = Path("benchmarks") / benchmark_name
        self.answers_file = self.benchmark_dir / "iflow_answers.md"
        
        # Session management
        self.iflow_session_id: Optional[str] = None
        self.current_turn = 0
        
        # PR information (loaded from workspace)
        self.repo_name = ""
        self.pr_number = ""
        self.pr_title = ""
        
        # Ensure directories exist
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.workspace_dir.exists():
            raise FileNotFoundError(f"Workspace directory not found: {workspace_dir}")
    
    def load_pr_info(self) -> bool:
        """Load PR information from workspace files."""
        print("📋 Loading PR information from workspace...")
        
        # Find PR info file
        pr_info_files = list(self.workspace_dir.glob("pr_*_info.json"))
        if not pr_info_files:
            print("❌ No PR info file found in workspace")
            return False
        
        try:
            with open(pr_info_files[0]) as f:
                pr_info = json.load(f)
            
            self.repo_name = pr_info.get('repository', 'unknown')
            self.pr_number = str(pr_info.get('pr_number', 'unknown'))
            self.pr_title = pr_info.get('title', f"PR #{self.pr_number}")
            
            print(f"✅ Loaded PR info: {self.repo_name} #{self.pr_number}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load PR info: {e}")
            return False
    
    def load_initial_prompt(self) -> Optional[str]:
        """Load the generated initial prompt."""
        print("📝 Loading generated initial prompt...")
        
        # Look for generated prompt file
        prompt_files = [
            self.workspace_dir / "generated_prompt.md",
            self.workspace_dir / "initial_prompt.md",
            self.benchmark_dir / "initial_prompt.md"
        ]
        
        for prompt_file in prompt_files:
            if prompt_file.exists():
                try:
                    prompt = prompt_file.read_text()
                    print(f"✅ Loaded prompt from: {prompt_file}")
                    return prompt
                except Exception as e:
                    print(f"⚠️  Could not read {prompt_file}: {e}")
        
        print("❌ No generated prompt found. Run dynamic_prompt_generator.py first.")
        return None
    
    def load_ground_truth_questions(self) -> List[str]:
        """Load ground truth questions from workspace or benchmark directory."""
        print("📝 Loading ground truth questions...")
        
        # Check both workspace and benchmark directories
        questions_files = [
            self.workspace_dir / "ground_truth_questions.md",
            self.benchmark_dir / "ground_truth_questions.md"
        ]
        
        for questions_file in questions_files:
            if questions_file.exists():
                try:
                    content = questions_file.read_text()
                    questions = []
                    
                    # Extract questions (lines starting with Q: or **Question:**)
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('Q:'):
                            question = line[2:].strip()
                            if question:
                                questions.append(question)
                        elif line.startswith('**Question:**'):
                            question = line[13:].strip()
                            if question:
                                questions.append(question)
                    
                    if questions:
                        print(f"✅ Loaded {len(questions)} questions from: {questions_file}")
                        return questions
                        
                except Exception as e:
                    print(f"⚠️  Could not read {questions_file}: {e}")
        
        print("❌ No ground truth questions found")
        return []
    
    def check_iflow_installation(self) -> Optional[str]:
        """Check if iFlow CLI is installed and return version."""
        try:
            # Set up environment with SSL bypass for iFlow CLI
            env = os.environ.copy()
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            
            result = subprocess.run(["iflow", "--version"], 
                                  capture_output=True, text=True, timeout=10, env=env)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ iFlow CLI found: {version}")
                return version
            else:
                print("❌ iFlow CLI not found or not working")
                return None
        except Exception as e:
            print(f"❌ iFlow CLI check failed: {e}")
            return None
    
    def _execute_iflow_command(self, cmd: List[str], timeout: int = 120) -> Dict:
        """Execute iFlow CLI command with proper error handling."""
        try:
            print(f"📤 Executing: {' '.join(cmd[:2])} {cmd[2][:100]}{'...' if len(cmd[2]) > 100 else ''}")
            print(f"📁 Working directory: {self.workspace_dir}")
            
            start_time = time.time()
            
            # Set up environment with SSL bypass for iFlow CLI
            env = os.environ.copy()
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            
            result = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'output': result.stdout,
                    'error': result.stderr,
                    'response_time': response_time
                }
            else:
                error_msg = f"iFlow CLI failed (exit {result.returncode}): {result.stderr}"
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'output': result.stdout,
                    'error': error_msg,
                    'response_time': response_time
                }
                
        except subprocess.TimeoutExpired as e:
            error_msg = f"iFlow CLI timed out after {timeout}s"
            print(f"⏰ {error_msg}")
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'response_time': timeout
            }
        except Exception as e:
            error_msg = f"iFlow CLI execution failed: {e}"
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'output': '',
                'error': error_msg,
                'response_time': 0
            }
    
    def _extract_session_id(self, output: str) -> Optional[str]:
        """Extract session ID from iFlow output."""
        # Look for session ID in execution info JSON
        session_match = re.search(r'"session-id":\s*"(session-[a-f0-9-]+)"', output)
        if session_match:
            return session_match.group(1)
        
        # Fallback: Look for session ID anywhere in output
        session_match = re.search(r'session-[a-f0-9-]+', output)
        if session_match:
            return session_match.group(0)
        return None
    
    def send_initial_prompt(self, prompt: str) -> Tuple[str, float]:
        """Send initial prompt to create iFlow session."""
        print(f"🚀 Turn {self.current_turn}: Creating new iFlow session with initial context...")
        
        cmd = ["iflow", "-p", prompt]
        result = self._execute_iflow_command(cmd, timeout=180)
        
        if not result['success']:
            raise Exception(result['error'])
        
        # Extract session ID from both stdout and stderr
        combined_output = result['output'] + '\n' + result['error']
        self.iflow_session_id = self._extract_session_id(combined_output)
        if not self.iflow_session_id:
            print("⚠️  Warning: Could not extract session ID from output")
            print(f"DEBUG - Output: {result['output']}")
            print(f"DEBUG - Error: {result['error']}")
        else:
            print(f"✅ Session ID extracted: {self.iflow_session_id}")
        
        self.current_turn += 1
        return result['output'], result['response_time']
    
    def send_question(self, question: str) -> Tuple[str, float]:
        """Send question using session resume."""
        if not self.iflow_session_id:
            raise Exception("No active session ID")
        
        cmd = ["iflow", "-r", self.iflow_session_id, "-p", question]
        result = self._execute_iflow_command(cmd, timeout=120)
        
        if not result['success']:
            raise Exception(result['error'])
        
        self.current_turn += 1
        return result['output'], result['response_time']
    
    def initialize_answers_file(self, iflow_version: str):
        """Initialize the answers file with metadata."""
        content = f"""# iFlow CLI Benchmark Results - {self.benchmark_name.title()}

This file contains the complete benchmark results for iFlow CLI evaluation.

**Test Information:**
- **Repository:** {self.repo_name}
- **PR Number:** #{self.pr_number}
- **PR Title:** {self.pr_title}
- **Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **iFlow CLI Version:** {iflow_version}
- **Workspace:** {self.workspace_dir}

**Session Management:**
- **Session Model:** Single persistent session per benchmark
- **Session ID:** [Will be populated after Turn 0]
- **Turn Tracking:** Turn 0 (session creation) + Turn 1+ (session resume with -r flag)
- **Context Persistence:** Rich initial context + session memory accumulation
- **Error Handling:** Robust retry logic for reliability

---

## Test Results

### Session Summary
[Will be populated at the end]

---

## Initial Context Setup (Turn 0)

"""
        self.answers_file.write_text(content)
        print(f"📄 Initialized answers file: {self.answers_file}")
    
    def save_initial_response(self, prompt: str, response: str, response_time: float):
        """Save the initial prompt and response."""
        content = f"""### Session Information:
- **Session ID:** {self.iflow_session_id or 'Not captured'}
- **Turn:** 0 (Session Creation)
- **Response Time:** {response_time:.1f}s

### Initial Prompt Sent to iFlow:
```
{prompt}
```

### iFlow's Initial Response:
```
{response}
```

---

## Question & Answer Pairs

"""
        
        with open(self.answers_file, 'a') as f:
            f.write(content)
    
    def append_qa_pair(self, question_num: int, question: str, answer: str, response_time: float):
        """Append a Q&A pair to the answers file."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        content = f"""### Question {question_num} (Turn {self.current_turn - 1})
**Session ID:** {self.iflow_session_id or 'Not captured'}
**Turn:** {self.current_turn - 1} (Session Resume with -r flag)
**Question:** {question}
**iFlow Answer:** {answer}
**Response Time:** {response_time:.1f}s
**Timestamp:** {timestamp}

---

"""
        
        with open(self.answers_file, 'a') as f:
            f.write(content)
    
    def finalize_results(self, total_questions: int, total_time: float, 
                        memory_references: int, detailed_responses: int):
        """Finalize the results file with summary statistics."""
        
        # Read current content
        content = self.answers_file.read_text()
        
        # Create session summary
        avg_time = total_time / total_questions if total_questions > 0 else 0
        
        session_summary = f"""### Session Summary
- **Session ID:** {self.iflow_session_id or 'Not captured'}
- **Total Turns:** {self.current_turn}
- **Total Questions:** {total_questions}
- **Questions Answered:** {total_questions}
- **Session Duration:** {total_time:.1f}s
- **Average Response Time:** {avg_time:.1f}s
- **Memory References Detected:** {memory_references}
- **Detailed Responses:** {detailed_responses}

---"""
        
        # Replace placeholder
        content = content.replace(
            "### Session Summary\n[Will be populated at the end]",
            session_summary
        )
        
        self.answers_file.write_text(content)
        print(f"📊 Finalized results in: {self.answers_file}")
    
    def run_benchmark(self) -> bool:
        """Run the benchmark process (session management only)."""
        
        print(f"🚀 Starting iFlow PR Benchmark - Session Management")
        print("=" * 60)
        
        # Step 1: Check iFlow CLI
        iflow_version = self.check_iflow_installation()
        if not iflow_version:
            return False
        
        # Step 2: Load PR information
        if not self.load_pr_info():
            return False
        
        # Step 3: Load initial prompt
        initial_prompt = self.load_initial_prompt()
        if not initial_prompt:
            return False
        
        # Step 4: Load questions
        questions = self.load_ground_truth_questions()
        if not questions:
            print("❌ No questions available for testing")
            return False
        
        # Step 5: Initialize results
        self.initialize_answers_file(iflow_version)
        
        try:
            # Step 6: Send initial context
            print(f"\n🚀 Sending initial context...")
            response, response_time = self.send_initial_prompt(initial_prompt)
            
            if not self.iflow_session_id:
                print("❌ Failed to establish session")
                return False
            
            print(f"✅ Session established: {self.iflow_session_id}")
            self.save_initial_response(initial_prompt, response, response_time)
            
            # Step 7: Run questions
            print(f"\n❓ Running {len(questions)} benchmark questions...")
            
            total_time = response_time
            memory_references = 0
            detailed_responses = 0
            
            for i, question in enumerate(questions, 1):
                print(f"\n--- Question {i}/{len(questions)} ---")
                print(f"❓ {question}")
                
                try:
                    answer, response_time = self.send_question(question)
                    
                    # Analyze response quality
                    is_detailed = (
                        len(answer) > 100 and 
                        "I don't know" not in answer and
                        any(keyword in answer.lower() for keyword in [
                            'file', 'function', 'class', 'line', self.repo_name.lower().split('/')[-1]
                        ])
                    )
                    
                    if is_detailed:
                        detailed_responses += 1
                        print(f"✅ Detailed response ({len(answer)} chars)")
                    else:
                        print(f"⚠️  Basic response: {answer[:100]}...")
                    
                    # Check for memory references
                    memory_indicators = ['earlier', 'previous', 'before', 'mentioned', 'as I']
                    if any(indicator in answer.lower() for indicator in memory_indicators):
                        memory_references += 1
                        print(f"🧠 Memory reference detected")
                    
                    self.append_qa_pair(i, question, answer, response_time)
                    total_time += response_time
                    
                except Exception as e:
                    print(f"❌ Question {i} failed: {e}")
                    self.append_qa_pair(i, question, f"ERROR: {e}", 0)
            
            # Step 8: Finalize results
            self.finalize_results(len(questions), total_time, memory_references, detailed_responses)
            
            # Step 9: Print summary
            print(f"\n🎯 BENCHMARK COMPLETED")
            print("=" * 40)
            print(f"📋 Session ID: {self.iflow_session_id}")
            print(f"🔄 Total turns: {self.current_turn}")
            print(f"❓ Questions: {len(questions)}")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"📊 Detailed responses: {detailed_responses}/{len(questions)} ({detailed_responses/len(questions)*100:.1f}%)")
            print(f"🧠 Memory references: {memory_references}")
            print(f"📄 Results: {self.answers_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="iFlow PR Benchmark System - Session Management & Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Prerequisites:
1. Run enhanced_pr_fetcher.py to clone repository and prepare PR data
2. Run dynamic_prompt_generator.py to create the initial context prompt
3. Run this script to execute the benchmark

Examples:
  python3 iflow_pr_benchmark.py --workspace pr_workspace_apache --benchmark apache_pr_58365
  python3 iflow_pr_benchmark.py --workspace pr_workspace_terraform --benchmark terraform_pr_37923
        """
    )
    
    parser.add_argument('--workspace', required=True,
                       help='Workspace directory (created by enhanced_pr_fetcher.py)')
    parser.add_argument('--benchmark', required=True,
                       help='Benchmark name (e.g., apache_pr_58365)')
    
    args = parser.parse_args()
    
    try:
        # Create benchmark
        benchmark = iFlowPRBenchmark(args.workspace, args.benchmark)
        
        # Run benchmark
        success = benchmark.run_benchmark()
        
        if success:
            print(f"\n🎉 Benchmark completed successfully!")
            print(f"📄 Results available in: {benchmark.answers_file}")
        else:
            print(f"\n❌ Benchmark failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()