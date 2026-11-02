"""
NLP Leave Reasons Dataset Generator
Curates and verifies a balanced corpus of 500+ realistic natural language leave application reasons across 5 target leave categories: CL, ML, EL, SCL, OD.
"""
import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any

from utils.logger import get_logger

logger = get_logger("nlp.dataset_generator")

# Target Leave Categories
LEAVE_CATEGORIES = {
    "CL": "Casual Leave",
    "ML": "Medical Leave",
    "EL": "Earned Leave",
    "SCL": "Special Casual Leave",
    "OD": "On Duty Leave",
}

# Template seed pattern lists for generating rich, diverse leave text variations
CL_REASONS = [
    "I need to attend a family function at my hometown.",
    "Personal work at the local RTO office for driving license renewal.",
    "Urgent domestic work at home regarding house renovation.",
    "Need one day leave for personal banking and property documentation work.",
    "Attending my cousin's wedding ceremony in Bangalore.",
    "Need leave for child's school annual day function and parent teacher meeting.",
    "Urgent plumbing and electrical repair work at my residence.",
    "I have some urgent personal commitments to attend to at my native place.",
    "Attending family religious ceremony and pooja at home.",
    "Need casual leave for apartment society management committee meeting.",
    "Personal errand regarding Aadhaar card address update and passport verification.",
    "Family emergency at home requiring my presence.",
    "Need leave to take my mother to government office for pension verification.",
    "Attending house warming ceremony of a close relative.",
    "Personal work related to home loan processing at bank branch.",
]

ML_REASONS = [
    "I am suffering from severe viral fever and doctor advised 3 days bed rest.",
    "Severe migraine headache and nausea since yesterday morning.",
    "Admitted to hospital for emergency appendicitis surgery and post-op care.",
    "Underwent dental root canal treatment and advised rest by dentist.",
    "Diagnosed with acute typhoid fever and prescribed medication rest for 5 days.",
    "Severe back pain due to lumbar sprain, physician recommended complete bed rest.",
    "High body temperature and chest infection, doctor advised isolation and medicine.",
    "Sustained leg fracture during sports and unable to walk or commute.",
    "Food poisoning and gastroenteritis leading to weakness and dehydration.",
    "Undergoing outpatient diagnostic tests and ultrasound scan at hospital.",
    "Eye infection conjunctivitis doctor advised 3 days rest to prevent spread.",
    "Severe asthma attack and respiratory allergy needing bed rest.",
    "Doctor advised medical rest following minor surgical procedure.",
    "Physically unwell with acute bronchitis and persistent coughing.",
    "Accidental wrist sprain needing immobilization and medical leave.",
]

EL_REASONS = [
    "Planning extended annual family vacation trip to North India.",
    "Availing earned leave for long planned international family tour.",
    "Taking 10 days earned leave for daughter's marriage preparations and reception.",
    "Extended domestic leave for ancestral property division and registration.",
    "Earned leave application for leisure trip to Kerala with family during break.",
    "Requesting 7 days earned leave for pilgrimage trip to Tirupati and Varanasi.",
    "Personal long leave for house construction supervision in hometown.",
    "Annual leave for family vacation and rest after continuous semester duties.",
    "Availing earned leave for elder son's higher education admission in Delhi.",
    "Extended leave for attending international family reunion event.",
]

SCL_REASONS = [
    "Attending IEEE International Conference on Artificial Intelligence to present paper.",
    "Participating in 5-day AICTE sponsored Faculty Development Program on Machine Learning.",
    "Deputed for VTU University semester end practical examination evaluation duty.",
    "Invited as key speaker for national seminar on Cybersecurity at MIT Manipal.",
    "Attending national level research workshop on Deep Learning in IIT Madras.",
    "Special casual leave for conducting PhD viva-voce examination as external referee.",
    "Delivering guest lecture on Cloud Computing at Regional Engineering College.",
    "Participating in DST sponsored research project review committee meeting.",
    "Attending National Board of Accreditation (NBA) evaluator orientation workshop.",
    "Deputed as chief superintendent for central evaluation of university answer scripts.",
]

OD_REASONS = [
    "Deputed on official university duty for inspecting affiliated college laboratories.",
    "Official visit to State Higher Education Council for syllabus revision meeting.",
    "On duty for accompanying MCA students on industrial visit to Infosys Mysore.",
    "Official duty for representing institute at University Athletic Meet coordination.",
    "Deputed by HOD for NAAC peer team accreditation preparation work at campus B.",
    "Official visit to Regional Science Centre for guiding student project exhibition.",
    "On duty leave for attending mandatory University Academic Council meeting.",
    "Official university deputation for conducting external lab examination.",
    "On official duty at Higher Education Department for scholarship scheme audit.",
    "Representing college at Inter-University Robotics Competition as faculty mentor.",
]


def generate_corpus_dataset(target_samples: int = 500) -> List[Dict[str, Any]]:
    """
    Generates a dataset of 500+ realistic leave reason text records across 5 target categories.
    """
    samples = []
    record_id = 1

    categories_seed = [
        ("CL", "Casual Leave", CL_REASONS),
        ("ML", "Medical Leave", ML_REASONS),
        ("EL", "Earned Leave", EL_REASONS),
        ("SCL", "Special Casual Leave", SCL_REASONS),
        ("OD", "On Duty Leave", OD_REASONS),
    ]

    # Target ~100+ samples per category
    per_category = max(100, target_samples // len(categories_seed))

    modifiers = [
        "",
        " Please grant me leave for the same.",
        " Requesting you to kindly approve my application.",
        " Doctor certificate is attached herewith for your reference.",
        " I will ensure my lecture topics are covered by substitute faculty.",
        " Kindly consider my request and grant permission.",
        " Thanking you in advance.",
        " I will resume duties immediately upon return.",
        " Necessary supporting documents have been uploaded.",
        " I have informed the HOD regarding lecture adjustments.",
    ]

    for code, name, seed_texts in categories_seed:
        cat_count = 0
        while cat_count < per_category:
            for seed in seed_texts:
                if cat_count >= per_category:
                    break

                mod = modifiers[cat_count % len(modifiers)]
                full_text = f"{seed}{mod}".strip()

                # Add minor realistic variations
                if cat_count % 3 == 1:
                    full_text = f"Respected Sir/Madam, {full_text}"
                elif cat_count % 3 == 2:
                    full_text = f"Due to urgent reasons, {full_text.lower()}"

                samples.append(
                    {
                        "id": record_id,
                        "text": full_text,
                        "label": code,
                        "leave_type_name": name,
                    }
                )
                record_id += 1
                cat_count += 1

    logger.info(f"Generated total {len(samples)} leave reason text samples for NLP corpus.")
    return samples


def save_corpus_files(samples: List[Dict[str, Any]], dataset_dir: str = "dataset") -> Dict[str, str]:
    """Saves generated corpus samples to JSON and CSV files."""
    p_dir = Path(dataset_dir)
    p_dir.mkdir(parents=True, exist_ok=True)

    json_path = p_dir / "leave_reasons_corpus.json"
    csv_path = p_dir / "leave_reasons_corpus.csv"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    # Save CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text", "label", "leave_type_name"])
        writer.writeheader()
        writer.writerows(samples)

    logger.info(f"Saved NLP Corpus JSON: {json_path.resolve()}")
    logger.info(f"Saved NLP Corpus CSV: {csv_path.resolve()}")

    return {
        "json_path": str(json_path.resolve()),
        "csv_path": str(csv_path.resolve()),
    }


def verify_and_build_dataset() -> Dict[str, Any]:
    """Builds, verifies, and returns dataset summary statistics."""
    samples = generate_corpus_dataset(target_samples=500)
    paths = save_corpus_files(samples)

    # Calculate statistics
    class_counts = {}
    total_words = 0

    for s in samples:
        lbl = s["label"]
        class_counts[lbl] = class_counts.get(lbl, 0) + 1
        total_words += len(s["text"].split())

    avg_words = round(total_words / len(samples), 1) if samples else 0.0

    stats = {
        "total_samples": len(samples),
        "class_counts": class_counts,
        "avg_words_per_sample": avg_words,
        "files": paths,
    }

    logger.info(f"Corpus Dataset Verification Stats: {stats}")
    return stats


if __name__ == "__main__":
    verify_and_build_dataset()
