import sys
import os
import ray


# Add src to python path
sys.path.append(
    os.path.join(
        os.getcwd(),
        "src",
    )
)

from extraction.processor import ParallelExtractor
from src.configs import DEFAULT_MAIN_TOPIC, setup_logging, get_logger

# Setup production grade logging
setup_logging()
logger = get_logger(__name__)


def main():
    """
    Execute the paper extraction and relevance assessment process.

    Returns:
        None: Results are saved to the output directory.
    """
    # Option 1: Provide a list of PDF paths or URLs
    papers = [
        "docs/2508.05669v1.pdf"
    ]

    # Option 2: Provide a CSV path directly (already contains Title and Abstract)
    csv_path = "docs/paper_info.csv"

    # Set to True to use CSV, False to use the papers list
    USE_CSV = True

    # The topic to assess relevance against
    main_topic = DEFAULT_MAIN_TOPIC

    # Initialize the extractor with default settings from config
    extractor = ParallelExtractor()

    try:
        # Run extraction and assessment
        if USE_CSV:
            logger.info(f"Processing papers from CSV: {csv_path}")
            df = extractor.run(
                csv_path=csv_path,
                main_title=main_topic,
            )
        else:
            logger.info(f"Processing papers from PDF list: {papers}")
            df = extractor.run(
                paper_list=papers,
                main_title=main_topic,
            )

        # Handle output
        output_dir = "output"
        if not os.path.exists(
            output_dir,
        ):
            os.makedirs(
                output_dir,
            )

        output_path = os.path.join(
            output_dir,
            "extraction_results.csv",
        )
        df.to_csv(
            output_path,
            index=False,
        )

        logger.info(
            f"Successfully processed {len(df)} papers."
        )
        logger.info(
            f"Results saved to {output_path}"
        )

        # Display results summary (first 5 if long)
        logger.info("--- Results Summary ---")
        for i, (_, row) in enumerate(df.head(5).iterrows()):
            paper_title = row['title'][:100] + "..." if len(row['title']) > 100 else row['title']
            logger.info(f"Paper {i+1}: {paper_title}")
            logger.info(f"Relevant: {row['is_relevant']}")
            logger.info(f"Reasoning: {row['reasoning']}")

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)

    finally:
        if ray.is_initialized():
            ray.shutdown()


if __name__ == "__main__":
    main()
