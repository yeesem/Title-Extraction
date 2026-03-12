import os
import ray
import pandas as pd
from typing import List, Dict, Optional, Literal, Union
from extraction.parser import PDFParser
from agent.relevance import RelevanceAgent
from src.configs import (
    DEFAULT_MODEL_PROVIDER,
    DEFAULT_GROBID_URL,
    DEFAULT_MAX_PAGES,
    get_logger,
)

logger = get_logger(__name__)


@ray.remote
def process_pdf_task(
    path_or_url: str,
    grobid_url: str,
    max_pages: int,
    main_title: Optional[str] = None,
    model_provider: Literal["gemini", "openai"] = DEFAULT_MODEL_PROVIDER,
) -> Dict[str, str]:
    """
    Ray task to process a single paper and assess its relevance.

    Args:
        path_or_url (str): The local path or URL of the PDF.
        grobid_url (str): The URL of the GROBID service.
        max_pages (int): The maximum number of pages to process.
        main_title (Optional[str]): The topic to assess relevance against.
        model_provider (Literal["gemini", "openai"]): The LLM provider.

    Returns:
        Dict[str, str]: Extraction and assessment results.
    """
    logger.info(f"Processing PDF: {os.path.basename(path_or_url)}")
    parser = PDFParser(
        grobid_url=grobid_url,
        max_pages=max_pages,
    )

    file_name = os.path.basename(
        path_or_url,
    )

    pdf_bytes = parser.fetch_pdf_bytes(
        path_or_url=path_or_url,
    )
    if not pdf_bytes:
        return {
            "source": path_or_url,
            "file_name": file_name,
            "title": "Error: Could not fetch PDF",
            "abstract": "N/A",
            "is_relevant": "False",
            "reasoning": "Could not fetch PDF",
        }

    trimmed_bytes = parser.trim_pdf(
        pdf_bytes=pdf_bytes,
    )
    if not trimmed_bytes:
        return {
            "source": path_or_url,
            "file_name": file_name,
            "title": "Error: Could not trim PDF",
            "abstract": "N/A",
            "is_relevant": "False",
            "reasoning": "Could not trim PDF",
        }

    result = parser.extract_metadata(
        pdf_bytes=trimmed_bytes,
    )
    result["source"] = path_or_url
    result["file_name"] = file_name

    # Perform relevance assessment if main_title is provided
    if main_title:
        agent = RelevanceAgent(
            model_provider=model_provider,
        )
        assessment = agent.run(
            main_title=main_title,
            paper_title=result["title"],
            paper_abstract=result["abstract"],
        )
        result["is_relevant"] = str(
            assessment["is_relevant"],
        )
        result["reasoning"] = assessment["reasoning"]
    else:
        result["is_relevant"] = "N/A"
        result["reasoning"] = "No main title provided"

    return result


@ray.remote
def process_csv_row_task(
    row_data: Dict[str, str],
    main_title: Optional[str] = None,
    model_provider: Literal["gemini", "openai"] = DEFAULT_MODEL_PROVIDER,
) -> Dict[str, str]:
    """
    Ray task to process a single CSV row and assess its relevance.

    Args:
        row_data (Dict[str, str]): Data from a single CSV row.
        main_title (Optional[str]): The topic to assess relevance against.
        model_provider (Literal["gemini", "openai"]): The LLM provider.

    Returns:
        Dict[str, str]: Assessment results.
    """
    title = row_data.get("Title", row_data.get("title", "Unknown Title"))
    abstract = row_data.get("Abstract", row_data.get("abstract", "N/A"))

    logger.info(f"Assessing relevance for: {str(title)[:50]}...")

    result = {
        "source": "CSV Row",
        "file_name": "N/A",
        "title": title,
        "abstract": abstract,
    }

    if main_title:
        agent = RelevanceAgent(
            model_provider=model_provider,
        )
        assessment = agent.run(
            main_title=main_title,
            paper_title=title,
            paper_abstract=abstract,
        )
        result["is_relevant"] = str(assessment["is_relevant"])
        result["reasoning"] = assessment["reasoning"]
    else:
        result["is_relevant"] = "N/A"
        result["reasoning"] = "No main title provided"

    return result


class ParallelExtractor:
    """
    Orchestrator for parallel PDF extraction and assessment using Ray.
    """

    def __init__(
        self,
        grobid_url: str = DEFAULT_GROBID_URL,
        max_pages: int = DEFAULT_MAX_PAGES,
        model_provider: Literal["gemini", "openai"] = DEFAULT_MODEL_PROVIDER,
    ):
        """
        Initialize the extractor with processing configuration.

        Args:
            grobid_url (str): The URL of the GROBID service.
            max_pages (int): The maximum number of pages to process per paper.
            model_provider (Literal["gemini", "openai"]): The LLM provider.
        """
        self.grobid_url = grobid_url
        self.max_pages = max_pages
        self.model_provider = model_provider

    def run(
        self,
        paper_list: Optional[List[str]] = None,
        csv_path: Optional[str] = None,
        main_title: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Execute parallel extraction and assessment on a list of papers or a CSV file.

        Args:
            paper_list (Optional[List[str]]): List of PDF paths or URLs.
            csv_path (Optional[str]): Path to a CSV file containing 'Title' and 'Abstract'.
            main_title (Optional[str]): Topic to assess relevance against.

        Returns:
            pd.DataFrame: Results of the extraction and assessment.
        """
        if not paper_list and not csv_path:
            return pd.DataFrame()

        if not ray.is_initialized():
            ray.init(
                ignore_reinit_error=True,
                runtime_env={
                    "working_dir": ".",
                    "env_vars": {"PYTHONPATH": "src"},
                },
            )

        futures = []
        if csv_path:
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"CSV file not found: {csv_path}")
            df = pd.read_csv(csv_path)
            # Ensure required columns exist
            cols = [c.lower() for c in df.columns]
            if "title" not in cols or "abstract" not in cols:
                # Try to map case-insensitively
                mapping = {}
                for c in df.columns:
                    if c.lower() == "title":
                        mapping[c] = "Title"
                    if c.lower() == "abstract":
                        mapping[c] = "Abstract"
                if len(mapping) < 2:
                    raise ValueError("CSV must contain 'Title' and 'Abstract' columns.")

            futures = [
                process_csv_row_task.remote(
                    row_data=row.to_dict(),
                    main_title=main_title,
                    model_provider=self.model_provider,
                )
                for _, row in df.iterrows()
            ]
        elif paper_list:
            futures = [
                process_pdf_task.remote(
                    path_or_url=p,
                    grobid_url=self.grobid_url,
                    max_pages=self.max_pages,
                    main_title=main_title,
                    model_provider=self.model_provider,
                )
                for p in paper_list
            ]

        results = ray.get(
            futures,
        )

        return pd.DataFrame(
            results,
        )
