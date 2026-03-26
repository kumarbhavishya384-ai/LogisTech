import random
import copy
from typing import Dict, List, Tuple
from models import Observation, LogisticsAction, Reward, Info, Warehouse, Shipment, ActionType

class LogisTechEnv:
    def __init__(self, task_id: str = "easy"):
        self.task_id = task_id
        self.max_steps = 30
        self.reset()

    def reset(self, task_id: str = None) -> Observation:
        if task_id:
            self.task_id = task_id

        self.current_day = 0
        self.cash_balance = 500000.0
        self.total_revenue = 0.0
        self.total_expenses = 0.0
        self.unfilled_orders = 0
        self.done = False

        # Warehouses setup
        self.warehouses = {
            "WH_UK": Warehouse(id="WH_UK", location="London, UK", inventory={"SKU_IPHONE": 0, "SKU_MACBOOK": 50}, capacity=500),
            "WH_DE": Warehouse(id="WH_DE", location="Berlin, Germany", inventory={"SKU_IPHONE": 100, "SKU_MACBOOK": 50}, capacity=500),
            "WH_SH": Warehouse(id="WH_SH", location="Shanghai, China", inventory={"SKU_IPHONE": 500, "SKU_MACBOOK": 200}, capacity=1000)
        }

        # Active shipments
        self.active_shipments = []

        # Alerts and Demand settings based on task
        self.alerts = []
        self.market_demand = {"SKU_IPHONE": 5.0, "SKU_MACBOOK": 2.0}

        if self.task_id == "easy":
            # Task: Stock transfer from DE to UK for iPhones
            self.alerts.append("UK Warehouse is out of IPHONE stock. DE Warehouse has surplus.")
            self.market_demand["SKU_IPHONE"] = 10.0
            self.max_steps = 10

        elif self.task_id == "medium":
            # Task: Sea freight delay due to strike. Need to reroute to Air.
            self.alerts.append("Shanghai Port Strike! All sea shipments from WH_SH are delayed 10 days.")
            self.active_shipments.append(Shipment(id="S1", sku="SKU_MACBOOK", quantity=50, origin="WH_SH", destination="WH_DE", status="IN_TRANSIT", mode="SEA", eta_days=5))
            self.max_steps = 15

        elif self.task_id == "hard":
            # Task: High demand surge (Black Friday) + Inventory crisis
            self.alerts.append("Black Friday Surge! Expect demand for all items to triple.")
            self.market_demand = {"SKU_IPHONE": 30.0, "SKU_MACBOOK": 15.0}
            self.max_steps = 30
            self.cash_balance = 200000.0 # Tighter budget

        return self.get_observation()

    def add_warehouse(self, wh_id: str, location: str, capacity: int, inventory: Dict[str, int] = None):
        """ Dynamically add a new branch to the network. """
        if wh_id not in self.warehouses:
            self.warehouses[wh_id] = Warehouse(
                id=wh_id, 
                location=location, 
                capacity=capacity, 
                inventory=inventory or {"SKU_IPHONE": 0, "SKU_MACBOOK": 0}
            )
            return True
        return False

    def get_observation(self) -> Observation:
        return Observation(
            warehouses=list(self.warehouses.values()),
            active_shipments=self.active_shipments,
            cash_balance=self.cash_balance,
            market_demand=self.market_demand,
            alerts=self.alerts,
            current_day=self.current_day
        )

    def state(self) -> Dict:
        return {
            "current_day": self.current_day,
            "cash_balance": self.cash_balance,
            "warehouses": {k: v.dict() for k, v in self.warehouses.items()},
            "shipments": [s.dict() for s in self.active_shipments],
            "total_revenue": self.total_revenue,
            "total_expenses": self.total_expenses,
            "unfilled_orders": self.unfilled_orders,
            "task_id": self.task_id,
            "done": self.done
        }

    def step(self, action: LogisticsAction) -> Tuple[Observation, Reward, bool, Info]:
        if self.done:
            return self.get_observation(), Reward(total=0.0), True, self.get_info()

        self.current_day += 1
        reward_components = {"revenue": 0.0, "cost": 0.0, "penalty": 0.0}

        # Process Agent Action
        self.process_action(action, reward_components)

        # Simulation updates
        self.process_shipments(reward_components)
        self.process_demand(reward_components)
        self.process_holding_costs(reward_components)

        total_reward = sum(reward_components.values())
        self.total_expenses -= (reward_components["cost"] + reward_components["penalty"])
        self.total_revenue += reward_components["revenue"]
        self.cash_balance += (reward_components["revenue"] + reward_components["cost"] + reward_components["penalty"])

        if self.current_day >= self.max_steps or self.cash_balance <= 0:
            self.done = True

        return self.get_observation(), Reward(total=total_reward, components=reward_components), self.done, self.get_info()

    def process_action(self, action: LogisticsAction, reward_components: dict):
        # Action implementation
        p = action.params
        if action.action_type == ActionType.TRANSFER:
            # {sku, origin, destination, quantity}
            sku, origin, dest, qty = p.get("sku"), p.get("origin"), p.get("destination"), p.get("quantity", 0)
            if origin in self.warehouses and dest in self.warehouses:
                wh_origin = self.warehouses[origin]
                if wh_origin.inventory.get(sku, 0) >= qty:
                    wh_origin.inventory[sku] -= qty
                    cost = qty * 2.0 # Fixed transfer cost per unit
                    reward_components["cost"] -= cost
                    self.active_shipments.append(Shipment(
                        id=f"T{random.randint(1000, 9999)}", sku=sku, quantity=qty,
                        origin=origin, destination=dest, status="IN_TRANSIT", mode="TRUCK", eta_days=2
                    ))

        elif action.action_type == ActionType.REROUTE:
            # {id, mode}
            ship_id, mode = p.get("id"), p.get("mode")
            for s in self.active_shipments:
                if s.id == ship_id:
                    if mode == "AIR" and s.mode != "AIR":
                        s.mode = "AIR"
                        s.eta_days = max(1, s.eta_days // 2)
                        reward_components["cost"] -= 500.0 # Rerouting fee

        elif action.action_type == ActionType.REORDER:
            # {sku, destination, quantity}
            sku, dest, qty = p.get("sku"), p.get("destination"), p.get("quantity", 0)
            if dest in self.warehouses:
                cost = qty * 10.0 # Purchase cost
                reward_components["cost"] -= cost
                self.active_shipments.append(Shipment(
                    id=f"R{random.randint(1000, 9999)}", sku=sku, quantity=qty,
                    origin="SUPPLIER", destination=dest, status="IN_TRANSIT", mode="SEA", eta_days=10
                ))

        elif action.action_type == ActionType.NOTIFY:
            # {order_id, message}
            # Reduces penalty for delayed orders
            reward_components["cost"] -= 50.0 # Communication overhead

    def process_shipments(self, reward_components: dict):
        to_remove = []
        for s in self.active_shipments:
            s.eta_days -= 1
            if s.eta_days <= 0:
                if s.destination in self.warehouses:
                    wh = self.warehouses[s.destination]
                    wh.inventory[s.sku] = wh.inventory.get(s.sku, 0) + s.quantity
                to_remove.append(s)
        
        for s in to_remove:
            self.active_shipments.remove(s)

    def process_demand(self, reward_components: dict):
        for wh_id, wh in self.warehouses.items():
            for sku, demand_base in self.market_demand.items():
                if wh_id == "WH_SH": continue # SH is mostly fulfillment center/factory
                
                # Randomized demand
                actual_demand = int(random.gauss(demand_base, 2))
                actual_demand = max(0, actual_demand)
                
                filled = min(wh.inventory.get(sku, 0), actual_demand)
                wh.inventory[sku] -= filled
                self.unfilled_orders += (actual_demand - filled)
                
                reward_components["revenue"] += (filled * 50.0)
                reward_components["penalty"] -= ((actual_demand - filled) * 20.0) # Lost sale penalty

    def process_holding_costs(self, reward_components: dict):
        for wh in self.warehouses.values():
            total_inv = sum(wh.inventory.values())
            reward_components["cost"] -= (total_inv * 0.5) # Storage cost

    def get_info(self) -> Info:
        total_attempts = self.total_revenue / 50.0 + self.unfilled_orders
        success_rate = (self.total_revenue / 50.0) / max(1, total_attempts)
        return Info(
            success_rate=success_rate,
            unfilled_orders=self.unfilled_orders,
            total_revenue=self.total_revenue,
            total_expenses=self.total_expenses
        )
