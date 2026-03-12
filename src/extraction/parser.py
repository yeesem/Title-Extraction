import io
import os
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader, PdfWriter
from typing import Dict, Optional
from src.configs import DEFAULT_GROBID_URL, DEFAULT_MAX_PAGES


class PDFParser:
    """
    A class to handle fetching, trimming, and metadata extraction from PDF files.
    """

    def __init__(
        self,
        grobid_url: str = DEFAULT_GROBID_URL,
        max_pages: int = DEFAULT_MAX_PAGES,
    ):
        """
        Initialize the PDFParser with configuration.

        Args:
            grobid_url (str): The URL of the GROBID service endpoint.
            max_pages (int): The maximum number of pages to process.
        """
        self.grobid_url = grobid_url
        self.max_pages = max_pages

    def fetch_pdf_bytes(
        self,
        path_or_url: str,
    ) -> Optional[bytes]:
        """
        Fetch PDF content from a local file path or a URL.

        Args:
            path_or_url (str): The local file path or the URL of the PDF.

        Returns:
            Optional[bytes]: The PDF content in bytes, or None if the fetch fails.
        """
        try:
            if path_or_url.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                response = requests.get(
                    path_or_url,
                    timeout=30,
                )
                response.raise_for_status()
                return response.content
            elif os.path.exists(
                path_or_url,
            ):
                with open(
                    path_or_url,
                    "rb",
                ) as f:
                    return f.read()
            return None
        except (
            requests.RequestException,
            OSError,
        ):
            return None

    def trim_pdf(
        self,
        pdf_bytes: bytes,
    ) -> Optional[bytes]:
        """
        Trim a PDF to the configured maximum number of pages.

        Args:
            pdf_bytes (bytes): The original PDF content in bytes.

        Returns:
            Optional[bytes]: The trimmed PDF content in bytes, or None if trimming fails.
        """
        try:
            reader = PdfReader(
                io.BytesIO(
                    pdf_bytes,
                )
            )
            writer = PdfWriter()

            num_pages = len(
                reader.pages,
            )
            for i in range(
                min(
                    num_pages,
                    self.max_pages,
                )
            ):
                writer.add_page(
                    reader.pages[i],
                )

            output = io.BytesIO()
            writer.write(
                output,
            )
            return output.getvalue()
        except Exception:
            return None

    def extract_metadata(
        self,
        pdf_bytes: bytes,
    ) -> Dict[str, str]:
        """
        Send a PDF to GROBID and parse the TEI XML for Title and Abstract.

        Args:
            pdf_bytes (bytes): The PDF content in bytes.

        Returns:
            Dict[str, str]: A dictionary containing the 'title' and 'abstract'.
        """
        try:
            files = {
                'input': (
                    'paper.pdf',
                    pdf_bytes,
                )
            }
            headers = {
                'Accept': 'application/xml',
            }
            response = requests.post(
                self.grobid_url,
                files=files,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                'xml',
            )

            # Extract title
            title_tag = soup.find(
                'titleStmt',
            )
            title = "Unknown Title"
            if title_tag and title_tag.find(
                'title',
            ):
                title = title_tag.find(
                    'title',
                ).get_text(
                    strip=True,
                )

            # Extract abstract
            abstract_tag = soup.find(
                'abstract',
            )
            abstract = "No Abstract Found"
            if abstract_tag:
                abstract = abstract_tag.get_text(
                    separator=' ',
                    strip=True,
                )

            return {
                "title": title,
                "abstract": abstract,
            }
        except Exception as e:
            return {
                "title": f"Error: {str(e)}",
                "abstract": "N/A",
            }
