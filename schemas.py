from pydantic import BaseModel, validator
from typing import Optional, List, Dict
from datetime import datetime
from fastapi import Query
from pydantic import EmailStr

class StrategyBase(BaseModel):
    name: str
    description: Optional[str] = None
    entry_rules: List[str] = []  # New: List of entry rule texts (unlimited)
    exit_rules: List[str] = []  # New: List of exit rule texts (unlimited)

class StrategyCreate(StrategyBase):
    pass  # For creating strategies with rules

class Strategy(StrategyBase):
    id: int
    user_email: str
    created_at: datetime

    class Config:
        from_attributes = True

class RuleBase(BaseModel):
    strategy_id: int
    rule_type: str  # 'entry' or 'exit'
    rule_text: str

class RuleCreate(RuleBase):
    pass

class Rule(RuleBase):
    id: int
    trade_id: Optional[int] = None
    followed: bool
    created_at: datetime

    class Config:
        from_attributes = True

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

# Broker models for connection (updated for multiple)
class BrokerCreate(BaseModel):
    name: Optional[str] = None  # Optional name for distinction (e.g., "My IBKR Account 1")
    broker_type: str  # 'ibkr' or 'schwab'
    creds: Dict  # e.g., for ibkr: {"host": str, "port": int, "client_id": int}; for schwab: {"api_token": str, "account_id": str}

class Broker(BrokerCreate):
    id: int
    user_email: str
    last_import: Optional[datetime] = None