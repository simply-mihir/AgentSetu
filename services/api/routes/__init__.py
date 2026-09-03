from fastapi import APIRouter
from routes import auth, merchants, discovery, transactions, payments, audit, webhooks, mcp, analytics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(merchants.router, prefix="/merchants", tags=["Merchants"])
api_router.include_router(discovery.router, prefix="/discover", tags=["Discovery"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["MCP"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
