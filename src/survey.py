"""Pilot study survey data — quiz questions, experience items, CSV writer."""
from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path

_SAVE_LOCK = threading.Lock()

PRE_QUIZ = [
    {
        "q": "Which nerve is primarily responsible for wrist drop?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Axillary nerve"],
        "ans": "B",
    },
    {
        "q": "What spinal cord levels form the brachial plexus?",
        "opts": ["A. C1–C5", "B. C3–C8", "C. C5–T1", "D. C6–T2"],
        "ans": "C",
    },
    {
        "q": "A patient cannot oppose their thumb and has a flat thenar eminence — which nerve is injured?",
        "opts": ["A. Radial nerve", "B. Ulnar nerve", "C. Median nerve", "D. Musculocutaneous nerve"],
        "ans": "C",
    },
    {
        "q": "Which four muscles make up the rotator cuff?",
        "opts": [
            "A. Deltoid, Biceps, Triceps, Supraspinatus",
            "B. Supraspinatus, Infraspinatus, Teres Minor, Subscapularis",
            "C. Supraspinatus, Teres Major, Infraspinatus, Deltoid",
            "D. Biceps, Coracobrachialis, Subscapularis, Supraspinatus",
        ],
        "ans": "B",
    },
    {
        "q": "Which nerve passes through the cubital tunnel at the medial elbow?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Musculocutaneous nerve", "D. Ulnar nerve"],
        "ans": "D",
    },
]

POST_QUIZ = [
    {
        "q": "Saturday night palsy (arm draped over a chair back during sleep) compresses which nerve?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Axillary nerve"],
        "ans": "B",
    },
    {
        "q": "Erb's palsy (C5–C6) and Klumpke's palsy (C8–T1) are both injuries to which nerve network?",
        "opts": ["A. Lumbar plexus", "B. Cervical plexus", "C. Sacral plexus", "D. Brachial plexus"],
        "ans": "D",
    },
    {
        "q": "Carpal tunnel syndrome compresses a nerve, causing weakness in thumb opposition. Which nerve?",
        "opts": ["A. Radial nerve", "B. Ulnar nerve", "C. Median nerve", "D. Anterior interosseous nerve"],
        "ans": "C",
    },
    {
        "q": "An OT patient cannot externally rotate or abduct the shoulder after a fall. Which muscle group is most likely torn?",
        "opts": [
            "A. Long head of biceps brachii",
            "B. Rotator cuff",
            "C. Deltoid and trapezius",
            "D. Pectoralis major",
        ],
        "ans": "B",
    },
    {
        "q": "Cubitus valgus deformity stretches a nerve at the elbow, causing tingling in the ring and little fingers. Which nerve?",
        "opts": ["A. Median nerve", "B. Radial nerve", "C. Ulnar nerve", "D. Musculocutaneous nerve"],
        "ans": "C",
    },
]

EXPERIENCE_QUESTIONS = [
    "The tutor helped me understand anatomy concepts better.",
    "The Socratic questioning approach was effective for my learning.",
    "The tutor felt natural and easy to interact with (not robotic).",
    "I would use this tool to study for the NBCOT exam.",
    "I would recommend this tool to other OT or anatomy students.",
]


def save_results(data: dict) -> str:
    """Append one row to today's CSV. Thread-safe."""
    results_dir = os.getenv("SURVEY_RESULTS_DIR", "survey_results")
    Path(results_dir).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filepath = os.path.join(results_dir, f"survey_{date_str}.csv")
    with _SAVE_LOCK:
        is_new = not os.path.exists(filepath)
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(data.keys()))
            if is_new:
                writer.writeheader()
            writer.writerow(data)
    return filepath
