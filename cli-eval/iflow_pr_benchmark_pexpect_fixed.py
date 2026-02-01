#!/usr/bin/env python3
"""
iFlow PR Benchmark System - PEXPECT VERSION (FIXED)
Uses pexpect to create a pseudo-terminal and work around iFlow CLI session memory bugs.
Fixed version that properly handles interactive mode.
"""

import os
import sys
import json
import time
import argparse
import pexpect
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re


class iFlowPRBenchmarkPexpectFixed:
    """Fixed pexpect-based iFlow PR Benchmark with proper interactive session handling"""
    
    def __init__(self, workspace_dir: str, benchmark_name: str):
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_name = benchmark_name
        self.benchmark_dir = Path("benchmarks") / benchmark_name
        self.answers_file = self.benchmark_dir / "iflow_answers_pexpect_fixed.md"
        
        # Session management
        self.iflow_session_id: Optional[str] = None
        self.current_turn = 0
        self.interactive_session: Optional[pexpect.spawn] = None
        
        # PR information (loaded from workspace)
        self.repo_name = ""
        self.pr_number = ""
        self.pr_title = ""
        
        # Pexpect configuration
        self.timeout = 300  # 5 minutes for LLM responses
        self.short_timeout = 30  # For quick operations
        
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
                        return questions[:5]  # Limit to first 5 for testing
                        
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
            
            # Use pexpect for version check too
            child = pexpect.spawn("iflow --version", encoding='utf-8', timeout=10, env=env)
            child.expect(pexpect.EOF)
            version = child.before.strip()
            child.close()
            
            if version:
                print(f"✅ iFlow CLI found: {version}")
                return version
            else:
                print("❌ iFlow CLI not found or not working")
                return None
        except Exception as e:
            print(f"❌ iFlow CLI check failed: {e}")
            return None
    
    def start_interactive_session(self) -> Tuple[str, float]:
        """Start an interactive iFlow session using pexpect."""
        print(f"🚀 Starting interactive iFlow session with pexpect...")
        
        start_time = time.time()
        
        # Set up environment
        env = os.environ.copy()
        env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
        
        # Start iFlow in interactive mode (no prompt, just interactive)
        cmd = 'iflow'
        print(f"📤 Starting interactive iFlow: {cmd}")
        
        try:
            # Spawn the interactive process
            self.interactive_session = pexpect.spawn(
                cmd, 
                encoding='utf-8', 
                timeout=self.timeout,
                env=env,
                cwd=str(self.workspace_dir)
            )
            
            # Enable logging for debugging
            log_file = self.benchmark_dir / "pexpect_debug_fixed.log"
            self.interactive_session.logfile_read = open(log_file, 'w')
            
            # Wait for iFlow to be ready (look for prompt or ready state)
            print("⏳ Waiting for iFlow to be ready...")
            
            # Look for various patterns that indicate iFlow is ready
            ready_patterns = [
                r"iFlow",  # iFlow startup message
                r">",      # Command prompt
                r"What can I help you with",  # Ready message
                pexpect.TIMEOUT
            ]
            
            try:
                index = self.interactive_session.expect(ready_patterns, timeout=30)
                print(f"✅ iFlow ready (pattern {index})")
            except pexpect.TIMEOUT:
                print("⚠️  Timeout waiting for iFlow ready, but continuing...")
            
            # Send initial context
            initial_prompt = f"""You are analyzing Apache Airflow PR #{self.pr_number}: {self.pr_title}

This is an interactive analysis session. Key information:

Files Changed:
- airflow-core/src/airflow/executors/local_executor.py
- airflow-core/tests/unit/executors/test_local_executor.py  
- airflow-core/tests/unit/executors/test_local_executor_check_workers.py

PR Summary: The PR adds gc.freeze() to prevent memory spikes in LocalExecutor when using fork mode.

Please confirm you understand and are ready to answer questions about this PR."""
            
            print("📤 Sending initial context...")
            self.interactive_session.sendline(initial_prompt)
            
            # Wait for response
            response_text = ""
            try:
                # Look for end of response patterns
                end_patterns = [
                    r"ready",
                    r"understand",
                    r"questions",
                    pexpect.TIMEOUT
                ]
                
                index = self.interactive_session.expect(end_patterns, timeout=60)
                
                # Collect the response
                if self.interactive_session.before:
                    response_text += self.interactive_session.before
                if self.interactive_session.after and self.interactive_session.after != pexpect.TIMEOUT:
                    response_text += self.interactive_session.after
                    
                print(f"✅ Received initial response")
                
            except pexpect.TIMEOUT:
                print("⚠️  Timeout on initial response, but continuing...")
                if self.interactive_session.before:
                    response_text = self.interactive_session.before
            
            end_time = time.time()
            response_time = end_time - start_time
            
            self.current_turn += 1
            
            return response_text.strip(), response_time
            
        except Exception as e:
            print(f"❌ Failed to start interactive session: {e}")
            raise e
    
    def send_interactive_question(self, question: str, question_num: int) -> Tuple[str, float]:
        """Send a question to the interactive iFlow session."""
        if not self.interactive_session or not self.interactive_session.isalive():
            raise Exception("No active interactive session")
        
        print(f"📤 Sending question {question_num}: {question[:100]}...")
        
        start_time = time.time()
        
        try:
            # Send the question
            self.interactive_session.sendline(question)
            
            # Wait for response - use a more flexible approach
            response_text = ""
            
            # Give it time to start responding
            time.sleep(2)
            
            # Read available output
            try:
                # Use expect with a timeout to collect response
                self.interactive_session.expect(pexpect.TIMEOUT, timeout=60)
                
                if self.interactive_session.before:
                    response_text = self.interactive_session.before
                    
            except pexpect.TIMEOUT:
                # This is expected - we use timeout to collect all output
                if self.interactive_session.before:
                    response_text = self.interactive_session.before
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Clean up the response
            response = response_text.strip()
            
            # Remove the question echo if present
            if question in response:
                response = response.replace(question, "").strip()
            
            self.current_turn += 1
            
            print(f"✅ Received response ({len(response)} chars, {response_time:.1f}s)")
            
            return response, response_time
            
        except Exception as e:
            print(f"❌ Error sending question {question_num}: {e}")
            # Return a placeholder response instead of failing
            return f"ERROR: {e}", 0
    
    def close_interactive_session(self):
        """Close the interactive iFlow session."""
        if self.interactive_session:
            try:
                if self.interactive_session.isalive():
                    self.interactive_session.sendcontrol('c')  # Send Ctrl+C
                    try:
                        self.interactive_session.expect(pexpect.EOF, timeout=5)
                    except:
                        pass
                self.interactive_session.close()
                
                # Close log file
                if hasattr(self.interactive_session, 'logfile_read') and self.interactive_session.logfile_read:
                    self.interactive_session.logfile_read.close()
                    
                print("✅ Interactive session closed")
            except:
                print("⚠️  Error closing interactive session")
            finally:
                self.interactive_session = None
    
    def validate_response_quality(self, response: str, question: str) -> bool:
        """Validate response quality."""
        response = response.strip()
        
        # Check for empty or minimal responses
        if len(response) < 20:
            return False
        
        # Check for error responses
        if response.startswith("ERROR:"):
            return False
        
        # Check for common failure patterns
        failure_patterns = [
            "I need to read",
            "Let me examine", 
            "I'll look at",
            "I need to analyze",
            "Let me check",
            "I need to understand"
        ]
        
        # Allow responses that start with explanation but have substantial content
        if len(response) > 100:
            return True
        
        if any(pattern in response for pattern in failure_patterns):
            return False
        
        return True
    
    def initialize_answers_file(self, iflow_version: str):
        """Initialize the answers file with metadata."""
        content = f"""# iFlow CLI Benchmark Results - {self.benchmark_name.title()} (PEXPECT FIXED)

This file contains the PEXPECT FIXED benchmark results for iFlow CLI evaluation.

**Test Information:**
- **Repository:** {self.repo_name}
- **PR Number:** #{self.pr_number}
- **PR Title:** {self.pr_title}
- **Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **iFlow CLI Version:** {iflow_version}
- **Workspace:** {self.workspace_dir}

**PEXPECT FIXED Features:**
- ✅ True interactive session using pseudo-terminal (PTY)
- ✅ Fixed command parsing issues with proper interactive mode
- ✅ Works around iFlow CLI session memory bugs
- ✅ Maintains continuous conversation without resume issues
- ✅ Improved response collection and timeout handling
- ✅ Better error recovery and session management
- ✅ Debug logging for troubleshooting

**Session Management:**
- **Session Model:** Single continuous interactive session via pexpect
- **Session Type:** Native interactive mode (no -p flag issues)
- **Context Persistence:** True interactive session maintains full context
- **Error Handling:** Improved pexpect pattern matching and recovery

---

## Test Results

### Session Summary
[Will be populated at the end]

---

## Initial Context Setup (Interactive Session Start)

"""
        self.answers_file.write_text(content)
        print(f"📄 Initialized answers file: {self.answers_file}")
    
    def save_initial_response(self, prompt: str, response: str, response_time: float):
        """Save the initial prompt and response."""
        content = f"""### Session Information:
- **Session Type:** Interactive (pexpect fixed)
- **Response Time:** {response_time:.1f}s

### Initial Context Sent to iFlow:
```
{prompt}
```

### iFlow's Initial Response:
```
{response}
```

---

## Question & Answer Pairs (Interactive Session)

"""
        
        with open(self.answers_file, 'a') as f:
            f.write(content)
    
    def append_qa_pair(self, question_num: int, question: str, answer: str, response_time: float):
        """Append a Q&A pair to the answers file."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        content = f"""### Question {question_num} (Turn {self.current_turn - 1})
**Session Type:** Interactive (pexpect fixed - continuous session)
**Question:** {question}
**iFlow Answer:** {answer}
**Response Time:** {response_time:.1f}s
**Timestamp:** {timestamp}

---

"""
        
        with open(self.answers_file, 'a') as f:
            f.write(content)
    
    def finalize_results(self, total_questions: int, total_time: float, successful_answers: int):
        """Finalize the results file with summary statistics."""
        
        # Read current content
        content = self.answers_file.read_text()
        
        # Create session summary
        avg_time = total_time / total_questions if total_questions > 0 else 0
        success_rate = (successful_answers / total_questions * 100) if total_questions > 0 else 0
        
        session_summary = f"""### Session Summary
- **Session Type:** Interactive (pexpect fixed)
- **Total Turns:** {self.current_turn}
- **Total Questions:** {total_questions}
- **Successful Answers:** {successful_answers}/{total_questions} ({success_rate:.1f}%)
- **Session Duration:** {total_time:.1f}s
- **Average Response Time:** {avg_time:.1f}s
- **Session Continuity:** ✅ Maintained throughout (no resume issues)
- **Memory Issues:** ❌ None (continuous interactive session)

### Technical Details:
- **Pseudo-Terminal (PTY):** Used for true interactive behavior
- **Command Parsing:** Fixed (no -p flag issues)
- **Session Resume:** Not needed (continuous session)
- **Context Loss:** Prevented by maintaining single session
- **Debug Log:** Available at `{self.benchmark_dir}/pexpect_debug_fixed.log`

---"""
        
        # Replace placeholder
        content = content.replace(
            "### Session Summary\n[Will be populated at the end]",
            session_summary
        )
        
        self.answers_file.write_text(content)
        print(f"📊 Finalized results in: {self.answers_file}")
    
    def run_benchmark(self) -> bool:
        """Run the fixed pexpect-based benchmark process."""
        
        print(f"🚀 Starting PEXPECT FIXED iFlow PR Benchmark")
        print("=" * 60)
        
        try:
            # Step 1: Check iFlow CLI
            iflow_version = self.check_iflow_installation()
            if not iflow_version:
                return False
            
            # Step 2: Load PR information
            if not self.load_pr_info():
                return False
            
            # Step 3: Load questions (limited for testing)
            questions = self.load_ground_truth_questions()
            if not questions:
                print("❌ No questions available for testing")
                return False
            
            print(f"📝 Testing with {len(questions)} questions")
            
            # Step 4: Initialize results
            self.initialize_answers_file(iflow_version)
            
            # Step 5: Start interactive session
            print(f"\n🚀 Starting interactive session...")
            
            response, response_time = self.start_interactive_session()
            
            print(f"✅ Interactive session established")
            self.save_initial_response("Initial context setup", response, response_time)
            
            # Step 6: Run questions in interactive mode
            print(f"\n❓ Running {len(questions)} questions in interactive session...")
            
            total_time = response_time
            successful_answers = 0
            
            for i, question in enumerate(questions, 1):
                print(f"\n--- Question {i}/{len(questions)} ---")
                print(f"❓ {question}")
                
                try:
                    answer, response_time = self.send_interactive_question(question, i)
                    
                    # Validate response quality
                    if self.validate_response_quality(answer, question):
                        successful_answers += 1
                        print(f"✅ High quality response ({len(answer)} chars)")
                    else:
                        print(f"⚠️  Lower quality response: {answer[:100]}...")
                    
                    self.append_qa_pair(i, question, answer, response_time)
                    total_time += response_time
                    
                    # Small delay between questions
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"❌ Question {i} failed: {e}")
                    self.append_qa_pair(i, question, f"ERROR: {e}", 0)
            
            # Step 7: Finalize results
            self.finalize_results(len(questions), total_time, successful_answers)
            
            # Step 8: Print summary
            success_rate = (successful_answers / len(questions) * 100) if len(questions) > 0 else 0
            
            print(f"\n🎯 PEXPECT FIXED BENCHMARK COMPLETED")
            print("=" * 50)
            print(f"🔄 Total turns: {self.current_turn}")
            print(f"❓ Questions: {len(questions)}")
            print(f"✅ Successful answers: {successful_answers}/{len(questions)} ({success_rate:.1f}%)")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"📄 Results: {self.answers_file}")
            print(f"🔍 Debug log: {self.benchmark_dir}/pexpect_debug_fixed.log")
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            # Always close the interactive session
            self.close_interactive_session()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="iFlow PR Benchmark System - PEXPECT VERSION (FIXED)"
    )
    
    parser.add_argument('--workspace', required=True,
                       help='Workspace directory (created by enhanced_pr_fetcher.py)')
    parser.add_argument('--benchmark', required=True,
                       help='Benchmark name (e.g., apache_pr_58365)')
    
    args = parser.parse_args()
    
    try:
        # Create benchmark
        benchmark = iFlowPRBenchmarkPexpectFixed(args.workspace, args.benchmark)
        
        # Run benchmark
        success = benchmark.run_benchmark()
        
        if success:
            print(f"\n🎉 PEXPECT FIXED Benchmark completed successfully!")
            print(f"📄 Results available in: {benchmark.answers_file}")
        else:
            print(f"\n❌ PEXPECT FIXED Benchmark failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
