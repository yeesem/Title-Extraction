"""
Configuration settings for the application.
"""

# LLM Settings
DEFAULT_MODEL_PROVIDER = "gemini"
DEFAULT_MODEL_NAME = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.0

# Extraction Settings
DEFAULT_GROBID_URL = "http://localhost:8070/api/processHeaderDocument"
DEFAULT_MAX_PAGES = 3

# Systematic Review Context
DEFAULT_MAIN_TOPIC = (
    "Probiotics and Synbiotics as Adjuncts to Anticancer Therapy in Colorectal Cancer: "
    "A Systematic Review of Preclinical and Clinical Evidence"
)
