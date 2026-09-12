"""Adaptive Game Model package.

A context-aware tactical adjustment engine for football.

The system answers the question:

    "Given the opponent's structure and our current game model, which tactical
    adjustment is most likely to improve our next attacking or defensive phase?"

This is an event-based tactical decision model, not a complete tracking-data
system. It estimates counterfactual expected possession value (EPV) for
alternative tactical responses inside automatically detected tactical states,
and communicates every recommendation with an explicit measure of uncertainty.
"""

__version__ = "1.0.0"
