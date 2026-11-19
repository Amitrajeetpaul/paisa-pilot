"""Gemini access: document reading and plain-language explanation.

Single Google GenAI SDK client (client.py). Reader/explainer prompts and
schemas are loaded verbatim from ai_studio/ (prompts.py, schemas.py) so a
result tested in AI Studio and a result from this code are the same
experiment. Nothing in this package computes a rupee figure -- that's
rules_engine's job; the AI only extracts and explains.
"""
