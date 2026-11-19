"""FastAPI backend: upload -> read -> confirm -> calculate -> source trail.

Storage and DB backends are swappable (api/storage/, api/db/) so local dev
needs zero cloud account. No route here computes a rupee figure itself --
everything routes through rules_engine or agents, which route through
rules_engine.
"""
