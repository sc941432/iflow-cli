# apache/airflow - PR #58365 Context

## Repository Information
- **Repository:** apache/airflow
- **Clone URL:** https://github.com/apache/airflow.git
- **Local Path:** pr_workspace_apache/airflow
- **Current Branch:** pr-58365

## PR Information
**Title:** Fix LocalExecutor memory spike by applying gc.freeze
**Author:** wjddn279
**Status:** open
**Base Branch:** main → **Head Branch:** fix-local-executor-cow-issue

**Statistics:**
- Commits: 8
- Files Changed: 3
- Additions: +60 lines
- Deletions: -8 lines

## PR Description
related: https://github.com/apache/airflow/discussions/58143

### Body
As discussed (not confirmed yet), this resolves the issue of sudden memory usage spikes in worker processes when using LocalExecutor. Memory increases due to unnecessary copying of read-only shared memory through COW caused by gc. By applying gc.freeze and moving existing objects to the permanent generation, we prevent COW from occurring.

When using fork mode, we create many worker processes at once to minimize gc.freeze and unfreeze calls. When using spawn mode, we maintain the existing approach to ensure stability.

### Benchmark

#### memory usage
Comparison of per-process memory usage in LocalExecutor before and after applying this PR. Measured in the same environment running 500 tasks per minute for 12 hours.
| AS-IS | TO-BE |
|-------|-------|
| [smem_as-is.txt](https://github.com/user-attachments/files/23567938/smem_as-is.txt) | [smem_to-be.txt](https://github.com/user-attachments/files/23567942/smem_to-be.txt) |
| <img width="400" alt="AS-IS" src="https://github.com/user-attachments/assets/53e6122a-5b39-46c6-a862-b635d53d3993" /> | <img width="400" alt="TO-BE" src="https://github.com/user-attachments/assets/9796032f-6d8d-4234-91eb-e2aa186381ba" /> |

#### gc.freeze / unfreeze performance (elapsed time)
We measured the elapsed time of gc.freeze and gc.unfreeze for each scheduler loop iteration. Most operations took microseconds, confirming virtually no impact. The actual operation is a very lightweight process that simply marks objects in the current generation as permanent generation without any memory copying.https://github.com/python/cpython/pull/3705/files
```
[airflow.jobs.scheduler_job_runner.SchedulerJobRunner] loc=scheduler_job_runner.py:1375
2025-11-15T05:13:36.911715Z [info     ] freeze: 18.83 μs               [airflow.jobs.scheduler_job_runner.SchedulerJobRunner] loc=scheduler_job_runner.py:1366
2025-11-15T05:13:36.912238Z [info     ] freeze_cpu: 10.08 μs           [airflow.jobs.scheduler_job_runner.SchedulerJobRunner] loc=scheduler_job_runner.py:1367
2025-11-15T05:13:36.912517Z [info     ] unfreeze: 10.92 μs             [airflow.jobs.scheduler_job_runner.SchedulerJobRunner] loc=scheduler_job_runner.py:1374
2025-11-15T05:13:36.913268Z [info     ] unfreeze_cpu: 6.87 μs  
```



<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 -->

<!--
Thank you for contributing! Please make sure that your code changes
are covered with tests. And in case of new features or big changes
remember to adjust the documentation.

Feel free to ping committers for the review!

In case of an existing issue, reference it using one of the following:

closes: #ISSUE
related: #ISSUE

How to write a good git commit message:
http://chris.beams.io/posts/git-commit/
-->



<!-- Please keep an empty line above the dashes. -->
---
**^ Add meaningful description above**
Read the **[Pull Request Guidelines](https://github.com/apache/airflow/blob/main/contributing-docs/05_pull_requests.rst#pull-request-guidelines)** for more information.
In case of fundamental code changes, an Airflow Improvement Proposal ([AIP](https://cwiki.apache.org/confluence/display/AIRFLOW/Airflow+Improvement+Proposals)) is needed.
In case of a new dependency, check compliance with the [ASF 3rd Party License Policy](https://www.apache.org/legal/resolved.html#category-x).
In case of backwards incompatible changes please leave a note in a newsfragment file, named `{pr_number}.significant.rst` or `{issue_number}.significant.rst`, in [airflow-core/newsfragments](https://github.com/apache/airflow/tree/main/airflow-core/newsfragments).


## Changed Files Summary
- ✏️ **airflow-core/src/airflow/executors/local_executor.py** (modified)
  - +34 -3 lines
- ✏️ **airflow-core/tests/unit/executors/test_local_executor.py** (modified)
  - +24 -3 lines
- ✏️ **airflow-core/tests/unit/executors/test_local_executor_check_workers.py** (modified)
  - +2 -2 lines


## Repository Access
You have full access to the cloned repository at: `airflow/`

### Available Capabilities:
1. **File Operations:**
   - `read_file airflow/path/to/file.java` - Read any file in the repository
   - `list_dir airflow/src/` - List directory contents
   - `grep -r "pattern" airflow/` - Search through all files

2. **Git Operations:**
   - `run_terminal_cmd git log --oneline -10` - View recent commits
   - `run_terminal_cmd git show HEAD` - Show latest commit
   - `run_terminal_cmd git diff HEAD~1` - Show changes in latest commit

3. **Code Analysis:**
   - `run_terminal_cmd find airflow -name "*.java" | head -10` - Find Java files
   - `run_terminal_cmd wc -l airflow/path/to/file.java` - Count lines
   - `run_terminal_cmd grep -n "class.*Plugin" airflow/src/**/*.java` - Find classes

4. **Build/Test Operations:**
   - `run_terminal_cmd cd airflow && ./gradlew test` - Run tests (if applicable)
   - `run_terminal_cmd cd airflow && mvn compile` - Compile (if applicable)

## Ground Truth Questions
The system will use questions from `ground_truth_questions.md` to test your understanding of this PR.

## Instructions for iFlow
1. **Use the full repository**: You have access to the complete codebase, not just changed files
2. **Read actual files**: Use read_file to examine specific code when asked
3. **Run commands**: Use terminal commands for analysis, searching, and testing
4. **Make changes if requested**: You can modify files and run tests
5. **Provide detailed answers**: Base responses on actual code examination

Please acknowledge that you understand this PR context and your full repository access. Reply with: READY FOR COMPREHENSIVE ANALYSIS
