from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.utils.json_db import accounts_db

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("")
async def get_accounts():
    accounts = accounts_db.read()
    return JSONResponse(accounts)
