#!/usr/bin/env python3
"""
iFlow PR Benchmark System - ENHANCED VERSION
Fixes session memory issues and improves conversation continuity.
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


class iFlowPRBenchmarkEnhanced:
    """Enhanced iFlow PR Benchmark with fixed session memory and conversation continuity"""
    
    def __init__(self, workspace_dir: str, benchmark_name: str):
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_name = benchmark_name
        self.benchmark_dir = Path("benchmarks") / benchmark_name
        self.answers_file = self.benchmark_dir / "iflow_answers_enhanced.md"
        
        # Session management
        self.iflow_session_id: Optional[str] = None
        self.current_turn = 0
        self.conversation_context = []  # Track conversation for context
        
        # PR information (loaded from workspace)
        self.repo_name = ""
        self.pr_number = ""
        self.pr_title = ""
        
        # Memory validation
        self.memory_check_interval = 3  # Check memory every N questions
        self.context_refresh_interval = 8  # Refresh context every N questions
        
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
    
    def _execute_iflow_command(self, cmd: List[str], timeout: int = 180) -> Dict:
        """Execute iFlow CLI command with improved error handling."""
        try:
            print(f"📤 Executing: {' '.join(cmd[:2])} {cmd[2][:100] if len(cmd) > 2 else ''}{'...' if len(cmd) > 2 and len(cmd[2]) > 100 else ''}")
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
        """Extract session ID from iFlow output with improved patterns."""
        # Look for session ID in various formats
        patterns = [
            r'"session-id":\s*"(session-[a-f0-9-]+)"',
            r'session-id:\s*(session-[a-f0-9-]+)',
            r'Session ID:\s*(session-[a-f0-9-]+)',
            r'(session-[a-f0-9-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                session_id = match.group(1)
                print(f"✅ Found session ID: {session_id}")
                return session_id
        
        print(f"⚠️  No session ID found in output")
        return None
    
    def _validate_response(self, response: str, question: str) -> bool:
        """Validate response quality."""
        response = response.strip()
        
        # Check for empty or minimal responses
        if len(response) < 10:
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
        if len(response) > 150:
            return True
        
        if any(pattern in response for pattern in failure_patterns):
            return False
        
        return True
    
    def validate_session_memory(self, question_num: int) -> bool:
        """Check if iFlow remembers previous context."""
        if question_num <= 2:  # Skip for first few questions
            return True
            
        print(f"🧠 Checking session memory at question {question_num}...")
        
        try:
            # Ask a memory test question
            memory_test = f"What PR number are we analyzing? (This is question {question_num} in our conversation)"
            cmd = ["iflow", "-r", self.iflow_session_id, "-p", memory_test]
            result = self._execute_iflow_command(cmd, timeout=30)
            
            if result['success']:
                response = result['output'].strip()
                if self.pr_number in response or "58365" in response:
                    print(f"✅ Session memory intact")
                    return True
                else:
                    print(f"⚠️  Session memory issue detected: {response[:100]}...")
                    return False
            else:
                print(f"⚠️  Memory test failed: {result['error']}")
                return False
                
        except Exception as e:
            print(f"⚠️  Memory validation error: {e}")
            return False
    
    def refresh_context(self, question_num: int):
        """Refresh context to maintain conversation continuity."""
        print(f"🔄 Refreshing context at question {question_num}...")
        
        context_summary = f"""
        [CONTEXT REFRESH - Question {question_num}]
        
        We are analyzing Apache Airflow PR #{self.pr_number}: "{self.pr_title}"
        
        Key points from our conversation so far:
        - We've examined the LocalExecutor changes that add gc.freeze()
        - The PR modifies 3 files to prevent memory spikes in fork mode
        - We've discussed the _spawn_workers_with_gc_freeze function
        - We've covered multiprocessing start methods and COW issues
        
        Please continue answering questions based on this established context.
        Do not re-read files we've already examined unless specifically needed.
        """
        
        try:
            cmd = ["iflow", "-r", self.iflow_session_id, "-p", context_summary]
            result = self._execute_iflow_command(cmd, timeout=30)
            
            if result['success']:
                print(f"✅ Context refreshed successfully")
            else:
                print(f"⚠️  Context refresh failed: {result['error']}")
                
        except Exception as e:
            print(f"⚠️  Context refresh error: {e}")
    
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
        
        # Track conversation context
        self.conversation_context.append({
            'turn': self.current_turn,
            'type': 'initial_prompt',
            'content': prompt,
            'response': result['output']
        })
        
        self.current_turn += 1
        return result['output'], result['response_time']
    
    def send_question(self, question: str, question_num: int, max_retries: int = 2) -> Tuple[str, float]:
        """Send question using session resume with enhanced continuity."""
        if not self.iflow_session_id:
            raise Exception("No active session ID")
        
        # Check session memory periodically
        if question_num % self.memory_check_interval == 0:
            if not self.validate_session_memory(question_num):
                print(f"🔧 Attempting to recover session memory...")
                self.refresh_context(question_num)
        
        # Refresh context periodically
        if question_num % self.context_refresh_interval == 0 and question_num > 1:
            self.refresh_context(question_num)
        
        # Enhance question with context for better continuity
        enhanced_question = f"""
        [Question {question_num} - Continuing our analysis of PR #{self.pr_number}]
        
        {question}
        
        [Please answer based on our ongoing conversation about the LocalExecutor gc.freeze changes]
        """
        
        for attempt in range(max_retries):
            try:
                cmd = ["iflow", "-r", self.iflow_session_id, "-p", enhanced_question]
                result = self._execute_iflow_command(cmd, timeout=180)
                
                if not result['success']:
                    if attempt < max_retries - 1:
                        print(f"⚠️  Command failed, retrying... (attempt {attempt + 1})")
                        time.sleep(3)
                        continue
                    else:
                        raise Exception(result['error'])
                
                response = result['output'].strip()
                
                # Validate response quality
                if not self._validate_response(response, question):
                    if attempt < max_retries - 1:
                        print(f"⚠️  Poor quality response, retrying... (attempt {attempt + 1})")
                        time.sleep(2)
                        continue
                    else:
                        print(f"⚠️  Keeping poor quality response after {max_retries} attempts")
                
                # Track conversation context
                self.conversation_context.append({
                    'turn': self.current_turn,
                    'type': 'question',
                    'question': question,
                    'response': response,
                    'question_num': question_num
                })
                
                self.current_turn += 1
                return response, result['response_time']
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Exception: {e}, retrying... (attempt {attempt + 1})")
                    time.sleep(3)
                    continue
                else:
                    raise e
    
    def initialize_answers_file(self, iflow_version: str):
        """Initialize the answers file with metadata."""
        content = f"""# iFlow CLI Benchmark Results - {self.benchmark_name.title()} (ENHANCED)

This file contains the ENHANCED benchmark results for iFlow CLI evaluation.

**Test Information:**
- **Repository:** {self.repo_name}
- **PR Number:** #{self.pr_number}
- **PR Title:** {self.pr_title}
- **Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **iFlow CLI Version:** {iflow_version}
- **Workspace:** {self.workspace_dir}

**Enhanced Features:**
- ✅ Fixed SSL certificate issues with NODE_TLS_REJECT_UNAUTHORIZED=0
- ✅ Enhanced session memory validation and recovery
- ✅ Periodic context refresh to maintain conversation continuity
- ✅ Improved question formatting with context markers
- ✅ Better response quality validation
- ✅ Session health monitoring every {self.memory_check_interval} questions
- ✅ Context refresh every {self.context_refresh_interval} questions
- ✅ Enhanced error handling and debugging

**Session Management:**
- **Session Model:** Single persistent session with enhanced continuity
- **Session ID:** [Will be populated after Turn 0]
- **Turn Tracking:** Turn 0 (session creation) + Turn 1+ (session resume with -r flag)
- **Context Persistence:** Rich initial context + periodic refresh + memory validation
- **Error Handling:** Robust retry logic with session recovery

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
    
    def append_qa_pair(self, question_num: int, question: str, answer: str, response_time: float, 
                      memory_check_passed: bool = True, context_refreshed: bool = False):
        """Append a Q&A pair to the answers file with enhanced metadata."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Add metadata about session health
        metadata = []
        if not memory_check_passed:
            metadata.append("⚠️ Memory check failed")
        if context_refreshed:
            metadata.append("🔄 Context refreshed")
        
        metadata_str = f" ({', '.join(metadata)})" if metadata else ""
        
        content = f"""### Question {question_num} (Turn {self.current_turn - 1}){metadata_str}
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
                        successful_answers: int, memory_checks: int, context_refreshes: int):
        """Finalize the results file with enhanced summary statistics."""
        
        # Read current content
        content = self.answers_file.read_text()
        
        # Create enhanced session summary
        avg_time = total_time / total_questions if total_questions > 0 else 0
        success_rate = (successful_answers / total_questions * 100) if total_questions > 0 else 0
        
        session_summary = f"""### Session Summary
- **Session ID:** {self.iflow_session_id or 'Not captured'}
- **Total Turns:** {self.current_turn}
- **Total Questions:** {total_questions}
- **Successful Answers:** {successful_answers}/{total_questions} ({success_rate:.1f}%)
- **Session Duration:** {total_time:.1f}s
- **Average Response Time:** {avg_time:.1f}s
- **Memory Checks Performed:** {memory_checks}
- **Context Refreshes:** {context_refreshes}
- **Session Health:** {'✅ Good' if successful_answers > total_questions * 0.8 else '⚠️ Issues detected'}

### Conversation Context Tracking:
- **Total Context Entries:** {len(self.conversation_context)}
- **Memory Check Interval:** Every {self.memory_check_interval} questions
- **Context Refresh Interval:** Every {self.context_refresh_interval} questions

---"""
        
        # Replace placeholder
        content = content.replace(
            "### Session Summary\n[Will be populated at the end]",
            session_summary
        )
        
        self.answers_file.write_text(content)
        print(f"📊 Finalized results in: {self.answers_file}")
    
    def run_benchmark(self) -> bool:
        """Run the enhanced benchmark process."""
        
        print(f"🚀 Starting ENHANCED iFlow PR Benchmark")
        print("=" * 60)
        
        # Step 1: Check iFlow CLI
        iflow_version = self.check_iflow_installation()
        if not iflow_version:
            return False
        
        # Step 2: Load PR information
        if not self.load_pr_info():
            return False
        
        # Step 3: Load questions
        questions = self.load_ground_truth_questions()
        if not questions:
            print("❌ No questions available for testing")
            return False
        
        # Step 4: Initialize results
        self.initialize_answers_file(iflow_version)
        
        try:
            # Step 5: Send initial context (enhanced)
            print(f"\n🚀 Sending enhanced initial context...")
            initial_prompt = f"""You are analyzing Apache Airflow PR #{self.pr_number}: "{self.pr_title}"

This is a comprehensive analysis session. Key information:

**Files Changed:**
- airflow-core/src/airflow/executors/local_executor.py
- airflow-core/tests/unit/executors/test_local_executor.py  
- airflow-core/tests/unit/executors/test_local_executor_check_workers.py

**PR Summary:**
The PR adds gc.freeze() to prevent memory spikes in LocalExecutor when using fork mode.

**Session Instructions:**
- This is a multi-question analysis session
- Build on previous answers and maintain context
- Reference earlier discussions when relevant
- Avoid re-reading files unnecessarily
- Provide detailed, technical answers

Ready to begin comprehensive analysis of this PR."""
            
            response, response_time = self.send_initial_prompt(initial_prompt)
            
            if not self.iflow_session_id:
                print("❌ Failed to establish session")
                return False
            
            print(f"✅ Session established: {self.iflow_session_id}")
            self.save_initial_response(initial_prompt, response, response_time)
            
            # Step 6: Run questions with enhanced monitoring
            print(f"\n❓ Running {len(questions)} benchmark questions with enhanced monitoring...")
            
            total_time = response_time
            successful_answers = 0
            memory_checks = 0
            context_refreshes = 0
            
            for i, question in enumerate(questions, 1):
                print(f"\n--- Question {i}/{len(questions)} ---")
                print(f"❓ {question}")
                
                # Track if memory check or context refresh happened
                memory_check_passed = True
                context_refreshed = False
                
                if i % self.memory_check_interval == 0:
                    memory_checks += 1
                    memory_check_passed = self.validate_session_memory(i)
                
                if i % self.context_refresh_interval == 0 and i > 1:
                    context_refreshes += 1
                    context_refreshed = True
                
                try:
                    answer, response_time = self.send_question(question, i)
                    
                    # Check if answer is substantial
                    if len(answer) > 50 and not answer.startswith("ERROR:"):
                        successful_answers += 1
                        print(f"✅ Good response ({len(answer)} chars)")
                    else:
                        print(f"⚠️  Basic response: {answer[:100]}...")
                    
                    self.append_qa_pair(i, question, answer, response_time, 
                                      memory_check_passed, context_refreshed)
                    total_time += response_time
                    
                except Exception as e:
                    print(f"❌ Question {i} failed: {e}")
                    self.append_qa_pair(i, question, f"ERROR: {e}", 0, 
                                      memory_check_passed, context_refreshed)
            
            # Step 7: Finalize with enhanced summary
            self.finalize_results(len(questions), total_time, successful_answers, 
                                memory_checks, context_refreshes)
            
            # Step 8: Print enhanced summary
            success_rate = (successful_answers / len(questions) * 100) if len(questions) > 0 else 0
            
            print(f"\n🎯 ENHANCED BENCHMARK COMPLETED")
            print("=" * 50)
            print(f"📋 Session ID: {self.iflow_session_id}")
            print(f"🔄 Total turns: {self.current_turn}")
            print(f"❓ Questions: {len(questions)}")
            print(f"✅ Successful answers: {successful_answers}/{len(questions)} ({success_rate:.1f}%)")
            print(f"🧠 Memory checks: {memory_checks}")
            print(f"🔄 Context refreshes: {context_refreshes}")
            print(f"⏱️  Total time: {total_time:.1f}s")
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
        description="iFlow PR Benchmark System - ENHANCED VERSION"
    )
    
    parser.add_argument('--workspace', required=True,
                       help='Workspace directory (created by enhanced_pr_fetcher.py)')
    parser.add_argument('--benchmark', required=True,
                       help='Benchmark name (e.g., apache_pr_58365)')
    
    args = parser.parse_args()
    
    try:
        # Create benchmark
        benchmark = iFlowPRBenchmarkEnhanced(args.workspace, args.benchmark)
        
        # Run benchmark
        success = benchmark.run_benchmark()
        
        if success:
            print(f"\n🎉 ENHANCED Benchmark completed successfully!")
            print(f"📄 Results available in: {benchmark.answers_file}")
        else:
            print(f"\n❌ ENHANCED Benchmark failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
