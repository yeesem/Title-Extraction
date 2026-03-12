# Abstract Analysis

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Ray](https://img.shields.io/badge/Distributed-Ray-orange.svg)](https://ray.io/)
[![LangChain](https://img.shields.io/badge/Orchestration-LangChain-green.svg)](https://langchain.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

**Abstract Analysis** is a production-grade, high-throughput pipeline designed to automate the screening phase of systematic reviews. By leveraging **Ray** for distributed computing and **Large Language Models (LLMs)** like Google Gemini and OpenAI, it extracts metadata from research papers (PDFs) and assesses their relevance to specific research criteria with human-level reasoning.

In modern research, screening thousands of abstracts is a significant bottleneck. This tool parallelizes the extraction and decision-making process, allowing researchers to filter massive datasets in minutes rather than weeks.

## Key Features

- 🚀 **Distributed Parallelism:** Powered by [Ray](https://ray.io/), the system scales across local CPU cores or multi-node clusters to process hundreds of papers simultaneously.
- 🧠 **LLM-Driven Relevance:** Uses state-of-the-art models (Gemini 1.5/2.0, GPT-4o) to evaluate papers against complex inclusion/exclusion criteria, providing structured reasoning for every "Relevant/Not Relevant" decision.
- 📄 **Smart PDF Parsing:** Integrated with **GROBID** and **PyPDF** to reliably extract Titles and Abstracts from academic layouts, even with complex multi-column formats.
- 📊 **Multi-Source Ingest:** Seamlessly process local PDF files, remote URLs, or existing CSV datasets containing pre-extracted text.
- 📋 **Systematic Reporting:** Outputs a comprehensive CSV report including source metadata, relevance flags, and the LLM's justification.
- ⚙️ **Configurable Prompts:** Easily adapt the system for different research topics by updating the systematic review context in the configuration.

## Architecture

The system follows a modular, task-based architecture optimized for scalability:

1.  **Orchestration (`ParallelExtractor`):** Manages the lifecycle of the extraction job, initializing the Ray runtime and dispatching tasks.
2.  **Extraction Task (`PDFParser`):** Fetches PDF bytes, trims documents to relevant pages (to save tokens), and parses structured metadata using GROBID.
3.  **Agentic Assessment (`RelevanceAgent`):** A LangChain-powered agent that constructs prompts, interacts with the LLM, and enforces structured output via Pydantic.
4.  **Data Layer:** Uses Pandas for efficient batch processing and final report generation.

## Repository Structure

```text
Abstract_Analysis/
├── main.py                 # Application entry point & example usage
├── pyproject.toml          # Dependency and project metadata
├── src/
│   ├── agent/              # LLM logic, LangGraph/LangChain agents
│   │   ├── relevance.py    # Core relevance assessment agent
│   │   └── __init__.py
│   ├── extraction/         # PDF processing & Ray task definitions
│   │   ├── parser.py       # PDF fetching and GROBID integration
│   │   ├── processor.py    # Ray orchestrator logic
│   │   └── __init__.py
│   └── configs/            # System-wide configuration
│       ├── settings.py     # Global constants and defaults
│       ├── prompts.py      # LLM system and human prompt templates
│       └── __init__.py
├── docs/                   # Input directory (PDFs, paper_info.csv)
└── output/                 # Generated results (extraction_results.csv)
```

## Installation

### Prerequisites

- **Python 3.12+**
- **uv** (Recommended: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **GROBID** (Optional: Required for advanced PDF header parsing)

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/Abstract_Analysis.git
    cd Abstract_Analysis
    ```

2.  **Install dependencies:**
    Using `uv`:
    ```bash
    uv sync
    ```
    Or using `pip`:
    ```bash
    pip install .
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory:
    ```bash
    GOOGLE_API_KEY=your_gemini_api_key
    OPENAI_API_KEY=your_openai_api_key
    GROBID_URL=http://localhost:8070/api/processHeaderDocument
    ```

## Configuration

Global settings are managed in `src/configs/settings.py`. Key parameters include:

- `DEFAULT_MODEL_PROVIDER`: Set to `"gemini"` or `"openai"`.
- `DEFAULT_MAX_PAGES`: Number of pages to read from the start of a PDF (default: 3).
- `DEFAULT_MAIN_TOPIC`: The research question or topic title used to guide the LLM.

Modify `src/configs/prompts.py` to refine the **Inclusion/Exclusion criteria** for your specific systematic review.

## Usage

### Running the Pipeline

You can run the extraction pipeline using the provided `main.py`. It supports two modes:

#### 1. Processing a CSV of Abstracts
If you already have a CSV with `Title` and `Abstract` columns:
```python
from extraction.processor import ParallelExtractor

extractor = ParallelExtractor()
df = extractor.run(
    csv_path="docs/paper_info.csv",
    main_title="Your Research Topic"
)
df.to_csv("output/results.csv", index=False)
```

#### 2. Processing Raw PDFs (Local or URL)
```python
from extraction.processor import ParallelExtractor

papers = ["docs/study1.pdf", "https://arxiv.org/pdf/2508.05669v1.pdf"]
extractor = ParallelExtractor()
df = extractor.run(
    paper_list=papers,
    main_title="Your Research Topic"
)
```

### CLI Execution
```bash
uv run main.py
```

## API / Interface

The `ParallelExtractor` class is the primary interface for integration:

| Parameter    | Type        | Description                                              |
| :----------- | :---------- | :------------------------------------------------------- |
| `paper_list` | `List[str]` | List of file paths or URLs to PDF documents.             |
| `csv_path`   | `str`       | Path to a CSV containing 'Title' and 'Abstract' columns. |
| `main_title` | `str`       | The research topic/question for relevance assessment.    |

**Returns:** A `pandas.DataFrame` containing `title`, `abstract`, `is_relevant`, and `reasoning`.

## Development Setup

### Running GROBID (Docker)
For optimal PDF metadata extraction, run GROBID in the background:
```bash
docker run -t --rm -p 8070:8070 grobid/grobid:0.8.0
```

### Linting & Formatting
```bash
# Run Ruff for linting and formatting
uv run ruff check .
uv run ruff format .
```

## Testing

Tests are located in the `tests/` directory (if applicable). Run them using `pytest`:
```bash
uv run pytest
```

## Deployment

The system is designed to run in distributed environments. For production deployments:

1.  **Ray Cluster:** Deploy a Ray head node and multiple worker nodes.
2.  **Environment Sync:** Ensure all nodes have the same environment variables and `PYTHONPATH` configured.
3.  **Containerization:** Use the provided `docker-compose.yaml` (if configured) to orchestrate Ray and GROBID together.

## Performance Considerations

- **Ray Scaling:** By default, Ray uses all available CPU cores. For large-scale cloud deployments, use `ray.init(address='auto')` to connect to an existing cluster.
- **LLM Rate Limits:** The system processes papers in parallel. Ensure your API tier (Gemini/OpenAI) supports the concurrency level (RPM/TPM).
- **PDF Trimming:** `PDFParser` trims PDFs to the first 3 pages by default to minimize data transfer and parsing time.

## Security Considerations

- **API Keys:** Never commit `.env` files or hardcode API keys. Use environment variables.
- **Data Privacy:** When using LLM providers, be aware that paper abstracts are sent to external APIs (Google/OpenAI) for processing. Ensure compliance with your institution's data privacy policies.

## Troubleshooting

- **Ray Initialization Errors:** Ensure no other Ray processes are hanging on the same ports. Run `ray stop` to clear state.
- **GROBID Connection Refused:** Verify the `GROBID_URL` in `.env` matches the port exposed by your Docker container (default: 8070).
- **LLM Authentication:** Check that your API keys are valid and have sufficient quota for the model specified in `settings.py`.

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## License

Distributed under the MIT License.