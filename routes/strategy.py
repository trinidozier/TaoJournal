# routes/strategy.py
from fastapi import APIRouter, Depends
from db import database, strategy
from schemas.strategy import StrategyCreate
from auth import get_current_user  # adjust if needed

router = APIRouter()

@router.post("/strategies")
async def create_strategy(payload: StrategyCreate, user=Depends(get_current_user)):
    query = strategy.insert().values(
        user_id=user["id"],
        name=payload.name,
        description=payload.description
    )
    strategy_id = await database.execute(query)
    return {"id": strategy_id, "name": payload.name}
