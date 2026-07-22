"""Statement import route — PDF upload → holdings → positions.

Endpoint:
  POST /api/v1/import/statement

Accepts a multipart form with:
  - ``file``: the PDF file (Schwab statement)
  - ``portfolio_id``: UUID of the target portfolio

Returns a summary of created/updated holdings.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio_manager.auth import current_active_user
from portfolio_manager.database import get_session
from portfolio_manager.models import Portfolio
from portfolio_manager.models.user import User
from portfolio_manager.services.statement_import import import_statement as _import_statement

router = APIRouter(prefix="/api/v1/import", tags=["import"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
}


async def _get_owned_portfolio(session: AsyncSession, portfolio_id: str, user_id) -> Portfolio:
    """Look up a portfolio owned by the user."""
    try:
        pid = UUID(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid portfolio_id") from exc

    result = await session.execute(
        select(Portfolio).where(Portfolio.id == pid, Portfolio.user_id == user_id)
    )
    portfolio = result.scalar_one_or_none()
    if portfolio is None:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post("/statement", status_code=status.HTTP_200_OK)
async def upload_statement(
    file: UploadFile = File(...),
    portfolio_id: str = Form(...),
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user),
) -> dict[str, object]:
    """Import holdings from a broker statement PDF.

    Upload a Schwab (or compatible) statement PDF. The service extracts
    the holdings table and creates/updates positions in the target portfolio.
    """
    # Validate ownership
    await _get_owned_portfolio(session, portfolio_id, user.id)

    # Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Expected PDF.",
        )

    # Read file contents
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Run import pipeline
    result = await _import_statement(session, portfolio_id, contents)
    await session.commit()
    return result
