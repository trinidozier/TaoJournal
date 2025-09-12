from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Strategy(StrategyCreate):
    id: int
    user_email: str
    created_at: datetime

class RuleCreate(BaseModel):
    strategy_id: int
    rule_type: str
    rule_text: str

class Rule(RuleCreate):
    id: int
    trade_id: Optional[int] = None
    followed: bool
    created_at: datetime

class TradeIn(BaseModel):
    buy_price: float
    sell_price: float
    qty: int
    buy_timestamp: Optional[str] = None
    sell_timestamp: Optional[str] = None
    direction: Optional[str] = None
    stop: Optional[float] = None
    fees: Optional[float] = 0

class Trade(TradeIn):
    id: int
    user: str
    pnl: float
    r_multiple: float
    timestamp: str

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    billing_address: str
    email: str
    password: str

class IBKRConnect(BaseModel):
    api_token: str
    account_id: str

class TradeRuleUpdate(BaseModel):
    followed: bool

class BrokerCreate(BaseModel):
    user_email: str
    broker_type: str
    creds_json: str

class Broker(BrokerCreate):
    id: int
    last_import: Optional[datetime] = None