"""
ProgramGarden - AI Agent Tool Interface

Functional tools collection for AI agents/chatbots
"""

from typing import Optional, List, Dict, Any
from programgarden.tools.registry_tools import (
    list_node_types,
    get_node_schema,
    list_plugins,
    get_plugin_schema,
    list_categories,
)
from programgarden.tools.credential_tools import (
    list_credentials,
    create_credential,
    delete_credential,
)
from programgarden.tools.definition_tools import (
    create_workflow,
    validate_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
    delete_workflow,
)
from programgarden.tools.job_tools import (
    start_job,
    get_job,
    list_jobs,
    pause_job,
    resume_job,
    cancel_job,
    get_job_state,
    emergency_close_all,
    cancel_all_orders,
    restore_job,
    has_checkpoint,
    get_checkpoint_info,
)
from programgarden.tools.event_tools import (
    get_events,
    get_job_summary,
    analyze_performance,
)
from programgarden.tools.sqlite_tools import (
    list_database_files,
    delete_database_file,
    list_tables,
    list_columns,
    create_table,
    api_list_databases,
    api_delete_database,
    api_list_tables,
    api_list_columns,
    api_create_table,
)

__all__ = [
    # Registry
    "list_node_types",
    "get_node_schema",
    "list_plugins",
    "get_plugin_schema",
    "list_categories",
    # Credential
    "list_credentials",
    "create_credential",
    "delete_credential",
    # Definition
    "create_workflow",
    "validate_workflow",
    "get_workflow",
    "list_workflows",
    "update_workflow",
    "delete_workflow",
    # Job
    "start_job",
    "get_job",
    "list_jobs",
    "pause_job",
    "resume_job",
    "cancel_job",
    "get_job_state",
    "emergency_close_all",
    "cancel_all_orders",
    "restore_job",
    "has_checkpoint",
    "get_checkpoint_info",
    # Event
    "get_events",
    "get_job_summary",
    "analyze_performance",
    # SQLite
    "list_database_files",
    "delete_database_file",
    "list_tables",
    "list_columns",
    "create_table",
    "api_list_databases",
    "api_delete_database",
    "api_list_tables",
    "api_list_columns",
    "api_create_table",
]
