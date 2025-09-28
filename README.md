# Toyota/Lexus RAG Assistant

A RAG assistant that combines vehicle sales data and documents to answer automotive questions. Built with LangGraph, ChromaDB, and SQLite. Ready for deployment with Docker. 
It also counts with [Evals](EVALS.md) with a detailed Evaluation Pipeline focused on testing tool calling using LangSmith.

## What it does

This assistant can:

- **Context-Aware Responses**: Handles only Toyota-specific questions. Refuses unrelated questions.
- **Query Sales Data**: Answers questions about vehicle sales using SQL database.
- **Search Documents**: Applied semantic search to find relevant information in manuals, contracts, and warranty documents.
- **Tool Orchestration**: Answers complex questions by combining sql and semantic questions using Agentic tool callings.

You can run it locally or you can access the deployed version at [https://rag-reference-demo.onrender.com/](https://rag-reference-demo.onrender.com/).

## What is included in the knowledge base?
- **Sales Data** (Accessible via SQLite): Vehicle sales by model, country, and date
- **Documents** (Accessible via ChromaDB): Toyota manuals, contracts, and warranty policies


### You can try these questions

**Using structured sales data:**
- "What were the RAV4 sales in Germany in 2024?"
- "Show me the top countries by vehicle sales"

**Using unstructured documents:**
- "What is the Toyota warranty coverage?"
- "Where is the tire repair kit in the UX?"

**Hybrid:**
- "Compare RAV4 sales and summarize its warranty"


## How it works

The assistant uses a multi-step LangGraph workflow with routing:

1. **Safety Check**: OpenAI Moderation API filters harmful content
2. **Query Analysis**: LLM classifies the question type and intent
3. **Context-Aware Routing**: Routes to appropriate response path:
   - **Toyota-specific**: If it detected that question is related to Toyota it uses tools (predefined SQL queries and semantic search) to answer the question
   - **Needs clarification**: Asks for more specific information
   - **Off-topic**: Politely redirects to Toyota/Lexus topics
4. **Agentic Tool Loop**: For Toyota questions, iterates between model and tools until complete

See bellow the agent architecture.

![Agent Architecture](media/agent_architecture.png)

For a detailed technical overview of the system architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).


## Demo

### Basic Demo

Demo showing the agent using semantic search to find relevant documents.

![Basic Demo](media/demo_optimized.gif)

### Sales Data Analysis Demo

Demo showing the agent using SQL capabilities to query the structured database.

![Sales Data Analysis Demo](media/demo_sales_data_2_optimized.gif)



## Quick Start

### Prerequisites

- **Option A (Docker)**: Docker and Docker Compose
- **Option B (Local)**: Python 3.11+

OpenAI API key is mandatory.

### Option A: Docker Deployment (Recommended)

1. **Create environment file**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

2. **Run with Docker Compose**
```bash
docker-compose up --build
```

3. **Or run with Docker directly**
```bash
# Build the image
docker build -f Dockerfile -t toyota-assistant .

# Run with environment file
docker run -p 8000:8000 --env-file .env toyota-assistant
```

Visit `http://localhost:8000` to chat with the assistant.

### Option B: Local Development

1. **Install dependencies**
```bash
uv sync
```

2. **Set environment variable**
```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

3. **Setup databases**
```bash
# This method will create the SQLite with the structured sales data and also ingest the pdfs to a ChromaDB
make setup-db
```

4. **Run the UI**
```bash
# Web interface. Runs chainglit UI locally
make run
```
Visit `http://localhost:8000` to chat with the assistant.

![Toyota RAG Assistant UI](media/run_ui.png)


5. **Run the agent using LangGraph Studio**

```bash
# Opens LangGraph Studio UI running our Agent
make dev
```

LangGraph Studio should automatically open in your browser.

![LangGraph Studio Development](media/studio_dev.png)


## Document Ingestion

### Local ChromaDB (Default)

Ingest PDF documents for semantic retrieval using ChromaDB.
This takes some time to parse the big documents.

```bash
# Ingest PDFs from ./docs directory
make setup-embeddings-db
```

### ChromaDB Cloud (Optional)

To use ChromaDB Cloud instead of local storage you need to specify your Chroma API keys:

1. **Set up ChromaDB Cloud credentials** in your `.env` file:
   ```bash
   CHROMA_API_KEY=your-chroma-api-key
   CHROMA_TENANT_ID=your-tenant-id
   CHROMA_DATABASE_NAME=your-database-name
   ```

2. **Run ingestion** (same command, will detect cloud config if available):

```bash
make setup-embeddings-db
```

The system automatically detects whether to use local or cloud ChromaDB based on the presence of `CHROMA_API_KEY`.

## Tests, Continuous Integration and Evals

### Running Unit tests

In order to run local unit tests you have a make action already defined.  Just run:

```bash
# Run unit tests
make tests
```

### CI/CD Pipeline using Github Actions
- **Automated Testing**: Runs on every push/PR
- **Multi-Python Support**: Tests on Python 3.11 and 3.12
- **Code Quality**: Ruff linting
- **Security**: Bandit security scanning

### Evals: Integrated Evaluation Pipeline using Langsmith

Running full evaluation pipeline and testing realistic [sample questions](resources/converstation_starters.csv).

```bash
# Command to run evaluation pipeline. Make sure you setup correctly Langsmith (see EVALS.md)
make evals-run
```

**Evaluation Features:**
- **Tool Selection Accuracy**: Measures correct tool usage
- **Category Performance**: SQL-only, document-only, mixed queries
- **LangSmith Integration**: Results tracking and analysis
- **15 Test Cases**: Comprehensive evaluation dataset (5 expecting SQL queries, 5 expecting semantic search, and 5 mixed queries using both)

For detailed info on how to run evaluation pipeline, see [EVALS.md](EVALS.md).

![Evaluating Tool Calling](media/tool-calling-evals.png)

## Troubleshooting

### Local Development Issues

**Database issues:**
```bash
make setup-db  # Create databases (sqlite and chromadb)
```
---

## Improvements and Next Steps
- **Contextual Retrieval**: Better document chunking with improved summaries
- **Reranking**: Semantic reranking to improve document retrieval relevance
- **User Feedback**: Collect user feedback in the UI (thumbs up/down)
- **Query Suggestions**: Provide intelligent follow-up question recommendations
