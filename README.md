# AI Agent Orchestration System

A comprehensive orchestrated AI agent system in Python that simulates a small enterprise workflow. This project demonstrates modular agent design, intelligent orchestration, ML integration, and robust error handling.

## 🚀 Overview

The system features 5 specialized agents coordinated by a central Orchestrator that manages task dependencies, handles failures, and supports conditional workflow branching.

### Core Agents
- **DataFetcher**: Retrieves real-time weather and news data (with mock fallback).
- **Analyzer**: Uses a pre-trained **Transformer model** (DistilBERT) for sentiment analysis and keyword extraction.
- **DecisionMaker**: Applies business rules and thresholds to determine priority and actions.
- **Notifier**: Generates multi-format reports (JSON, Text, HTML) and executive summaries.
- **Supervisor**: Validates outputs, resolves conflicts, and provides QA approval.

## 🛠️ Installation

1. **Clone the repository** (or navigate to the project folder).
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Download ML Models** (Optional - will auto-download on first run):
   The `Analyzer` agent uses Hugging Face's `transformers`. It will download the `distilbert-base-uncased-finetuned-sst-2-english` model (~260MB).

## 🔑 Configuration

Edit `config.yaml` to configure API keys, agent parameters, and workflow definitions.
- `OPENWEATHER_API_KEY`: For real weather data.
- `NEWS_API_KEY`: For real news articles.
- *Fallbacks*: The system will use high-quality mock data if API keys are missing.

## 💻 Usage

Run the system using the `main.py` entry point.

### 1. Run Complete Workflow
Run the full enterprise analysis workflow:
```bash
python main.py run --workflow enterprise_analysis
```

### 2. List Workflows
See all available workflow definitions:
```bash
python main.py list-workflows
```

### 3. Test Individual Agent
Run a specific agent in standalone mode for debugging:
```bash
python main.py test --agent DataFetcher
```

### 4. Check Agent Status
View execution stats and status of all agents:
```bash
python main.py status
```

## 📂 Project Structure

- `agents/`: Individual agent implementations and base classes.
- `orchestrator/`: Workflow management, scheduling, and state persistence.
- `utils/`: Logging, configuration, and custom exceptions.
- `cli/`: Command-line interface logic.
- `data/`: Sample inputs and generated outputs/logs.

## 🧠 Features

- **ML-Powered Analysis**: Sentiment analysis using pre-trained DistilBERT.
- **Intelligent Orchestration**: DAG-based dependency resolution and topological sorting.
- **Fault Tolerance**: Automatic retries with exponential backoff and error recovery.
- **Conditional Branching**: Workflows adjust behavior based on data insights (e.g., negative sentiment triggers alerts).
- **Comprehensive Logging**: Colored console logs and persistent file rotation.
- **State Management**: Workflow states are serialized to JSON for tracking and potential resumption.

## 📝 Demo Output

Generated reports can be found in `data/outputs/`. Check the generated HTML reports for a polished, visual summary of the agent activities.
