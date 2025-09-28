# Toyota Assistant Evaluation Pipeline


The evaluation pipeline consists of:
- **Dataset Creation**: Upload test cases to LangSmith
- **Evaluation Execution**: Run the assistant against test cases and measure performance
- **Metrics**: We focus on tool selection accuracy

## Quick Start

```bash
# Upload evaluation dataset to LangSmith
make evals-upload-dataset

# Run evaluation pipeline
make evals-run

# Show help for evaluation scripts
make evals-help
```

## Prerequisites

### 1. Install Dependencies

Make sure you have Langsmith dependency installed.

```bash
uv add langsmith
```

### 2. Set Up LangSmith

1. **Create LangSmith Account**: Sign up at [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Get API Key**: Go to Settings → API Keys → Create API Key
3. **Set Environment Variable**:

```bash
# Add to your .env file
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=Toyota-Assistant-Evaluation
```

## Dataset Structure

The evaluation dataset (`evals/datasets/toyota_assistant_tool_calling_evals.jsonl`) contains 15 test cases in JSONL format:

### Test Case Categories

- **SQL-only queries** (5 cases): Questions requiring database queries
- **Document-only queries** (5 cases): Questions requiring document search
- **Mixed queries** (5 cases): Questions requiring both SQL and document search

## Directory Structure

```
evals/
├── create_eval_dataset_on_langsmith.py    # Upload dataset to LangSmith
├── run_evaluation_pipeline.py             # Run evaluation pipeline
└── datasets/
    └── toyota_assistant_tool_calling_evals.jsonl  # Test cases dataset
```

### Example Test Case

```json
{
  "metadata": {
    "id": "sql_001",
    "category": "sql_only",
    "expected_tools": ["get_sales_by_model"]
  },
  "inputs": {
    "category": "sql_only",
    "question": "Show me RAV4 sales in Germany for 2024",
    "expected_tools": ["get_sales_by_model"]
  },
  "outputs": {
    "response": "Based on our sales data, here's how RAV4 performed...",
    "tools_called": ["get_sales_by_model"],
    "execution_status": "success"
  }
}
```

## Step 1: Register the Evaluation Dataset on Langsmith

Upload the test cases to LangSmith:

```bash
# Using Makefile (recommended)
make evals-upload-dataset

# Show help
make evals-help
```

**Expected Output:**
```
Uploading Toyota Assistant Dataset to LangSmith
📂 Loading evals/datasets/toyota_assistant_tool_calling_evals.jsonl...
Loaded 15 examples
Checking if dataset 'tool-calling-eval-dataset' already exists...
Creating new dataset: tool-calling-eval-dataset
Created new dataset with ID: 12345678-1234-1234-1234-123456789abc
Uploading 15 examples...
Success! Dataset ID: 12345678-1234-1234-1234-123456789abc
Uploaded 15 examples to dataset 'tool-calling-eval-dataset'
View at: https://smith.langchain.com/datasets/12345678-1234-1234-1234-123456789abc
```

## Step 2: Run Evaluation Pipeline

Execute the evaluation against your assistant:

```bash
# Using Makefile
make evals-run
```

**What this does:**
- Loads your Toyota assistant graph from `src/assistant/`
- Runs each test case through the assistant
- Extracts tool calls and responses
- Evaluates checking if the agent called the correct tools
- Saves results to LangSmith for analysis

**Expected Output:**
```
Toyota Assistant Evaluation Pipeline
====================================
Dataset: toyota-assistant-tool-calling-evaluation
Examples: 15
Started: 2024-01-15 14:30:00
Active Evaluators: 2 (tool_accuracy_evaluator, category_accuracy_evaluator)
Starting evaluation...
Evaluation completed in 45.2 seconds
Evaluation completed successfully!
Results available in LangSmith UI
```

## Evaluation Metrics

### 1. Tool Accuracy Evaluator

Measures how accurately the assistant selects the expected tools:

- **Perfect Match (1.0)**: All expected tools called, no extras
- **Subset Match (1.0)**: All expected tools called, some extras allowed
- **Partial Match (0.0-0.9)**: Some expected tools missing
- **No Match (0.0)**: No expected tools called

### 2. Category Accuracy Evaluator

Measures performance by question type category. These are the available categories:

- **SQL-only queries**: Database query accuracy
- **Document-only queries**: Document search accuracy
- **Mixed queries**: Combined SQL + document accuracy

## Viewing Results

### LangSmith UI

1. **Go to**: [https://smith.langchain.com/](https://smith.langchain.com/)
2. **Navigate to**: Projects → Toyota-Assistant-Evaluation
3. **View**: Experiment results, metrics, and individual test cases

### Key Metrics to Monitor

- **Overall Tool Accuracy**: Percentage of correct tool selections
- **Category Performance**: How well each query type performs
- **Response Quality**: Content relevance and completeness. (Work in Progress) We need ground-truth answers and feedback to start computing response quality
