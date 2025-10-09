# DB-CRAWL-AGENT
Agentic framework that translates natural language queries into analytic features, decomposes them into SQL tasks, executes them across databases, and leverages graph-based memoization for reuse.

📘 Table of Contents
	1.	Overview
	2.	Architecture
	3.	Core Modules
	4.	API Reference
	5.	Example Workflow
	6.	Testing
	7.	Deployment
	8.	Integration with Graph Memoization
	9.	Future Work


🧭 Overview

db-crawl is an agentic data-analysis framework that lets you query structured data warehouses using natural language.
It decomposes human intent into features, tasks, and SQL plans, then executes them across databases such as PostgreSQL, Snowflake, and AWS RDS.

User Query → Feature Orchestrator → Task Decomposer → SQL Executor → Insight Generator

Key Goals:
	•	LLM-driven feature reasoning
	•	Automated SQL generation
	•	Reuse via graph-memoization
	•	Multi-database compatibility

how to puild and deploy


 1. python -m build  
 2. twine upload dist/*x