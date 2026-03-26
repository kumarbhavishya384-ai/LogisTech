from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class ActionType(str, Enum):
    TRANSFER = "TRANSFER"  # Move stock between warehouses
    REORDER = "REORDER"   # Buy new stock from supplier
    REROUTE = "REROUTE"   # Change transport mode (e.g., Sea -> Air)
    NOTIFY = "NOTIFY"     # Send customer update to manage expectations
    PRIORITIZE = "PRIORITIZE" # Mark high-value orders for immediate shipping

class LogisticsAction(BaseModel):
    action_type: ActionType
    params: Dict[str, Any] = Field(..., description="Action parameters: sku, origin, destination, quantity, order_id, etc.")

class Warehouse(BaseModel):
    id: str
    location: str
    inventory: Dict[str, int]  # SKU -> current stock
    capacity: int

class Shipment(BaseModel):
    id: str
    sku: str
    quantity: int
    origin: str
    destination: str
    status: str
    mode: str  # SEA, AIR, RAIL, TRUCK
    eta_days: int

class Observation(BaseModel):
    warehouses: List[Warehouse]
    active_shipments: List[Shipment]
    cash_balance: float
    market_demand: Dict[str, float]  # SKU -> expected demand factor
    alerts: List[str]
    current_day: int

class Reward(BaseModel):
    total: float
    components: Dict[str, float] = Field(
        default_factory=lambda: {"revenue": 0.0, "cost": 0.0, "penalty": 0.0}
    )

class Info(BaseModel):
    success_rate: float
    unfilled_orders: int
    total_revenue: float
    total_expenses: float
