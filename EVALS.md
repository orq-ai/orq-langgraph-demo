# Toyota Assistant Evaluation Pipeline


The evaluation pipeline consists of:

- **Dataset Creation**: Upload test cases to orq.ai
- **Evaluation Execution**: Run the assistant against test cases and measure performance using [evaluatorq](https://docs.orq.ai/docs/experiments/api)
- **Metrics**: We focus on tool selection accuracy

![Evaluating Tool Calling](media/tool-calling-evals.png)

## Quick Start

```bash
# Upload evaluation dataset to orq.ai
make evals-upload-dataset

# Run evaluation pipeline
make evals-run

# Show help for evaluation scripts
make evals-help
```

## Prerequisites

### 1. Install Dependencies

Make sure you have the eval dependencies installed.

```bash
uv sync --group eval
```

### 2. Set Up orq.ai

1. **Create orq.ai Account**: Sign up at [https://my.orq.ai/](https://my.orq.ai/)
2. **Get API Key**: Go to Settings > API Keys > Create API Key
3. **Set Environment Variable**:

```bash
# Add to your .env file
ORQ_API_KEY=your_api_key_here
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
|-- create_eval_dataset.py                # Upload dataset to orq.ai
|-- run_evaluation_pipeline.py            # Run evaluation pipeline
`-- datasets/
    `-- toyota_assistant_tool_calling_evals.jsonl  # Test cases dataset
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

## Step 1: Register the Evaluation Dataset on orq.ai

Upload the test cases to orq.ai:

```bash
# Using Makefile (recommended)
make evals-upload-dataset
```

**Expected Output:**
```
Uploading Toyota Assistant Dataset to orq.ai
Loading evals/datasets/toyota_assistant_tool_calling_evals.jsonl...
Loaded 15 examples
Creating dataset: toyota-assistant-tool-calling-evals
Uploading 15 datapoints...
Success! Dataset ID: 01ARZ3NDEKTSV4RRFFQ69G5FAV
View at: https://my.orq.ai/datasets/01ARZ3NDEKTSV4RRFFQ69G5FAV
```

## Step 2: Run Evaluation Pipeline

Execute the evaluation against your assistant:

```bash
# Run with local file (default)
make evals-run

# Or run against an orq.ai dataset by ID
python evals/run_evaluation_pipeline.py <dataset_id>
```

**What this does:**

- Loads your Toyota assistant graph from `src/assistant/`
- Runs each test case through the assistant via an evaluatorq `@job`
- Extracts tool calls and responses
- Evaluates checking if the agent called the correct tools
- Syncs results to orq.ai for analysis (when `ORQ_API_KEY` is set)

**Expected Output:**

```
Toyota Assistant Evaluation Pipeline (orq.ai)
==================================================
Loaded 15 datapoints from local file
Starting evaluation...
...
Evaluation completed!
Results available in orq.ai Studio: https://my.orq.ai/experiments
```

## Evaluation Metrics

### 1. Tool Accuracy Scorer

Measures how accurately the assistant selects the expected tools:

- **Perfect Match (1.0)**: All expected tools called, no extras
- **Subset Match (1.0)**: All expected tools called, some extras allowed
- **Partial Match (0.0-0.9)**: Some expected tools missing
- **No Match (0.0)**: No expected tools called

### 2. Category Accuracy Scorer

Measures performance by question type category. These are the available categories:

- **SQL-only queries**: Database query accuracy
- **Document-only queries**: Document search accuracy
- **Mixed queries**: Combined SQL + document accuracy

## Viewing Results

### orq.ai Studio

1. **Go to**: [https://my.orq.ai/](https://my.orq.ai/)
2. **Navigate to**: Experiments
3. **View**: Experiment results, metrics, and individual test cases

### Key Metrics to Monitor

- **Overall Tool Accuracy**: Percentage of correct tool selections
- **Category Performance**: How well each query type performs
- **Response Quality**: Content relevance and completeness. (Work in Progress) We need ground-truth answers and feedback to start computing response quality

----
Author: Arian Pasquali
