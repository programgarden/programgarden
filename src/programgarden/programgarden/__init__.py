"""
ProgramGarden - Node-based DSL Execution Engine

5-Layer Architecture:
    1. Registry Layer - Node/Plugin metadata
    2. Credential Layer - Authentication/Security
    3. Definition Layer - Workflow definitions
    4. Job Layer - Execution instances
    5. Event Layer - Event history
"""

from programgarden.resolver import WorkflowResolver, ValidationResult
from programgarden.executor import WorkflowExecutor
from programgarden.context import ExecutionContext
from programgarden.client import ProgramGarden
from programgarden.tools import (
    # Registry Tools
    list_node_types,
    get_node_schema,
    list_plugins,
    get_plugin_schema,
    list_categories,
    # Credential Tools
    list_credentials,
    create_credential,
    delete_credential,
    # Definition Tools
    create_workflow,
    validate_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
    delete_workflow,
    # Job Tools
    start_job,
    get_job,
    list_jobs,
    pause_job,
    resume_job,
    cancel_job,
    get_job_state,
    emergency_close_all,
    cancel_all_orders,
    # Event Tools
    get_events,
    get_job_summary,
    analyze_performance,
)

# Auto-load community plugins on import
try:
    from programgarden_community import register_all_plugins
    register_all_plugins()
except ImportError:
    # Community package not installed
    pass

__version__ = "2.0.0"
__all__ = [
    # Core
    "ProgramGarden",
    "WorkflowResolver",
    "WorkflowExecutor",
    "ExecutionContext",
    "ValidationResult",
    # Registry Tools
    "list_node_types",
    "get_node_schema",
    "list_plugins",
    "get_plugin_schema",
    "list_categories",
    # Credential Tools
    "list_credentials",
    "create_credential",
    "delete_credential",
    # Definition Tools
    "create_workflow",
    "validate_workflow",
    "get_workflow",
    "list_workflows",
    "update_workflow",
    "delete_workflow",
    # Job Tools
    "start_job",
    "get_job",
    "list_jobs",
    "pause_job",
    "resume_job",
    "cancel_job",
    "get_job_state",
    "emergency_close_all",
    "cancel_all_orders",
    # Event Tools
    "get_events",
    "get_job_summary",
    "analyze_performance",
]
