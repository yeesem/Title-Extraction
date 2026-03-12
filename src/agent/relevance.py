import os
from typing import TypedDict, Literal, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from typing import Optional

from src.configs import (
    RELEVANCE_ASSESSMENT_SYSTEM_PROMPT,
    RELEVANCE_ASSESSMENT_HUMAN_PROMPT,
    DEFAULT_MODEL_PROVIDER,
    DEFAULT_MODEL_NAME,
    DEFAULT_TEMPERATURE,
)


# Load environment variables
load_dotenv()


class RelevanceResult(
    BaseModel,
):
    """
    Structured output for the relevance assessment.
    """

    is_relevant: bool = Field(
        description="Whether the paper is relevant to the main title.",
    )
    reasoning: Optional[str] = Field(
        default="",
        description="Concise reasoning for the relevance decision.",
    )


class AgentState(
    TypedDict,
):
    """
    State for the relevance assessment graph.
    """

    main_title: str
    paper_title: str
    paper_abstract: str
    is_relevant: bool
    reasoning: str


class RelevanceAgent:
    """
    Agent to assess the relevance of a paper to a given topic.
    """

    def __init__(
        self,
        model_provider: Literal["gemini", "openai"] = DEFAULT_MODEL_PROVIDER,
        model_name: str = DEFAULT_MODEL_NAME,
        temperature: float = DEFAULT_TEMPERATURE,
    ):
        """
        Initialize the RelevanceAgent with specified model settings.

        Args:
            model_provider (Literal["gemini", "openai"]): The LLM provider.
            model_name (str): The name of the model to use.
            temperature (float): The sampling temperature.
        """
        if model_provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                api_key = os.getenv("GEMINI_API_KEY")
            )
        elif model_provider == "openai":
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key = os.getenv("OPENAI_API_KEY")
            )
        else:
            raise ValueError(
                f"Unsupported model provider: {model_provider}",
            )

        self.structured_llm = self.llm.with_structured_output(
            RelevanceResult,
        )
        self.graph = self._build_graph()

    def _build_graph(
        self,
    ) -> StateGraph:
        """
        Construct the LangGraph workflow for relevance assessment.

        Returns:
            StateGraph: The compiled LangGraph object.
        """
        workflow = StateGraph(
            AgentState,
        )

        workflow.add_node(
            "assess_relevance",
            self.assess_relevance_node,
        )

        workflow.set_entry_point(
            "assess_relevance",
        )
        workflow.add_edge(
            "assess_relevance",
            END,
        )

        return workflow.compile()

    def assess_relevance_node(
        self,
        state: AgentState,
    ) -> dict:
        """
        Perform the relevance assessment using the LLM.

        Args:
            state (AgentState): The current state of the graph.

        Returns:
            dict: Updated state values.
        """
        system_prompt = RELEVANCE_ASSESSMENT_SYSTEM_PROMPT

        human_prompt = RELEVANCE_ASSESSMENT_HUMAN_PROMPT.format(
            main_title=state["main_title"],
            paper_title=state["paper_title"],
            paper_abstract=state["paper_abstract"],
        )

        messages = [
            SystemMessage(
                content=system_prompt,
            ),
            HumanMessage(
                content=human_prompt,
            ),
        ]

        result = self.structured_llm.invoke(
            messages,
        )

        return {
            "is_relevant": result.is_relevant,
            "reasoning": result.reasoning,
        }

    def run(
        self,
        main_title: str,
        paper_title: str,
        paper_abstract: str,
    ) -> dict:
        """
        Execute the relevance assessment workflow.

        Args:
            main_title (str): The main topic/title to compare against.
            paper_title (str): The title of the paper.
            paper_abstract (str): The abstract of the paper.

        Returns:
            dict: The final assessment result containing is_relevant and reasoning.
        """
        initial_state = {
            "main_title": main_title,
            "paper_title": paper_title,
            "paper_abstract": paper_abstract,
        }

        output = self.graph.invoke(
            initial_state,
        )

        return {
            "is_relevant": output["is_relevant"],
            "reasoning": output["reasoning"],
        }
