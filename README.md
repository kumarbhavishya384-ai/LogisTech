---
title: "LogisTech-OpenEnv: Autonomous Supply Chain Environment"
emoji: "📦"
colorFrom: "blue"
colorTo: "indigo"
sdk: "docker"
pinned: false
tags:
  - "openenv"
---

# LogisTech-OpenEnv: High-Fidelity Supply Chain Disruptor & Optimization Environment


LogisTech-OpenEnv is an industrial-strength simulation designed to evaluate agentic intelligence in complex global logistics scenarios. Unlike toy problems, agents must manage real-world constraints: inventory holding costs, shipping modes (Sea/Air/Truck), dynamic market demand, and sudden disruptions (strikes, holidays).

This environment is fully compliant with the **OpenEnv** specification.

## 🚀 Environment Overview
Agents act as global logistics coordinators managing a network of three warehouses (UK, Germany, China) and a fulfillment center. The goal is to maximize revenue, minimize expenses (holding/transit), and resolve critical alerts in a multi-step trajectory.

- **Domain:** Supply Chain Management / Global Logistics
- **Action Space:** Discrete (Typed Models)
- **Observation Space:** Structured JSON (Inventory, Shipments, Alerts, Financials)
- **Rewards:** Signal-rich, trajectory-based rewards (Revenue - Costs - Stockout Penalties).

## 🛠 Action Space
Actions are typed using Pydantic models. Available actions include:
- `TRANSFER`: Move stock between warehouses (e.g., DE -> UK).
- `REORDER`: Buy stock from suppliers to a destination warehouse.
- `REROUTE`: Expedite active shipments (e.g., Sea freight to Air freight).
- `NOTIFY`: Communicate with customers to mitigate stockout penalties.
- `PRIORITIZE`: Mark orders for high-value fulfillment.

## 🏥 Tasks & Difficulty
| Task ID | Name | Difficulty | Objective |
|---------|------|------------|-----------|
| `easy` | The UK Stockout | Easy | Identify iPhone shortage in UK and transfer from Germany. |
| `medium` | Shanghai Port Strike | Medium | Reroute MacBook sea shipments to Air to avoid a 10-day delay. |
| `hard` | Black Friday Resilience | Hard | Manage 3x demand surge with limited cash and inventory. |

## 📊 Baseline Scores
A rule-based baseline agent achieved the following scores:
```json
{
  "easy": 1.0,
  "medium": 1.0,
  "hard": 0.4
}
```

## 📦 Getting Started

### Local Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the server:
   ```bash
   python server.py
   ```
3. Run the baseline:
   ```bash
   python scripts/baseline_inference.py
   ```

### Docker Usage
```bash
docker build -t logistech-openenv .
docker run -p 7860:7860 logistech-openenv
```

## 🏷 Hugging Face Space
This environment is designed for deployment on HF Spaces using the `openenv` tag. Set your `OPENAI_API_KEY` (if using an LLM agent) as a secret in the HF Space settings.

## 📄 API Endpoints
- `/reset?task_id=easy`: Initialize environment for a task.
- `/step`: Submit an action and get the next observation.
- `/state`: Get full internal environment state.
- `/grader`: Get the current score based on trajectory history.
- `/tasks`: List all tasks and the action schema.
- `/baseline`: Run the internal baseline and return scores.
