# Architecture

The Toyota RAG Assistant is a PoC for a conversational AI system that combines structured vehicle sales data with unstructured documents to provide comprehensive Toyota/Lexus vehicle information using best practices for this type of project. Built with LangGraph for agent orchestration, ChromaDB for vector storage, and SQLite for structured data, it demonstrates simple but advanced RAG architecture patterns and is ready for deployment with Docker. Here I document some architecture decisions.

## Architecture Overview Diagram

![RAG Architecture](media/rag-architecture.png)

## Key Architectural Components

### 1. **Agent Orchestration Layer (LangGraph)**

- **Purpose**: Manages conversation flow, safety, and tool coordination
- **Components**:
  - Safety guardrails (OpenAI Moderation)
  - Query classification router
  - Tool-calling agent with GPT-4.1-mini
  - State management for conversation context

### 2. **Data Access Layer**

- **Structured Data**: SQLite with star schema (fact tables + dimensions)
  - `fact_sales`, `dim_model`, `dim_country`, `dim_ordertype`
- **Unstructured Data**: ChromaDB vector store with OpenAI embeddings
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

- **Vector Search Tools**: Semantic search across documents. Available pdfs were ingested and persisted using ChromaDB.

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

### **Cost**

**Current Cost Structure:**

```
Per 1000 User Interactions (estimated):

OpenAI API Costs: ~$1.35 per 1000 questions

Infrastructure:
|-- Compute [Render](https://render.com/): ~$7-25/month
|-- Storage [ChromaDB](https://www.trychroma.com/): ~$0-10/month
`-- Total Infrastructure: ~$7-35/month

The goal was to focus on DX for quick and easy CI/CD instead of cost. 
```

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
- **Model Routing Strategy**: Consider using [Cast.ai](https://cast.ai/) - a proxy tool that routes to the cheapest model available without compromising quality
- **Batch Processing**: Consider using OpenAI Batch API for even lower costs during document ingestion
- Better concurrency management for document ingestion pipeline

### More Security

- Add authentication
- Implement rate limiting per user or IP

### Billing Strategy

- **Usage-Based Billing**: Consider using [Lago](https://www.getlago.com/) - a usage-based billing and metering cloud solution
- **Flexible Pricing Models**: Setup billing by message, tokens, packages, etc.
- **Focus Benefits**: This way we can focus on the system and the billing experimentation until we find the billing model we are happy with

### Document Relevancy and Performance

- **Current Approach**: Due to latency and for the sake of simplicity we are showing them [all retrieved documents] here to demonstrate the feature
- **Production Enhancement**: Ideally we would have a relevancy assessment or reranker and filter out those documents that are not relevant
- **Trade-off**: Showing all retrieved documents vs. implementing reranking (adds latency but improves precision)

----

**Quality versus Latency Trade-off**:

The current system implementation is more focused on quality of the answer and safety than speed. I consider that the KPI First-Token-Latency is around 1s, meaing it takes 1 second to start streaming the answer to the user. The trade-off is good ideal for customer iterations and improvements based on actual real usage. Following the principle: First make it run, make it better and make it faster.


----
Author: Arian Pasquali
