# routes/rule.py
from fastapi import APIRouter
from db import database, rule
from schemas.rule import RuleCreate

router = APIRouter()

@router.post("/rules")
async def create_rule(payload: RuleCreate):
    query = rule.insert().values(
        strategy_id=payload.strategy_id,
        type=payload.type,
        description=payload.description,
        sort_order=payload.sort_order
    )
    rule_id = await database.execute(query)
    return {"id": rule_id, "description": payload.description}
