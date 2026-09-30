"""bmad-langgraph: BMAD-METHOD's analyst/PM/architect/UX/dev pipeline, ported
from Claude-Code skill prompts to a LangGraph StateGraph.

See ``graph.build_graph`` for the compiled graph and ``cli.main`` for the
interactive driver.
"""

from .graph import build_graph

__all__ = ["build_graph"]
__version__ = "0.1.0"
