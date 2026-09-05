"""
MCP (Model Context Protocol) routes.

Exposes the standard MCP endpoints:
  - GET  /mcp/tools         → list available tools
  - POST /mcp/tools/call    → execute a tool call

SECURITY:
  - Public tools (discovery) work without auth.
  - All financial and data-access tools require a valid JWT.
  - Identity is ALWAYS from the JWT, never from tool arguments.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from auth.dependencies import get_optional_user
from database import get_session
from mcp.handler import MCPError, handle_tool_call
from mcp.tools import TOOLS
from models.user import User

logger = logging.getLogger("agentsetu.mcp")

router = APIRouter()


class ToolCallRequest(BaseModel):
    """MCP tool call request body."""
    name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """MCP tool call response."""
    content: list[dict[str, Any]] = Field(..., description="Tool result content blocks")
    isError: bool = Field(default=False, description="Whether this is an error response")


@router.get("/tools", summary="List available MCP tools")
async def list_tools():
    """
    Return the list of MCP tool definitions.
    Each tool has: name, description, inputSchema.
    """
    return {"tools": TOOLS}


@router.post("/tools/call", summary="Execute an MCP tool call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Execute an MCP tool call.

    - Public tools (discover_products, get_merchant_arm, list_merchants) work
      without authentication.
    - All other tools require a valid JWT in the Authorization header.
    - The caller's identity is derived from the JWT, never from tool arguments.
    """
    try:
        result = await handle_tool_call(
            tool_name=request.name,
            arguments=request.arguments,
            session=session,
            user=current_user,
        )
        return ToolCallResponse(
            content=[{"type": "text", "text": _serialize(result)}],
            isError=False,
        )

    except MCPError as e:
        logger.warning("MCP tool error: %s — %s", request.name, str(e))
        status = 401 if e.code == "AUTH_REQUIRED" else (
            403 if e.code == "FORBIDDEN" else (
            404 if e.code == "NOT_FOUND" else (
            422 if e.code == "VALIDATION_ERROR" else 400
        )))
        raise HTTPException(
            status_code=status,
            detail={
                "error": {
                    "code": e.code,
                    "message": str(e),
                }
            },
        )

    except Exception:
        logger.exception("Unexpected MCP error: %s", request.name)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred processing the tool call.",
                }
            },
        )


def _serialize(result: Any) -> str:
    """Serialize a result dict to a JSON string for the MCP content block."""
    import json
    return json.dumps(result, default=str, ensure_ascii=False)
