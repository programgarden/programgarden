"""
ProgramGarden Core - Group Node

Subflow node:
- GroupNode: Reusable subflow
"""

from typing import Optional, List, Literal, Dict, Any
from pydantic import Field

from programgarden_core.nodes.base import (
    BaseNode,
    NodeCategory,
    InputPort,
    OutputPort,
)


class GroupNode(BaseNode):
    """
    Reusable subflow node

    Groups multiple nodes into a reusable subflow.
    Exchanges data with external nodes via $input.*, $output.* interfaces.
    Supports unlimited nesting.
    """

    type: Literal["GroupNode"] = "GroupNode"
    category: NodeCategory = NodeCategory.GROUP
    description: str = "i18n:nodes.GroupNode.description"

    # GroupNode specific config
    workflow_id: Optional[str] = Field(
        default=None,
        description="Sub-workflow ID to reference (for external definition)",
    )
    inline_nodes: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Inline node definitions (for direct definition within group)",
    )
    inline_edges: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Inline edge definitions (for direct definition within group)",
    )
    input_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Input mapping ($input.* → internal node)",
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="Output mapping (internal node → $output.*)",
    )

    _inputs: List[InputPort] = [
        InputPort(
            name="$input",
            type="any",
            description="Group input (dynamic, defined by input_mapping)",
            multiple=True,
        ),
    ]
    _outputs: List[OutputPort] = [
        OutputPort(
            name="$output",
            type="any",
            description="Group output (dynamic, defined by output_mapping)",
        ),
    ]
