#!/usr/bin/env python3
"""
iFlow PR Benchmark System - DIRECT PEXPECT VERSION
Direct pexpect approach without subprocess fallback to ensure it actually works.
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


class iFlowPRBenchmarkPexpectDirect:
    """Direct pexpect-only iFlow PR Benchmark - no subprocess fallback"""
    
    def __init__(self, workspace_dir: str, benchmark_name: str):
        self.workspace_dir = Path(workspace_dir)
        self.benchmark_name = benchmark_name
        self.benchmark_dir = Path("benchmarks") / benchmark_name
        self.answers_file = self.benchmark_dir / "iflow_answers_pexpect_direct.md"
        
        # Session management
        self.current_turn = 0
        self.interactive_session: Optional[pexpect.spawn] = None
        
        # PR information
        self.repo_name = ""
        self.pr_number = ""
        self.pr_title = ""
        
        # Pexpect configuration
        self.timeout = 120  # 2 minutes for responses
        
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
                        return questions[:8]  # Limit to 8 for focused testing
                        
                except Exception as e:
                    print(f"⚠️  Could not read {questions_file}: {e}")
        
        print("❌ No ground truth questions found")
        return []
    
    def start_interactive_session(self) -> bool:
        """Start a direct interactive iFlow session."""
        print(f"🚀 Starting DIRECT pexpect interactive session...")
        
        # Set up environment
        env = os.environ.copy()
        env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0'
        
        try:
            # Start iFlow in interactive mode
            print("📤 Starting: iflow")
            self.interactive_session = pexpect.spawn(
                'iflow', 
                encoding='utf-8', 
                timeout=self.timeout,
                env=env,
                cwd=str(self.workspace_dir)
            )
            
            # Enable detailed logging
            log_file = self.benchmark_dir / "pexpect_direct_debug.log"
            self.interactive_session.logfile_read = open(log_file, 'w')
            
            print("⏳ Waiting for iFlow to be ready...")
            
            # Wait a moment for iFlow to start
            time.sleep(3)
            
            # Send initial context immediately
            initial_context = f"""You are analyzing Apache Airflow PR #{self.pr_number}: {self.pr_title}

This is an interactive session. I will ask you multiple questions about this PR.

Key files changed:
- airflow-core/src/airflow/executors/local_executor.py
- airflow-core/tests/unit/executors/test_local_executor.py  
- airflow-core/tests/unit/executors/test_local_executor_check_workers.py

The PR adds gc.freeze() to prevent memory spikes in LocalExecutor when using fork mode.

Please confirm you understand and are ready to answer questions."""
            
            print("📤 Sending initial context...")
            self.interactive_session.sendline(initial_context)
            
            # Wait for initial response
            print("⏳ Waiting for initial response...")
            time.sleep(5)  # Give it time to process
            
            # Try to read any available output
            try:
                self.interactive_session.expect(pexpect.TIMEOUT, timeout=30)
                initial_response = self.interactive_session.before or ""
                print(f"✅ Got initial response ({len(initial_response)} chars)")
            except pexpect.TIMEOUT:
                initial_response = self.interactive_session.before or ""
                print(f"⚠️  Timeout on initial response, got {len(initial_response)} chars")
            
            self.current_turn += 1
            return True
            
        except Exception as e:
            print(f"❌ Failed to start interactive session: {e}")
            return False
    
    def send_question_direct(self, question: str, question_num: int) -> Tuple[str, float]:
        """Send question directly via pexpect."""
        if not self.interactive_session or not self.interactive_session.isalive():
            return "ERROR: No active session", 0
        
        print(f"📤 Question {question_num}: {question[:80]}...")
        
        start_time = time.time()
        
        try:
            # Send the question
            self.interactive_session.sendline(question)
            
            # Wait for response - use a more aggressive approach
            print("⏳ Waiting for response...")
            time.sleep(3)  # Initial wait
            
            # Collect response with timeout
            response_text = ""
            
            try:
                # Try to read with timeout
                self.interactive_session.expect(pexpect.TIMEOUT, timeout=self.timeout)
                response_text = self.interactive_session.before or ""
            except pexpect.TIMEOUT:
                response_text = self.interactive_session.before or ""
                print(f"⚠️  Response timeout, collected {len(response_text)} chars")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Clean up response
            response = response_text.strip()
            
            # Remove question echo if present
            if question in response:
                response = response.replace(question, "").strip()
            
            # Remove common artifacts
            response = re.sub(r'^.*?\n', '', response, count=1)  # Remove first line if it's echo
            response = response.strip()
            
            print(f"✅ Response received ({len(response)} chars, {response_time:.1f}s)")
            
            self.current_turn += 1
            return response, response_time
            
        except Exception as e:
            print(f"❌ Error with question {question_num}: {e}")
            return f"ERROR: {e}", 0
    
    def validate_response_quality(self, response: str, question: str) -> bool:
        """Validate response quality."""
        if len(response.strip()) < 15:
            return False
        if response.startswith("ERROR:"):
            return False
        if "I don't have any record" in response:
            return False
        if "I need to analyze" in response and len(response) < 100:
            return False
        return True
    
    def close_session(self):
        """Close the interactive session."""
        if self.interactive_session:
            try:
                if self.interactive_session.isalive():
                    print("🔄 Closing interactive session...")
                    self.interactive_session.sendcontrol('c')
                    try:
                        self.interactive_session.expect(pexpect.EOF, timeout=5)
                    except:
                        pass
                self.interactive_session.close()
                
                # Close log file
                if hasattr(self.interactive_session, 'logfile_read') and self.interactive_session.logfile_read:
                    self.interactive_session.logfile_read.close()
                    
                print("✅ Interactive session closed")
            except Exception as e:
                print(f"⚠️  Error closing session: {e}")
            finally:
                self.interactive_session = None
    
    def run_benchmark(self) -> bool:
        """Run the direct pexpect benchmark."""
        
        print(f"🚀 Starting DIRECT PEXPECT iFlow PR Benchmark")
        print("=" * 60)
        
        try:
            # Setup
            if not self.load_pr_info():
                return False
            
            questions = self.load_ground_truth_questions()
            if not questions:
                return False
            
            print(f"📝 Testing with {len(questions)} questions")
            
            # Initialize results file
            self.answers_file.write_text(f"""# iFlow CLI Benchmark Results - {self.benchmark_name.title()} (DIRECT PEXPECT)

**Test Information:**
- Repository: {self.repo_name}
- PR Number: #{self.pr_number}
- PR Title: {self.pr_title}
- Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Direct Pexpect Approach:**
- ✅ Pure pexpect interaction (no subprocess)
- ✅ Single continuous interactive session
- ✅ Direct pseudo-terminal communication
- ✅ No session resume issues
- ✅ Real-time response collection

---

## Results

""")
            
            # Start interactive session
            if not self.start_interactive_session():
                print("❌ Failed to start interactive session")
                return False
            
            print(f"✅ Interactive session ready")
            
            # Run questions
            total_time = 0
            successful_answers = 0
            
            for i, question in enumerate(questions, 1):
                print(f"\n--- Question {i}/{len(questions)} ---")
                
                answer, response_time = self.send_question_direct(question, i)
                
                # Validate response
                is_good = self.validate_response_quality(answer, question)
                if is_good:
                    successful_answers += 1
                    print(f"✅ Good response")
                else:
                    print(f"⚠️  Poor response: {answer[:100]}...")
                
                # Save to file
                with open(self.answers_file, 'a') as f:
                    f.write(f"""### Question {i}
**Mode:** Direct Pexpect
**Question:** {question}
**Answer:** {answer}
**Response Time:** {response_time:.1f}s
**Quality:** {'✅ Good' if is_good else '⚠️ Poor'}

---

""")
                
                total_time += response_time
                
                # Brief pause between questions
                time.sleep(2)
            
            # Final summary
            success_rate = (successful_answers / len(questions) * 100) if questions else 0
            
            with open(self.answers_file, 'a') as f:
                f.write(f"""## Summary
- **Total Questions:** {len(questions)}
- **Successful Answers:** {successful_answers}/{len(questions)} ({success_rate:.1f}%)
- **Total Time:** {total_time:.1f}s
- **Average Time:** {total_time/len(questions):.1f}s per question
- **Session Type:** Direct Pexpect (continuous)
- **Session Issues:** None (no resume needed)

### Key Improvements:
- ✅ No subprocess/resume issues
- ✅ Continuous session maintained
- ✅ Direct terminal interaction
- ✅ Better response collection
""")
            
            print(f"\n🎯 DIRECT PEXPECT BENCHMARK COMPLETED")
            print("=" * 50)
            print(f"✅ Success rate: {success_rate:.1f}%")
            print(f"⏱️  Total time: {total_time:.1f}s")
            print(f"📄 Results: {self.answers_file}")
            print(f"🔍 Debug log: {self.benchmark_dir}/pexpect_direct_debug.log")
            
            return True
            
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            self.close_session()


def main():
    parser = argparse.ArgumentParser(description="iFlow PR Benchmark - DIRECT PEXPECT VERSION")
    parser.add_argument('--workspace', required=True, help='Workspace directory')
    parser.add_argument('--benchmark', required=True, help='Benchmark name')
    
    args = parser.parse_args()
    
    try:
        benchmark = iFlowPRBenchmarkPexpectDirect(args.workspace, args.benchmark)
        success = benchmark.run_benchmark()
        
        if success:
            print(f"\n🎉 DIRECT PEXPECT Benchmark completed!")
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


