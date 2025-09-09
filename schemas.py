from pydantic import BaseModel, validator
from typing import Optional, List, Dict
from datetime import datetime
from fastapi import Query
from pydantic import EmailStr

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None

class StrategyCreate(StrategyBase):
    pass  # For creating strategies (already in main.py, kept for consistency)

class Strategy(StrategyBase):
    id: int
    user_email: str
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2+: Allows loading from dicts/Record attributes

class RuleBase(BaseModel):
    strategy_id: int
    rule_type: str  # 'entry' or 'exit'
    rule_text: str

class RuleCreate(RuleBase):
    pass  # For creating rules (already in main.py, kept for consistency)

class Rule(RuleBase):
    id: int
    trade_id: Optional[int] = None
    followed: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Reusing existing models from main.py (included here for clarity, but they stay in main.py)
class TradeIn(BaseModel):
    instrument: str
    buy_timestamp: datetime
    sell_timestamp: datetime
    buy_price: float
    sell_price: float
    qty: int
    direction: Optional[str] = None
    trade_type: Optional[str] = "Stock"
    strategy_id: Optional[int] = None
    rule_adherence: Optional[List[Dict]] = []  # List of {rule_id, followed}
    confidence: Optional[int] = 0
    target: Optional[float] = 0.0
    stop: Optional[float] = 0.0
    notes: Optional[str] = ""
    goals: Optional[str] = ""
    preparedness: Optional[str] = ""
    what_i_learned: Optional[str] = ""
    changes_needed: Optional[str] = ""

class Trade(TradeIn):
    direction: str
    pnl: float
    r_multiple: float
    image_path: Optional[str] = ""
    user: str
    id: Optional[int] = None

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    billing_address: str
    email: EmailStr
    password: str
    verify_password: str

    @validator("verify_password")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

class IBKRConnect(BaseModel):
    api_token: str
    account_id: str

class TradeRuleUpdate(BaseModel):
    followed: bool