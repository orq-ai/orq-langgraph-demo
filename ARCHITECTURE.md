# Architecture

The Hybrid Data Agent is a reference implementation of a conversational AI agent that combines structured data (SQLite sales records) with unstructured documents (manuals, contracts, warranty policies) in a single LangGraph workflow. Built with LangGraph for agent orchestration, the orq.ai Knowledge Base for managed vector storage, and SQLite for structured data, it demonstrates end-to-end patterns for building agents that reason across multiple data sources, managed through the orq.ai platform. Here I document the key architecture decisions.

## Architecture Overview Diagram

![RAG Architecture](media/rag-architecture.png)

## Key Architectural Components

### 1. **Agent Orchestration Layer (LangGraph)**

- **Purpose**: Manages conversation flow, safety, and tool coordination
- **Components**:
  - Safety guardrails (OpenAI Moderation)
  - Query classification router
  - Tool-calling agent with GPT-4.1-mini routed through the orq.ai AI Router
  - State management for conversation context
  - System prompt fetched from orq.ai Prompts at startup (with local fallback)

### 2. **Data Access Layer**

- **Structured Data**: SQLite with star schema (fact tables + dimensions)
  - `fact_sales`, `dim_model`, `dim_country`, `dim_ordertype`
- **Unstructured Data**: orq.ai Knowledge Base (managed embeddings + vector search)
  - PDF documents, manuals, warranties, contracts

### 3. **Tool Layer**

- **Individual SQL Tools**: 9 approved queries. Provides SQL injection protection by preventing direct SQL engine exposure to the LLM.
All necessary SQL operations are accessible through predefined SQL statements exposed as individual tools.

This approach prioritizes safety over flexibility. In case we see new data needs we need to review the available queries and provide new tools if necessary.

Here is the list of predefined queries and their use:

  - `get_sales_by_model`: Model-specific sales data with country/year filters
  - `get_sales_by_country`: Country-specific sales analysis
  - `get_sales_by_region`: Regional sales comparison and analysis
  - `get_sales_trends`: Monthly sales trends and patterns
  - `get_top_performing_models`: Best-selling models by sales volume
  - `get_powertrain_analysis`: Sales performance by powertrain type
  - `get_top_countries_by_sales`: Country rankings by sales performance
  - `get_powertrain_sales_trends`: Powertrain-specific monthly trends
  - `compare_models_by_brand`: Brand-specific model comparisons

- **Vector Search Tools**: Semantic search across documents. PDFs are chunked locally (PyPDF + RecursiveCharacterTextSplitter) and ingested into an orq.ai Knowledge Base, which handles embeddings and vector search.

### 4. **User Interface Layer**

- **Framework**: Chainlit web application
- **Features**: Streaming responses, PDF display, conversation starters, reference links
- **Deployment**: Docker containerization for easy local development and cloud deployment with CI/CD

## Data Flow Architecture

Overview of how data flows through the agent to answer questions.

![Data Flow Architecture](media/rag-architecture-data-diagram.png)

## Architecture Trade-offs Analysis

### **Latency**

**Current Approach:**

- **Sequential Processing**: Safety > Router > Model > Tools > Response
- **Streaming**: Real-time token streaming to UI
- **Quality vs Speed Trade-off**: The current system implementation is more focused on quality of the answer and safety than speed

**Targets and Key Performance Metric:**

- **First-Token-Latency**: ~1 second to start streaming response
- **Total Response Time**: ~1.5-4.5s per interaction
- **Design Philosophy**: *"First make it run, make it better and make it faster"*

**Latency Breakdown:**
- Safety check: ~100-200ms
- Query classification: ~300-500ms
- Tool execution: ~100-400ms
- Response generation: ~1-5s (streaming depending on the size of the answer)

### Security

### Security Architecture Decisions and its layers

|  **Layer** |  **Implementation Status** |  **Protection Against** |
|-----------|---------------------------|------------------------|
| **Input Filtering** | OpenAI Moderation API | Harmful content |
| **Query Routing** | LLM-based topic classification | Off-topic queries, conversation hijacking |
| **Query Templates** | Parameterized query whitelisting | Unauthorized database access |
| **Parameter Validation** | Type-safe parameter checking | Invalid parameters, data corruption |
| **Database Access** | Read-only SQLite connections | Data modification |

#### Layer 1: Input Validation & Content Filtering

- **OpenAI Moderation API**: First line of defense against harmful content
- **Real-time Processing**: Blocks policy violations before query processing
- **Coverage**: Hate speech, violence, self-harm, sexual content, harassment

#### Layer 2: Query Classification & Routing

- **LLM-based Topic Detection**: Identifies query intent and topic relevance
- **Off-topic Protection**: Prevents conversation hijacking and prompt injection
- **Route-specific Security**: Different security measures per query type

#### Layer 3: SQL Security

1. **Predefined SQL queries as Tools**: SQL is not exposed to the LLM, the LLM only knows the tool functions.
3. **Template Execution**: Parameterized queries with predefined templates only

#### Layer 4: Database Security

- **Read-only Access**: Read mode prevents data modification


**Security Trade-offs:**

- **Input Guardrails**: OpenAI Moderation API filters all incoming messages before processing. It is a simple solution given the time constraints.
- **Database Security**: Individual SQL tools with predefined parameterized queries.
- **Off-topic Protection**: Off-topic conversations are a risky vector for Prompt or SQL injection and jailbreaking. We block that with a router node.

**Document Serving Security:**

- **Current**: By default Chainlit serves the files under the public directory as static files. Good for a prototype but not for production environment.
- **Recommendation**: Ideally this would be served with something like blob storage or S3 bucket with proper access control and permissions.

## Observability

All LangGraph executions are traced to the orq.ai Studio via OpenTelemetry
(see [`src/assistant/tracing.py`](src/assistant/tracing.py)). The Control
Tower auto-registers agents, tools, and models from the spans, and every
trace captures the full graph tree — nodes, LLM calls, tool executions, and
Knowledge Base retrievals — with token usage and cost per step.

The trace, timeline, and thread views are shown in [README.md#observability](README.md#observability).

## Evaluation & Testing

### **orq.ai Evaluation (evaluatorq)**

- **Dataset Management**: Ground truth datasets with 15 test questions covering SQL-only, document-only, and mixed scenarios
- **Categories Tested**:
  - SQL-only (5 questions): Model sales, top performers, regional analysis, trends, rankings
  - Document-only (5 questions): Warranty info, maintenance procedures, safety features, repair guides
  - Mixed (5 questions): Combined SQL + document responses
- **Evaluation Metrics**: Tool selection accuracy is evaluated. It is prepared to evaluate response quality as well, but not released yet due to time constraints and lack of appropriate ground-truth.
- **Test Coverage**: 100% perfect tool matches in ground truth dataset with real SQL responses

- **See details** at [Evals](EVALS.md).

## Other considerations

### Cost Optimization

- Implement response caching for common queries
- Use smaller models for classification tasks. We are using GPT-4.1-mini, but we could test with even smaller models for specific classification tasks.
- **Model Routing Strategy**: TODO — enable [orq.ai AI Router auto-routing](https://router.orq.ai/) so LLM calls are dispatched to the cheapest model that still meets the quality bar, with built-in fallbacks and retries. We already route through `https://api.orq.ai/v2/router` (see [`src/assistant/utils.py`](src/assistant/utils.py#L102)), so this is a configuration change in the Router, not a code change.
- **Batch Processing**: Consider using OpenAI Batch API for even lower costs during document ingestion
- Better concurrency management for document ingestion pipeline

### Document Relevancy and Performance

- **Current Approach**: Due to latency and for the sake of simplicity we are showing them [all retrieved documents] here to demonstrate the feature
- **Production Enhancement**: Ideally we would have a relevancy assessment or reranker and filter out those documents that are not relevant
- **Trade-off**: Showing all retrieved documents vs. implementing reranking (adds latency but improves precision)

----

**Quality versus Latency Trade-off**:

The current system implementation is more focused on quality of the answer and safety than speed. I consider that the KPI First-Token-Latency is around 1s, meaing it takes 1 second to start streaming the answer to the user. The trade-off is good ideal for customer iterations and improvements based on actual real usage. Following the principle: First make it run, make it better and make it faster.


----
Author: Arian Pasquali
