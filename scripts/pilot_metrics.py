"""Pilot numbers straight from Firestore, using your own gcloud login (no keys).

    gcloud auth application-default login
    python scripts/pilot_metrics.py paisa-pilot-prod-8025
"""

import sys
from collections import Counter

from google.cloud import firestore

project = sys.argv[1] if len(sys.argv) > 1 else "paisa-pilot-prod-8025"
db = firestore.Client(project=project)

events = [d.to_dict() for d in db.collection("events").stream()]
by_event = Counter(e.get("event") for e in events)
visitors = {e.get("anon_id") for e in events}
funnel = ["landing_view", "sample_started", "consent_given", "document_uploaded", "document_confirmed", "advise_question"]

print(f"Anonymous visitors: {len(visitors)}")
print("Funnel (events):")
for name in funnel:
    print(f"  {name:<20} {by_event.get(name, 0)}")
print(f"Waitlist signups:   {sum(1 for _ in db.collection('waitlist').stream())}")
print("\nWrong-number reports:")
for d in db.collection("feedback").stream():
    f = d.to_dict()
    print(f"  [{f.get('card_id')}] {f.get('note')}")
