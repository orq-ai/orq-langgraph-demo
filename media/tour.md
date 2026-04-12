# Tour GIF storyboard

The README references `media/tour.gif` — a 15–20 second screen recording that
tells the whole platform story in one loop. This file is a storyboard for when
you (or I) record it.

## Target: 15–20 seconds, <5 MB, silent (no audio track)

## Sequence

1. **Terminal** (1s) — `make run` → Chainlit opens on localhost:8000
2. **Chainlit UI** (3s) — type "What is the Toyota warranty for Europe?" → press Enter
3. **Streaming response** (3s) — agent streams the answer with PDF citations
4. **Switch to browser tab** (1s) — orq.ai Studio → Traces tab
5. **Click the newest trace** (2s) — tree view expands showing:
   ```
   Hybrid Data Agent
   ├── guard_input
   ├── analyze_and_route_query
   ├── call_model
   ├── tools (search_documents)
   └── call_model (final response)
   ```
6. **Click the final ChatOpenAI span** (2s) — right panel shows messages, tokens, cost
7. **Switch to Experiments tab** (1s) — click most recent `hybrid-data-agent-prompt-ab`
8. **Hover a PASS row** (1s) — tooltip shows the scorer name and explanation

## Recording tips

- Use a terminal width of 100 columns and font size ≥16pt so text is legible at GIF resolution
- Use Kap (macOS) or Peek (Linux) to record; export at 8–12 fps to keep file size down
- Trim to ≤20 seconds total, otherwise the file gets too big for GitHub's inline rendering limit
- Add a 1-second pause at the end so the loop reset isn't jarring

## Once recorded

1. Save as `media/tour.gif`
2. Delete this `media/tour.md` file
3. Verify the README renders it correctly (it's referenced just under the title)
