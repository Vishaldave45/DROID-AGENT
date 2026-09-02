#!/usr/bin/env python3
"""CLI and Subprocess bridge to dispatch tools via NexForge Droid ToolRegistry."""

import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.tools import get_default_tool_registry
from app.security.base import SecurityContext, DefaultPolicyEngine


def main():
    if len(sys.argv) < 2:
        # Default: list all tools
        registry = get_default_tool_registry(workspace_root=BASE_DIR)
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
                "requires_permission": getattr(t, "requires_permission", False),
            }
            for t in registry.list_tools()
        ]
        print(json.dumps(tools))
        return

    tool_name = sys.argv[1]
    args_json = sys.argv[2] if len(sys.argv) > 2 else "{}"
    workspace = sys.argv[3] if len(sys.argv) > 3 else BASE_DIR

    try:
        kwargs = json.loads(args_json)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Invalid arguments JSON: {str(e)}"}))
        return

    registry = get_default_tool_registry(workspace_root=workspace)
    result = registry.dispatch(tool_name, kwargs)
    print(json.dumps(result.to_dict()))


if __name__ == "__main__":
    main()
