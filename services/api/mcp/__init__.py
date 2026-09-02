"""
MCP (Model Context Protocol) adapter for AgentSetu.

Exposes AgentSetu capabilities as MCP tools so external AI agents
can discover merchants, evaluate policy, and orchestrate purchases
through a standardised tool-call interface.

SECURITY INVARIANT:
  - The MCP layer is a thin adapter. It NEVER bypasses the policy engine.
  - Payment authorisation still requires: policy ALLOW + capability + auth.
  - Identity is derived from the JWT in the MCP request, never from tool args.
"""
