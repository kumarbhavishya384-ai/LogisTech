---
title: LogisTech OpenEnv
emoji: 🛡️
colorFrom: indigo
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# 🛡️ LogisTech-OpenEnv: Autonomous Global Supply Chain 

![LogisTech Banner](static/assets/dashboard_bg.png)

<div align="center">
  <img src="https://img.shields.io/badge/OpenEnv-Certified-blueviolet?style=for-the-badge&logo=huggingface" alt="OpenEnv Certified">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker" alt="Docker Ready">
  <img src="https://img.shields.io/badge/FastAPI-Framework-05998b?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/Security-EmailJS_OTP-6366f1?style=for-the-badge&logo=shield" alt="OTP Security">
</div>

---

## 🚀 Overview
**LogisTech-OpenEnv** is a high-fidelity logistics simulation environment designed to train and evaluate the next generation of autonomous AI agents. Built on the **OpenEnv Standard**, it challenges agents to manage complex global supply chains, mitigate disruptions (like port strikes), and optimize inventory-to-revenue efficiency.

### 🏆 Key Features
- **🌐 Global Network**: Live simulation across nodes in London, Berlin, and Shanghai.
- **🛡️ Verifiable Security**: Integrated **EmailJS OTP** verification for authenticated onboarding.
- **📈 Real-Time Analytics**: Dynamic performance tracking via Chart.js for data-driven agent grading.
- **🤖 OpenEnv Compliant**: Gymnasium-style `step()`, `reset()`, and `state()` endpoints for instant AI integration.
- **✨ Glassmorphic UI**: Premium, state-of-the-art dashboard designed for the future of SaaS.

---

## 🛠 Technical Stack
- **Backend**: FastAPI (Python 3.11)
- **Database**: MongoDB Atlas (Vector/Document Store)
- **Security**: PyJWT & BCrypt hashing
- **Frontend**: Vanilla JS (ES6+), Vanilla CSS (Glassmorphism), Chart.js
- **Communications**: EmailJS SDK Integration

---

## 📦 Getting Started

### 1. Prerequisites
- Python 3.11+
- MongoDB Atlas Account
- EmailJS Account

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
MONGODB_URL=your_mongodb_url
SECRET_KEY=LOGISTECH_SUPER_SECRET
EMAILJS_SERVICE_ID=...
EMAILJS_TEMPLATE_OTP=...
EMAILJS_TEMPLATE_WELCOME=...
EMAILJS_PUBLIC_KEY=...
```

### 3. Run Locally
```bash
pip install -r requirements.txt
python server.py
# Open http://localhost:7860
```

### 4. Docker (Deployment)
```bash
docker build -t logistech-openenv .
docker run -p 7860:7860 logistech-openenv
```

---

## 📋 OpenEnv Specification
This environment is fully compliant with the **OpenEnv v1.0** specification.
- **Task IDs**: `easy`, `medium`, `hard`
- **Grader Endpoint**: `/grader?session_id=<id>`
- **Baseline Results**: Accessible via `/baseline`

---

<div align="center">
  <p>Built for the <b>Meta & Hugging Face: OpenEnv Challenge</b> by <i>Antigravity Agent</i> 🛡️🏆</p>
</div>
