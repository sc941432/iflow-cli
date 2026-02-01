#!/usr/bin/env python3
"""
iFlow PR Benchmark System - HYBRID VERSION
Combines the best of enhanced session management and pexpect for maximum reliability.
"""

import os
import sys
import json
import time
import argparse
import subprocess
import pexpect
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import re


class iFlowPRBenchmarkHybrid:
    """Hybrid iFlow PR Benchmark combining enhanced session management with pexpect fallback"""
    
    def __init__(self, workspace_dir: str, benchmark_name: str):
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_name = benchmark_name
        self.benchmark_dir = Path("benchmarks") / benchmark_name
        self.answers_file = self.benchmark_dir / "iflow_answers_hybrid.md"
        
        # Session management
        self.iflow_session_id: Optional[str] = None
        self.current_turn = 0
        self.use_pexpect = False  # Start with subprocess, fallback to pexpect
        self.interactive_session: Optional[pexpect.spawn] = None
        
        # PR information
        self.repo_name = ""
        self.pr_number = ""
        self.pr_title = ""
        
        # Configuration
        self.memory_check_interval = 3
        self.context_refresh_interval = 8
        self.max_failures_before_pexpect = 2
        self.current_failures = 0
        
        # Ensure directories exist
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.workspace_dir.exists():
            raise FileNotFoundError(f"Workspace directory not found: {workspace_dir}")
    
    def load_pr_info(self) -> bool:
        """Load PR information from workspace files."""
        print("📋 Loading PR information from workspace...")
        
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
        """Load ground truth questions."""
        print("📝 Loading ground truth questions...")
        
        questions_files = [
            self.workspace_dir / "ground_truth_questions.md",
            self.benchmark_dir / "ground_truth_questions.md"
        ]
        
        for questions_file in questions_files:
            if questions_file.exists():
                try:
                    content = questions_file.read_text()
                    questions = []
                    
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
                        return questions[:10]  # Limit for testing
                        
                except Exception as e:
                    print(f"⚠️  Could not read {questions_file}: {e}")
        
        print("❌ No ground truth questions found")
        return []
    
    def check_iflow_installation(self) -> Optional[str]:
        """Check if iFlow CLI is installed."""
        try:
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
    
    def _execute_subprocess_command(self, cmd: List[str], timeout: int = 180) -> Dict:
        """Execute iFlow CLI command using subprocess."""
        try:
            print(f"📤 Subprocess: {' '.join(cmd[:2])} {cmd[2][:100] if len(cmd) > 2 else ''}{'...' if len(cmd) > 2 and len(cmd[2]) > 100 else ''}")
            
            start_time = time.time()
            
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
                return {
                    'success': False,
                    'output': result.stdout,
                    'error': f"Exit {result.returncode}: {result.stderr}",
                    'response_time': response_time
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f"Timeout after {timeout}s",
                'response_time': timeout
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f"Execution failed: {e}",
                'response_time': 0
            }
    
    def _switch_to_pexpect(self):
        """Switch to pexpect mode when subprocess fails."""
        print("🔄 Switching to pexpect mode for better session handling...")
        self.use_pexpect = True
        
        try:
            # Start interactive session
            env = os.environ.copy()
            env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
            
            self.interactive_session = pexpect.spawn(
                'iflow', 
                encoding='utf-8', 
                timeout=300,
                env=env,
                cwd=str(self.workspace_dir)
            )
            
            # Enable logging
            log_file = self.benchmark_dir / "pexpect_hybrid.log"
            self.interactive_session.logfile_read = open(log_file, 'w')
            
            print("✅ Pexpect session started")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start pexpect session: {e}")
            return False
    
    def _send_pexpect_question(self, question: str, question_num: int) -> Tuple[str, float]:
        """Send question using pexpect."""
        if not self.interactive_session or not self.interactive_session.isalive():
            raise Exception("No active pexpect session")
        
        start_time = time.time()
        
        try:
            self.interactive_session.sendline(question)
            
            # Wait for response with timeout
            time.sleep(3)  # Give it time to respond
            
            try:
                self.interactive_session.expect(pexpect.TIMEOUT, timeout=60)
                response = self.interactive_session.before or ""
            except pexpect.TIMEOUT:
                response = self.interactive_session.before or ""
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Clean response
            response = response.strip()
            if question in response:
                response = response.replace(question, "").strip()
            
            return response, response_time
            
        except Exception as e:
            return f"PEXPECT ERROR: {e}", 0
    
    def _extract_session_id(self, output: str) -> Optional[str]:
        """Extract session ID from output."""
        patterns = [
            r'"session-id":\s*"(session-[a-f0-9-]+)"',
            r'session-id:\s*(session-[a-f0-9-]+)',
            r'(session-[a-f0-9-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def validate_session_memory(self, question_num: int) -> bool:
        """Check if session remembers context."""
        if question_num <= 2:
            return True
            
        print(f"🧠 Checking session memory at question {question_num}...")
        
        try:
            memory_test = f"What PR number are we analyzing? (Question {question_num})"
            
            if self.use_pexpect:
                response, _ = self._send_pexpect_question(memory_test, question_num)
            else:
                cmd = ["iflow", "-r", self.iflow_session_id, "-p", memory_test]
                result = self._execute_subprocess_command(cmd, timeout=30)
                response = result['output'] if result['success'] else ""
            
            if self.pr_number in response or "58365" in response:
                print(f"✅ Session memory intact")
                return True
            else:
                print(f"⚠️  Session memory issue: {response[:100]}...")
                return False
                
        except Exception as e:
            print(f"⚠️  Memory validation error: {e}")
            return False
    
    def send_initial_prompt(self, prompt: str) -> Tuple[str, float]:
        """Send initial prompt using subprocess."""
        print(f"🚀 Creating initial session...")
        
        cmd = ["iflow", "-p", prompt]
        result = self._execute_subprocess_command(cmd, timeout=180)
        
        if not result['success']:
            raise Exception(result['error'])
        
        combined_output = result['output'] + '\n' + result['error']
        self.iflow_session_id = self._extract_session_id(combined_output)
        
        if self.iflow_session_id:
            print(f"✅ Session ID: {self.iflow_session_id}")
        else:
            print("⚠️  No session ID found")
        
        self.current_turn += 1
        return result['output'], result['response_time']
    
    def send_question(self, question: str, question_num: int) -> Tuple[str, float]:
        """Send question with hybrid approach."""
        
        # Check memory periodically
        if question_num % self.memory_check_interval == 0:
            memory_ok = self.validate_session_memory(question_num)
            if not memory_ok:
                self.current_failures += 1
        
        # Switch to pexpect if too many failures
        if self.current_failures >= self.max_failures_before_pexpect and not self.use_pexpect:
            if self._switch_to_pexpect():
                # Send context to pexpect session
                context = f"We are analyzing Apache Airflow PR #{self.pr_number} about gc.freeze in LocalExecutor."
                self._send_pexpect_question(context, 0)
        
        # Enhanced question with context
        enhanced_question = f"""[Question {question_num} - PR #{self.pr_number} Analysis]

{question}

[Please answer based on our ongoing analysis of the LocalExecutor gc.freeze changes]"""
        
        try:
            if self.use_pexpect:
                response, response_time = self._send_pexpect_question(enhanced_question, question_num)
            else:
                cmd = ["iflow", "-r", self.iflow_session_id, "-p", enhanced_question]
                result = self._execute_subprocess_command(cmd, timeout=180)
                
                if result['success']:
                    response = result['output']
                    response_time = result['response_time']
                else:
                    # Failure - increment counter
                    self.current_failures += 1
                    response = f"SUBPROCESS ERROR: {result['error']}"
                    response_time = 0
            
            self.current_turn += 1
            return response, response_time
            
        except Exception as e:
            self.current_failures += 1
            return f"ERROR: {e}", 0
    
    def validate_response_quality(self, response: str) -> bool:
        """Validate response quality."""
        if len(response.strip()) < 20:
            return False
        if response.startswith("ERROR:"):
            return False
        if "I don't have any record" in response:
            return False
        return True
    
    def close_sessions(self):
        """Close all active sessions."""
        if self.interactive_session:
            try:
                if self.interactive_session.isalive():
                    self.interactive_session.sendcontrol('c')
                    self.interactive_session.expect(pexpect.EOF, timeout=5)
                self.interactive_session.close()
                if hasattr(self.interactive_session, 'logfile_read'):
                    self.interactive_session.logfile_read.close()
            except:
                pass
    
    def run_benchmark(self) -> bool:
        """Run the hybrid benchmark."""
        
        print(f"🚀 Starting HYBRID iFlow PR Benchmark")
        print("=" * 60)
        
        try:
            # Setup
            iflow_version = self.check_iflow_installation()
            if not iflow_version:
                return False
            
            if not self.load_pr_info():
                return False
            
            questions = self.load_ground_truth_questions()
            if not questions:
                return False
            
            # Initialize results file
            self.answers_file.write_text(f"""# iFlow CLI Benchmark Results - {self.benchmark_name.title()} (HYBRID)

**Test Information:**
- Repository: {self.repo_name}
- PR Number: #{self.pr_number}
- PR Title: {self.pr_title}
- Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- iFlow CLI Version: {iflow_version}

**Hybrid Approach:**
- ✅ Starts with subprocess for speed
- ✅ Switches to pexpect when session issues detected
- ✅ Memory validation every {self.memory_check_interval} questions
- ✅ Automatic fallback on {self.max_failures_before_pexpect} failures
- ✅ Enhanced error recovery

---

## Results

""")
            
            # Send initial context
            initial_prompt = f"""You are analyzing Apache Airflow PR #{self.pr_number}: {self.pr_title}

Key files changed:
- airflow-core/src/airflow/executors/local_executor.py
- airflow-core/tests/unit/executors/test_local_executor.py  
- airflow-core/tests/unit/executors/test_local_executor_check_workers.py

The PR adds gc.freeze() to prevent memory spikes in LocalExecutor when using fork mode.

Ready to answer detailed questions about this PR."""
            
            response, response_time = self.send_initial_prompt(initial_prompt)
            
            # Run questions
            total_time = response_time
            successful_answers = 0
            
            for i, question in enumerate(questions, 1):
                print(f"\n--- Question {i}/{len(questions)} ---")
                print(f"❓ {question}")
                print(f"🔧 Mode: {'Pexpect' if self.use_pexpect else 'Subprocess'}")
                
                answer, response_time = self.send_question(question, i)
                
                if self.validate_response_quality(answer):
                    successful_answers += 1
                    print(f"✅ Good response ({len(answer)} chars)")
                else:
                    print(f"⚠️  Poor response: {answer[:100]}...")
                
                # Save to file
                with open(self.answers_file, 'a') as f:
                    f.write(f"""### Question {i}
**Mode:** {'Pexpect' if self.use_pexpect else 'Subprocess'}
**Question:** {question}
**Answer:** {answer}
**Response Time:** {response_time:.1f}s

---

""")
                
                total_time += response_time
                time.sleep(1)  # Brief pause
            
            # Final summary
            success_rate = (successful_answers / len(questions) * 100) if questions else 0
            
            with open(self.answers_file, 'a') as f:
                f.write(f"""## Summary
- **Total Questions:** {len(questions)}
- **Successful Answers:** {successful_answers}/{len(questions)} ({success_rate:.1f}%)
- **Total Time:** {total_time:.1f}s
- **Mode Switches:** {'Yes' if self.use_pexpect else 'No'}
- **Failures Before Switch:** {self.current_failures}
""")
            
            print(f"\n🎯 HYBRID BENCHMARK COMPLETED")
            print(f"✅ Success rate: {success_rate:.1f}%")
            print(f"🔧 Final mode: {'Pexpect' if self.use_pexpect else 'Subprocess'}")
            print(f"📄 Results: {self.answers_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            return False
            
        finally:
            self.close_sessions()


def main():
    parser = argparse.ArgumentParser(description="iFlow PR Benchmark - HYBRID VERSION")
    parser.add_argument('--workspace', required=True, help='Workspace directory')
    parser.add_argument('--benchmark', required=True, help='Benchmark name')
    
    args = parser.parse_args()
    
    try:
        benchmark = iFlowPRBenchmarkHybrid(args.workspace, args.benchmark)
        success = benchmark.run_benchmark()
        
        if success:
            print(f"\n🎉 HYBRID Benchmark completed!")
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
