# Growing the eval dataset from production traces

One of the strongest reasons to use orq.ai is the **production → eval loop**:
every real user query captured as a trace is a potential eval datapoint.
This turns your eval dataset from a static snapshot into a living record
of what the agent actually handles in production.

This repo ships a script that closes that loop:

```bash
# 1. Export traces from orq.ai (Studio UI → Traces → Export, or MCP tool)
#    Save to a file like `recent-traces.json`

# 2. Dry-run: see what would be added
make evals-grow-from-traces FILE=recent-traces.json

# 3. Append for real (writes to evals/datasets/tool_calling_evals.jsonl)
uv run python scripts/grow_eval_dataset.py --from-file recent-traces.json --apply

# 4. Re-run the evals against the grown dataset
make evals-run
```

## What the script does

For each trace, the script:

1. **Extracts the first user message** from `input.messages` or similar
   (handles string and multi-part content formats).
2. **Collects tool names** from spans whose type contains `tool`
   (matches our LangGraph `search_documents`, `get_sales_by_model`, etc.).
3. **Classifies the category** based on which tools were called:
   - `sql_only` if all tools are in the SQL whitelist
   - `document_only` if all tools are in the doc whitelist
   - `mixed` if both
   - `unknown` → skipped
4. **Deduplicates** against existing datapoints by SHA-256 of the question text.
5. **Appends** unique new datapoints to `evals/datasets/tool_calling_evals.jsonl`.

## Getting the traces JSON

### Option A: Studio UI

1. Navigate to your project (`langgraph-demo`) → **Traces** tab
2. Filter by entity key (`hybrid-data-agent` or `Hybrid Data Agent`)
3. Filter by date range (e.g. last 24 hours)
4. Select the traces to include
5. Click **Export** → **JSON**
6. Save to a file in your repo (add to `.gitignore` if sensitive)

### Option B: orq MCP server (in Claude Code)

If you have the `orq` MCP server connected in Claude Code, use the
`list_traces` tool:

```
list_traces({
  entity_key: "hybrid-data-agent",
  project_id: "<your-project-id>",
  start_time_after: "2026-04-01T00:00:00Z",
  limit: 50
})
```

Save the response body to a JSON file and pass it to the script.

### Option C: Direct REST (currently not publicly exposed)

At the time of writing, `/v2/traces` isn't available on the public orq.ai
REST API. When it becomes available, the script can be extended with a
`--from-api` flag that queries it directly.

## Suggested workflow

Run the growth script **weekly**, in this order:

1. `make evals-run` — establish the baseline on the current dataset
2. Export recent production traces
3. `make evals-grow-from-traces FILE=...` (dry run) — review proposed additions
4. `make evals-grow-from-traces FILE=... --apply`
5. `make evals-run` — see if tool-accuracy dropped on the new cases
6. If it dropped: investigate, fix the agent, re-run until green
7. Commit the updated JSONL and open a PR — CI will block any regression

This is the core **production → eval → improvement** loop that makes
orq.ai's observability valuable for teams, not just individual developers.
