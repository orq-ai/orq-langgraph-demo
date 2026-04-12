# Hybrid Data Agent Evaluation Pipeline


The evaluation pipeline consists of:

- **Dataset Creation**: Upload test cases to orq.ai
- **Evaluation Execution**: Run the assistant against test cases and measure performance using [evaluatorq](https://docs.orq.ai/docs/experiments/api)
- **Metrics**: We focus on tool selection accuracy

![Evaluating Tool Calling](media/tool-calling-evals.png)

## Quick Start

```bash
# One-time bootstrap: creates the dataset (+ KB + system prompt) on orq.ai.
# Safe to re-run — it reuses existing entities by key.
make setup-workspace

# Run evaluation pipeline (against the local JSONL file by default)
make evals-run

# Show help for evaluation scripts
make evals-help
```

> `make setup-workspace` is the recommended way to create the dataset.
> `make evals-upload-dataset` still exists and runs only the dataset step —
> use it if you've deleted the dataset in the Studio and want to re-upload.

## Prerequisites

### 1. Install Dependencies

Make sure you have the eval dependencies installed.

```bash
uv sync --group eval
```

### 2. Set Up orq.ai

1. **Create orq.ai Account**: Sign up at [https://my.orq.ai/](https://my.orq.ai/)
2. **Get API Key**: Go to Settings > API Keys > Create API Key
3. **Set Environment Variables**:

```bash
# Add to your .env file
ORQ_API_KEY=your_api_key_here
ORQ_PROJECT_NAME=langgraph-demo   # or any name you prefer
```

4. **Bootstrap the workspace** (creates the dataset, KB, and system prompt):

```bash
make setup-workspace
```

## Dataset Structure

The evaluation dataset (`evals/datasets/tool_calling_evals.jsonl`) contains 15 test cases in JSONL format:

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
    `-- tool_calling_evals.jsonl                  # Test cases dataset
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

The recommended way is to run `make setup-workspace` (shown in Prerequisites)
which creates the dataset alongside the KB and system prompt. If you only
want to upload the dataset — e.g. after deleting it in the Studio — you can
use the standalone command:

```bash
make evals-upload-dataset
```

**Expected Output:**
```
Uploading Hybrid Data Agent Dataset to orq.ai
Loading evals/datasets/tool_calling_evals.jsonl...
Loaded 15 examples
Creating dataset: hybrid-data-agent-tool-calling-evals
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

- Loads the Hybrid Data Agent graph from `src/assistant/`
- Runs each test case through the assistant via an evaluatorq `@job`
- Extracts tool calls and responses
- Evaluates whether the agent called the correct tools (PASS/FAIL per scorer)
- Syncs results to orq.ai for analysis under the project defined by `ORQ_PROJECT_NAME`

**Expected Output:**

```
Hybrid Data Agent Evaluation Pipeline (orq.ai)
==================================================
Loaded 15 datapoints from local file
Starting evaluation...
...
Evaluation completed!
Results available in orq.ai Studio: https://my.orq.ai/experiments
```

## Evaluation Metrics

Each scorer returns `EvaluationResult(value=<bool>, pass_=<bool>, explanation=...)`.
The boolean `value` makes the orq.ai Studio color-code experiment cells
green/red, and `pass_` lets evaluatorq exit non-zero on any failure for
CI/CD gating.

### 1. Tool Accuracy Scorer (local)

- **True** (green): All expected tools were called (additional tools are allowed)
- **False** (red): One or more expected tools are missing

Defined in `evals/run_evaluation_pipeline.py` — stays local because it needs
the agent's `tools_called` output field which isn't part of the standard
orq.ai Python evaluator log surface.

### 2. Source Citations (orq.ai Python evaluator)

- **True** (green): Response contains at least one `https?://` URL
- **False** (red): No source URL

Registered as a workspace Python evaluator `source-citations-present`
(created by `make setup-workspace`). Invoked via `orq_scorers.py`.

### 3. Response Grounding (orq.ai LLM evaluator)

- **True** (green): All claims in the response are supported by the retrieved docs
- **False** (red): The response makes claims not present in the retrievals

Registered as a workspace LLM evaluator `response-grounding`. This scorer
needs the retrievals to work, so the job captures `state.retrieved_documents`
and passes them to the evaluator via `orq_scorers.py`.

### 4. Hallucination Check (orq.ai LLM evaluator)

- **True** (green): Response contains no contradictions or unsupported claims vs retrievals
- **False** (red): At least one contradiction or fabrication found

Registered as a workspace LLM evaluator `hallucination-check`. Complements
grounding (grounding = "everything is supported", hallucination = "nothing is
contradicted"). Same retrievals plumbing as the grounding scorer.

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
