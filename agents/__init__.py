"""Google ADK agents: Money Finder, Leak Fixer, AI Consultant.

Each agent is a simple tool-using Agent (not fully autonomous -- safer for
money advice, per the brief). Every tool in tools.py is a thin wrapper
around rules_engine; none of them compute anything themselves, so an
agent's only way to get a rupee figure is to call one of these.
"""
