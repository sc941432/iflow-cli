# iFlow PR Benchmark System - Modular 3-Step Workflow

A complete, production-ready benchmark system for evaluating iFlow CLI's session management and repository analysis capabilities on GitHub Pull Requests.

## 🚀 Features

- **🔄 Modular 3-Step Workflow**: Clean separation of concerns for maximum control
- **🧠 Perfect Session Management**: Single persistent session with memory retention
- **📊 Comprehensive Evaluation**: Ground truth questions with quality metrics
- **⚡ Performance Optimized**: Shallow cloning, timeout handling, retry logic
- **🔧 File Access Fixed**: Handles macOS extended attributes and permissions
- **📈 Detailed Metrics**: Response quality, memory references, performance data
- **🎯 Production Ready**: Clean, robust, well-documented modular code

## 🎯 3-Step Workflow

### **Step 1: Repository Cloning & PR Data Preparation**
```bash
python3 enhanced_pr_fetcher.py --repo apache/airflow --pr 58365 --output-dir pr_workspace_apache
```

**What it does:**
- ✅ Clones the complete repository with shallow depth for performance
- ✅ Fetches PR branch and extracts diff
- ✅ Creates comprehensive PR context files
- ✅ **Fixes file permissions** (removes macOS extended attributes)
- ✅ Sets up ground truth questions template

### **Step 2: Dynamic Prompt Generation**
```bash
python3 dynamic_prompt_generator.py --workspace pr_workspace_apache --output generated_prompt.md
```

**What it does:**
- ✅ Analyzes PR workspace and metadata
- ✅ Generates optimized initial context prompt
- ✅ Adapts instructions for full repository exploration
- ✅ Creates file path mappings for iFlow

### **Step 3: Benchmark Execution with Session Management**
```bash
python3 iflow_pr_benchmark.py --workspace pr_workspace_apache --benchmark apache_pr_58365
```

**What it does:**
- ✅ Loads generated prompt and PR data
- ✅ Manages perfect iFlow session (single persistent session)
- ✅ Executes ground truth questions with memory tracking
- ✅ Generates comprehensive results and metrics

## 📁 Project Structure

```
cli-eval/
├── enhanced_pr_fetcher.py        # 🎯 Step 1: Repository & PR preparation
├── dynamic_prompt_generator.py   # 🎯 Step 2: Intelligent prompt generation
├── iflow_pr_benchmark.py         # 🎯 Step 3: Session management & evaluation
├── benchmarks/                   # 📊 Benchmark results
│   ├── apache_pr_58365/         # Example: Apache Airflow PR results
│   │   ├── ground_truth_questions.md
│   │   └── iflow_answers.md
│   └── sample_questions.md      # Template for ground truth questions
├── pr_workspace_apache/         # 📁 Cloned repository workspace
│   ├── airflow/                 # Complete Apache Airflow repository
│   ├── pr_58365_context.md     # PR description and context
│   ├── pr_58365.diff           # Actual code changes
│   ├── pr_58365_info.json      # PR metadata
│   ├── generated_prompt.md     # Generated initial prompt
│   └── ground_truth_questions.md
└── README.md                    # This documentation
```

## 🎯 Complete Usage Examples

### **Example 1: Apache Airflow PR**
```bash
# Step 1: Clone and prepare
python3 enhanced_pr_fetcher.py --repo apache/airflow --pr 58365 --output-dir pr_workspace_apache

# Step 2: Generate prompt
python3 dynamic_prompt_generator.py --workspace pr_workspace_apache --output pr_workspace_apache/generated_prompt.md

# Step 3: Run benchmark
python3 iflow_pr_benchmark.py --workspace pr_workspace_apache --benchmark apache_pr_58365
```

### **Example 2: Terraform PR**
```bash
# Step 1: Clone and prepare
python3 enhanced_pr_fetcher.py --repo hashicorp/terraform --pr 37923 --output-dir pr_workspace_terraform

# Step 2: Generate prompt
python3 dynamic_prompt_generator.py --workspace pr_workspace_terraform --output pr_workspace_terraform/generated_prompt.md

# Step 3: Run benchmark
python3 iflow_pr_benchmark.py --workspace pr_workspace_terraform --benchmark terraform_pr_37923
```

### **Example 3: Any GitHub PR**
```bash
# Step 1: Clone and prepare
python3 enhanced_pr_fetcher.py --repo owner/repo --pr 123 --output-dir pr_workspace_custom

# Step 2: Generate prompt
python3 dynamic_prompt_generator.py --workspace pr_workspace_custom --output pr_workspace_custom/generated_prompt.md

# Step 3: Run benchmark
python3 iflow_pr_benchmark.py --workspace pr_workspace_custom --benchmark custom_pr_123
```

## 📊 What Gets Evaluated

### Session Management
- ✅ **Single Persistent Session**: One session ID throughout entire benchmark
- ✅ **Memory Retention**: References to previous questions and context
- ✅ **Turn Tracking**: Proper session creation and resumption
- ✅ **Error Recovery**: Robust retry logic for reliability

### Repository Analysis
- ✅ **Full Repository Access**: Complete codebase exploration (8000+ files)
- ✅ **File Reading**: PR diffs, context, metadata, actual source code
- ✅ **Code Understanding**: Functions, classes, patterns, relationships
- ✅ **Technical Depth**: Architecture, performance, testing, documentation

### Response Quality
- 📈 **Detailed Responses**: Specific file paths, function names, code snippets
- 🎯 **Code Analysis**: Technical understanding beyond basic PR description
- 🧠 **Memory References**: Building on previous conversation context
- ⚡ **Performance**: Response times and processing efficiency

## 📈 Results & Metrics

Each benchmark produces comprehensive results:

### Session Summary
```
Session ID: session-1447fef6-6bab-43ae-a2c9-e26bad9459cd
Total Turns: 16
Total Questions: 15
Session Duration: 559.4s
Average Response Time: 41.9s
Memory References: 8
Detailed Responses: 10/15 (67%)
```

### Quality Breakdown
- 🎯 **Detailed Responses**: Comprehensive responses with technical specifics
- ⚠️ **Basic Responses**: Simple responses without depth
- ❌ **Unknown Responses**: "I don't know" responses

### Success Criteria
- **Excellent**: 80%+ detailed responses
- **Good**: 60-80% detailed responses  
- **Fair**: 40-60% detailed responses
- **Needs Improvement**: <40% detailed responses

## 🔧 Ground Truth Questions

Create custom evaluation questions in your workspace:

```markdown
# Ground Truth Questions

## Code Analysis
CA1 Q: What function is modified to apply gc.freeze?
CA2 Q: Which file contains the test for worker batching strategy?

## Technical Understanding  
TU1 Q: What method is used to prevent COW in LocalExecutor?
TU2 Q: How many files were changed in this PR?
```

See `benchmarks/sample_questions.md` for a complete template.

## 🎉 Success Story

**Proven Results:**
- ✅ **Perfect session management** (single persistent session)
- ✅ **Full repository access** (8000+ files accessible)
- ✅ **File access fixed** (extended attributes handled)
- ✅ **67% detailed responses** with technical depth
- ✅ **8 memory references** showing session continuity
- ✅ **Modular architecture** for maximum flexibility

## 🔧 Technical Implementation

### Key Features
- **Shallow Cloning**: `--depth 1 --single-branch` for performance
- **SSL Bypass**: `-c http.sslVerify=false` for corporate networks
- **Extended Attributes Fix**: `xattr -cr` for macOS compatibility
- **Session Management**: `-r session-id` for proper session resumption
- **Timeout Handling**: Configurable timeouts with retry logic
- **Modular Design**: Clean separation of concerns

### Architecture Benefits
- **Flexibility**: Run steps independently or modify individual components
- **Debugging**: Easy to isolate issues in specific steps
- **Reusability**: Reuse cloned repositories for multiple benchmarks
- **Maintainability**: Clean, focused code in each module
- **Performance**: Skip steps when data already exists

## 🚀 Requirements

- **Python 3.7+**
- **iFlow CLI** (installed and authenticated)
- **Git** (for repository cloning)
- **Internet Connection** (for GitHub access)

## 💡 Why 3-Step Workflow?

### **Advantages:**
1. **🔧 Flexibility**: Modify or skip individual steps as needed
2. **🐛 Debugging**: Easy to isolate and fix issues in specific components
3. **♻️ Reusability**: Reuse cloned repositories for multiple tests
4. **⚡ Performance**: Skip expensive cloning when repository already exists
5. **🧹 Maintainability**: Clean, focused code that's easy to understand and modify

### **Workflow Control:**
- **Step 1**: Only run when you need fresh repository data
- **Step 2**: Customize prompts for different evaluation scenarios
- **Step 3**: Run multiple benchmarks on the same prepared data

## 📞 Support

This is a complete, production-ready modular system that provides maximum flexibility and control over the benchmarking process. Each step can be run independently, modified, or extended as needed for your specific evaluation requirements.