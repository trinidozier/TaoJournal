🧠 Tao Trader: Annotation-First Trading Journal

Tao Trader is a modular, annotation-first trading journal built with FastAPI and deployed via Railway. It’s designed for traders who value precision, context, and analytics—offering a clean interface for logging trades, attaching insights, and visualizing performance.

This project reflects my journey into trading, Python development, web deployment, and data integrity. It’s a hands-on showcase of my ability to learn fast, troubleshoot deeply, and build tools that solve real problems.

🔧 Features

    Trade Logging API – Add, view, and delete trades with rich metadata (strategy, confidence, notes, etc.)

    Malware-Grade Backup Logic – Atomic JSON writes, timestamped backups, and auto-recovery to prevent data loss

    Analytics Dashboard – Live charting of win rate, loss rate, and average R-multiple using Matplotlib

    CSV Import – Parse and group Tradovate exports into structured trade entries

    PDF & Excel Export – Generate clean reports for review or sharing

    Image Attachments – Upload annotated screenshots or charts per trade

🛠 Tech Stack
Layer	Tools Used
Backend	FastAPI, Pydantic
Deployment	Railway, GitHub
Data Handling	JSON, CSV, Matplotlib
Security	Manual validation, backup rotation
Learning Tools	Google Cybersecurity Cert, Copilot

📈 Why It Matters

Tao Trader isn’t just a coding exercise—it’s a tool I use to track real trades, reflect on decisions, and improve performance. It’s built with the same mindset I bring to IT support: protect the data, respect the user, and make recovery painless.
🧪 What I Learned

    How to build and deploy a Python API from scratch

    How to use GitHub for version control and CI/CD

    How to handle malformed JSON and prevent data corruption

    How to collaborate with AI (Copilot) to troubleshoot and iterate quickly

    How to design endpoints that are intuitive and resilient

    How to add user authentication for SaaS

    How to build a Web-based UI

🚀 Next Steps

    Add Stripe integration for SaaS launch

    Add AI based inferences about users trade data

    Expand analytics to include equity curves and risk-adjusted metrics

🙋 About Me

I'm Trent Dozier—an experienced IT Support Specialist and stock market fanatic. Tao Trader is part of my journey to grow technically while staying grounded in practical problem-solving.

📫 Reach me at trinitydozier072@gmail.com 

## Setup
```bash
pip install -r requirements.txt
uvicorn main:app --reload
