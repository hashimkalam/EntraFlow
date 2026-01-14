# EntraFlow: Enterprise Agent Orchestration System

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Framework: LangChain](https://img.shields.io/badge/Framework-LangChain-green.svg)](https://www.langchain.com/)

**EntraFlow** is a powerful, production-ready AI agent orchestration system designed to simulate and automate complex enterprise workflows. It leverages modular agent architecture, intelligent DAG-based orchestration, and seamless integration with Large Language Models (LLMs) to provide deep business insights and automated decision-making.

---

## 🚀 Overview

EntraFlow coordinates a suite of specialized agents through a central Orchestrator. Each agent is responsible for a specific domain—from data ingestion and machine learning analysis to strategic decision-making and quality assurance.

### The Agent Ecosystem
- **📡 DataFetcher**: Ingests real-time data from external APIs (OpenWeather, NewsAPI). Features robust caching and mock data fallbacks for development.
- **🔍 Analyzer**: Conducts multi-layer analysis using **Transformer models** (DistilBERT) for sentiment analysis and **LangChain-powered LLMs** for deep semantic insights.
- **⚖️ DecisionMaker**: Applies complex business logic and priority rules. It uses LLMs to provide **Strategic AI Advisory**, translating data analysis into actionable corporate strategy.
- **📢 Notifier**: The reporting engine. Generates stakeholder-ready reports in **HTML**, **JSON**, and **Markdown/Text** formats, including executive summaries and alert logs.
- **🛡️ Supervisor**: The QA layer. Validates agent outputs against schemas, resolves data conflicts, and ensures final reports meet enterprise quality standards.

---

## 🧠 Key Features

- **Intelligent Orchestration**: Uses a Directed Acyclic Graph (DAG) for dependency management and topological sorting.
- **LLM-Agnostic Core**: Native support for **OpenAI**, **HuggingFace**, and **Ollama** via LangChain integration.
- **Fault-Tolerant Engine**: Automatic retries with exponential backoff, state persistence for workflow resumption, and graceful degradation.
- **Extensible Configuration**: Entire workflows, agent thresholds, and API settings are managed via a centralized `config.yaml`.
- **Comprehensive Logging**: Multi-tier logging with console colorization and persistent storage for audit trails.
- **Enterprise-Grade Analysis**: Combines classical NLP (keywords) with modern Deep Learning (Transformers) and GenAI (LLMs).

---

## 🛠️ Installation

### 1. Clone & Setup
```bash
git clone https://github.com/hashimkalam/EntraFlow.git
cd EntraFlow
```

### 2. Environment Configuration
Create a `.env` file or set environment variables:
```bash
# API Keys (Optional - fallbacks provided)
export OPENWEATHER_API_KEY="your_key"
export NEWS_API_KEY="your_key"
export OPENAI_API_KEY="your_key"  # If using OpenAI provider
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

*Note: On first run, the system will automatically download the DistilBERT model (~260MB) for local analysis if not present.*

---

## 🔑 Configuration

EntraFlow is highly configurable via `config.yaml`. Key sections include:

- **api**: Set your preferred LLM provider (`huggingface`, `openai`, `ollama`) and model name.
- **agents**: Tune confidence thresholds, priority rules, and output formats.
- **workflows**: Define custom sequences of agent execution.

---

## 💻 Usage

EntraFlow provides a powerful CLI for managing your agent workforce.

### Run a Workflow
Execute the full enterprise analysis pipeline:
```bash
python main.py run --workflow enterprise_analysis
```

### Manage Workflows
```bash
# List all defined workflows
python main.py list-workflows

# Check status of previous runs
python main.py status
```

### Debugging & Testing
```bash
# Test a specific agent in isolation
python main.py test --agent Analyzer
```

---

## 📂 Project Structure

```text
EntraFlow/
├── agents/             # Modular agent implementations
│   ├── base_agent.py   # Base class with core lifecycle logic
│   ├── analyzer.py     # ML & LLM analysis logic
│   └── ...             # Other specialized agents
├── orchestrator/       # The "Brain" of the system
│   ├── orchestrator.py # DAG execution and scheduling
│   └── workflow.py     # Workflow definition parsing
├── utils/              # Shared utilities
│   ├── llm.py          # LangChain & LLM provider management
│   └── logger.py       # Enterprise logging system
├── cli/                # Terminal interface logic
├── data/               # Persistent states and generated reports
└── config.yaml         # Centralized system settings
```

---

## 📝 Output & Reporting

EntraFlow doesn't just process data; it communicates results. Check `data/outputs/` after a run for:
- **HTML Reports**: Polished, visual summaries for executives.
- **JSON Data**: Raw, structured output for downstream integration.
- **Alert Logs**: Immediate notification of critical business triggers.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
