from enum import Enum
from typing import Dict, List, Any
from models import Observation, LogisticsAction, Reward, Info

class TaskId(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class LogisticsGrader:
    @staticmethod
    def score(task_id: str, episode_history: List[Dict[str, Any]]) -> float:
        """
        Calculates a score from 0.0 to 1.0 based on the episode history.
        episode_history is a list of dicts: {'observation', 'action', 'reward', 'done', 'info', 'state'}
        """
        if not episode_history:
            return 0.0
        
        final_state = episode_history[-1]['state']
        
        if task_id == "easy":
            # Target: SKU_IPHONE in WH_UK should be > 0 at some point.
            # And at least one TRANSFER action was taken.
            transfer_taken = any(h['action']['action_type'] == "TRANSFER" for h in episode_history if h['action'])
            uk_stock = any(h['state']['warehouses']['WH_UK']['inventory'].get('SKU_IPHONE', 0) > 0 for h in episode_history)
            
            if transfer_taken and uk_stock:
                return 1.0
            elif transfer_taken:
                return 0.5 # Partial credit for trying
            return 0.0

        elif task_id == "medium":
            # Target: Reroute S1 to AIR.
            # Check if any action was REROUTE and params['id'] == 'S1' and params['mode'] == 'AIR'
            rerouted = any(
                h['action']['action_type'] == "REROUTE" and 
                h['action']['params'].get('id') == "S1" and 
                h['action']['params'].get('mode') == "AIR"
                for h in episode_history if h['action']
            )
            
            # Plus, success rate should be > 0.6
            success_rate = final_state['total_revenue'] / max(1, (final_state['total_revenue'] + final_state['unfilled_orders'] * 50))
            
            if rerouted and success_rate > 0.6:
                return 1.0
            elif rerouted:
                return 0.7
            return 0.0

        elif task_id == "hard":
            # Target: Profitability during Black Friday.
            # Cash balance should be higher than starting (200,000)
            # and unfilled orders should be relatively low (< 500)
            profit = final_state['cash_balance'] - 200000.0
            unfilled = final_state['unfilled_orders']
            
            if profit > 50000 and unfilled < 200:
                return 1.0
            elif profit > 20000 and unfilled < 500:
                return 0.8
            elif profit > 0:
                return 0.4
            return 0.0

        return 0.0

def get_tasks_list():
    return [
        {
            "id": "easy",
            "name": "The UK Stockout",
            "description": "The UK warehouse is out of iPhones. Transfer stock from the Berlin (DE) warehouse to resolve the crisis.",
            "difficulty": "Easy",
            "target_score": 1.0
        },
        {
            "id": "medium",
            "name": "Shanghai Port Strike",
            "description": "A port strike has delayed sea shipments from Shanghai. Reroute critical MacBook shipments to Air freight to ensure availability in Germany.",
            "difficulty": "Medium",
            "target_score": 1.0
        },
        {
            "id": "hard",
            "name": "Black Friday Resilience",
            "description": "Holiday surge is coming! Manage surging demand for all SKUs while keeping costs low and fulfilling at least 80% of orders.",
            "difficulty": "Hard",
            "target_score": 1.0
        }
    ]
