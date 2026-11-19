"""Deterministic financial rules for Paisa Pilot.

No AI, no network calls. Every function here takes confirmed user data (and,
where relevant, a RulesConfig loaded from versioned YAML) and returns a plain
number or dataclass -- same input, same output, every time. This is the only
place in the codebase allowed to produce a rupee figure.
"""
