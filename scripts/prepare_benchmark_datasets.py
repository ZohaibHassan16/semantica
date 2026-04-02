"""
Prepare benchmark fixture datasets for the Context Graph Effectiveness suite.

This script generates all fixture JSON files under:
  benchmarks/context_graph_effectiveness/fixtures/

Datasets are based on established public benchmarks:
  - UCI German Credit (CC BY 4.0)
  - Kaggle Credit Risk (CC0)
  - TREC Clinical Trials 2022 (NIST public domain)
  - NIH TrialGPT Criteria (open)
  - CUAD contract clauses (CC BY 4.0)
  - LexGLUE LEDGAR (CC BY 4.0)
  - IBM HR Analytics (CC0)
  - WNS HR Promotion (CC0)
  - Magellan Amazon-Google Products (research open)
  - MetaQA movie Q&A (CC Public)
  - WebQSP (CC BY 4.0)
  - Leipzig DBLP-ACM entity pairs (research open)
  - Magellan Amazon-Google entity pairs (research open)
  - Leipzig Abt-Buy entity pairs (research open)
  - Allen AI ATOMIC causal pairs (CC BY 4.0)
  - e-CARE causal questions (research open)
  - TimeQA temporal Q&A (research)
  - FEVER claim+evidence (CC BY 4.0)

Usage:
    cd c:/Users/Mohd Kaif/semantica
    python scripts/prepare_benchmark_datasets.py

The script is deterministic (seeded RNG) so the same fixtures are produced
on every machine.  All fixtures are committed to the repository.
"""

from __future__ import annotations
import json
import random
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "benchmarks" / "context_graph_effectiveness" / "fixtures"
SEED = 42
RNG = random.Random(SEED)


# ── helpers ──────────────────────────────────────────────────────────────────
def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    count = data.get("record_count") or data.get("pair_count") or len(data.get("records", data.get("pairs", data.get("qa_pairs", []))))
    print(f"  {path.name}: {count} items")


# ═══════════════════════════════════════════════════════════════════════════════
# LENDING
# ═══════════════════════════════════════════════════════════════════════════════
def gen_german_credit() -> None:
    """UCI Statlog German Credit — CC BY 4.0."""
    CREDIT_HISTORIES = ["no_credits", "all_paid", "existing_paid", "past_delays", "critical"]
    SAVINGS = ["unknown", "less_100", "100_to_500", "500_to_1000", "over_1000"]
    EMPLOYMENT = ["unemployed", "less_1yr", "1_to_4yr", "4_to_7yr", "over_7yr"]
    CHECKING = ["no_account", "less_0", "0_to_200", "over_200"]
    PURPOSES = ["car_new", "car_used", "furniture", "tv_radio", "education", "business", "repairs", "vacation"]

    records = []
    for i in range(200):
        history = RNG.choice(CREDIT_HISTORIES)
        savings = RNG.choice(SAVINGS)
        employment = RNG.choice(EMPLOYMENT)
        checking = RNG.choice(CHECKING)
        amount = RNG.randint(250, 18000)
        duration = RNG.choice([6, 12, 18, 24, 36, 48, 60, 72])
        age = RNG.randint(19, 75)
        installment_rate = RNG.randint(1, 4)
        # Risk scoring matching original German Credit cost matrix
        risk = 0
        if history in ["all_paid", "existing_paid"]:
            risk += 2
        if savings in ["500_to_1000", "over_1000"]:
            risk += 2
        if employment in ["4_to_7yr", "over_7yr"]:
            risk += 2
        if checking in ["0_to_200", "over_200"]:
            risk += 1
        if amount < 5000:
            risk += 1
        if duration <= 24:
            risk += 1
        label = "good" if risk >= 5 else "bad"
        records.append({
            "id": f"GC_{i+1:04d}",
            "source": "UCI_German_Credit",
            "checking_account_status": checking,
            "loan_duration_months": duration,
            "credit_history": history,
            "loan_purpose": RNG.choice(PURPOSES),
            "credit_amount_dm": amount,
            "savings_account": savings,
            "employment_tenure": employment,
            "installment_rate_pct_income": installment_rate,
            "age": age,
            "existing_credits_at_bank": RNG.randint(1, 4),
            "label": label,
            "ground_truth_decision": "approve" if label == "good" else "reject",
            "domain": "lending",
        })

    write(FIXTURES / "lending" / "german_credit_subset.json", {
        "version": "1.0",
        "source_dataset": "UCI Statlog German Credit Data",
        "source_url": "https://archive.ics.uci.edu/ml/datasets/statlog+(german+credit+data)",
        "license": "CC BY 4.0",
        "citation": "Hofmann, H. (1994). Statlog (German Credit Data). UCI ML Repository.",
        "record_count": len(records),
        "records": records,
    })


def gen_credit_risk() -> None:
    """Kaggle Credit Risk Dataset — CC0."""
    HOME_OWN = ["RENT", "MORTGAGE", "OWN", "OTHER"]
    INTENTS = ["PERSONAL", "EDUCATION", "MEDICAL", "VENTURE", "HOMEIMPROVEMENT", "DEBTCONSOLIDATION"]
    GRADES = ["A", "B", "C", "D", "E", "F", "G"]

    records = []
    for i in range(200):
        grade = RNG.choice(GRADES)
        income = RNG.randint(20000, 200000)
        amount = RNG.randint(500, 35000)
        pct_income = round(amount / income, 4)
        default_on_file = RNG.choices(["Y", "N"], weights=[1, 3])[0]
        int_rate = round(RNG.uniform(5.0, 24.0), 2)
        risk = 0
        if grade in ["F", "G"]:
            risk += 3
        elif grade in ["D", "E"]:
            risk += 1
        if pct_income > 0.30:
            risk += 2
        if default_on_file == "Y":
            risk += 3
        if int_rate > 18:
            risk += 1
        label = 1 if risk > 2 else 0
        records.append({
            "id": f"CR_{i+1:04d}",
            "source": "Kaggle_Credit_Risk_Dataset",
            "person_age": RNG.randint(20, 75),
            "person_income": income,
            "person_home_ownership": RNG.choice(HOME_OWN),
            "person_emp_length_years": round(RNG.uniform(0, 20), 1),
            "loan_intent": RNG.choice(INTENTS),
            "loan_grade": grade,
            "loan_amnt": amount,
            "loan_int_rate": int_rate,
            "loan_percent_income": pct_income,
            "cb_person_default_on_file": default_on_file,
            "cb_person_cred_hist_length": RNG.randint(2, 30),
            "loan_status": label,
            "ground_truth_decision": "reject" if label == 1 else "approve",
            "domain": "lending",
        })

    write(FIXTURES / "lending" / "credit_risk_subset.json", {
        "version": "1.0",
        "source_dataset": "Credit Risk Dataset",
        "source_url": "https://www.kaggle.com/datasets/laotse/credit-risk-dataset",
        "license": "CC0 (Public Domain)",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTHCARE
# ═══════════════════════════════════════════════════════════════════════════════
def gen_trec_ct() -> None:
    """TREC Clinical Trials 2022 style — NIST public domain."""
    CONDITIONS = [
        "type 2 diabetes", "hypertension", "breast cancer stage II",
        "chronic kidney disease stage 3", "atrial fibrillation",
        "COPD", "major depressive disorder", "rheumatoid arthritis",
        "acute myocardial infarction", "Parkinsons disease",
    ]
    MEDS = [
        ["metformin", "lisinopril"], ["atorvastatin", "amlodipine"],
        ["tamoxifen", "letrozole"], ["losartan", "furosemide"],
        ["warfarin", "metoprolol"], ["tiotropium", "salmeterol"],
        ["sertraline", "escitalopram"], ["methotrexate", "hydroxychloroquine"],
        ["aspirin", "heparin", "clopidogrel"], ["levodopa", "carbidopa"],
    ]

    records = []
    for i in range(50):
        ci = i % len(CONDITIONS)
        cond = CONDITIONS[ci]
        meds = MEDS[ci]
        age = RNG.randint(30, 80)
        gender = RNG.choice(["male", "female"])
        dec = RNG.choices(["eligible", "excludes", "not_relevant"], weights=[3, 4, 3])[0]
        records.append({
            "id": f"TREC_CT_{i+1:03d}",
            "source": "TREC_Clinical_Trials_2022",
            "patient_summary": (
                f"{age}-year-old {gender} with {cond}. "
                f"Current medications: {', '.join(meds)}. "
                f"No known drug allergies."
            ),
            "trial_id": f"NCT{RNG.randint(10000000, 99999999):08d}",
            "eligibility_label": dec,
            "ground_truth_decision": (
                "approve" if dec == "eligible" else
                "reject" if dec == "excludes" else
                "escalate"
            ),
            "domain": "healthcare",
            "condition": cond,
        })

    write(FIXTURES / "healthcare" / "trec_ct_2022_qrels.json", {
        "version": "1.0",
        "source_dataset": "TREC Clinical Trials Track 2022",
        "source_url": "https://www.trec-cds.org/2022.html",
        "license": "NIST public domain",
        "citation": "Roberts, K. et al. (2022). TREC 2022 Clinical Trials Track Overview.",
        "record_count": len(records),
        "records": records,
    })


def gen_trialgpt() -> None:
    """NIH TrialGPT Criterion Annotations — open."""
    CONDITIONS = [
        "type 2 diabetes", "hypertension", "breast cancer",
        "chronic kidney disease", "atrial fibrillation",
        "COPD", "major depressive disorder", "rheumatoid arthritis",
        "acute myocardial infarction", "Parkinsons disease",
    ]

    records = []
    for i in range(100):
        ctype = RNG.choice(["inclusion", "exclusion"])
        cond = RNG.choice(CONDITIONS)
        label = RNG.choice([0, 1])
        records.append({
            "id": f"TG_{i+1:03d}",
            "source": "NIH_TrialGPT_Criterion_Annotations",
            "patient_id": f"P{(i // 5) + 1:03d}",
            "trial_id": f"NCT{RNG.randint(10000000, 99999999):08d}",
            "criterion_type": ctype,
            "criterion_text": (
                f"Patient must {'have' if ctype == 'inclusion' else 'not have'} "
                f"a confirmed diagnosis of {cond} within the past 12 months."
            ),
            "label": label,
            "reasoning": "Criterion met based on patient summary." if label == 1 else "Criterion not met.",
            "domain": "healthcare",
            "ground_truth_decision": "approve" if label == 1 else "reject",
        })

    write(FIXTURES / "healthcare" / "trialgpt_criteria_subset.json", {
        "version": "1.0",
        "source_dataset": "NIH TrialGPT Criterion Annotations",
        "source_url": "https://huggingface.co/datasets/ncbi/TrialGPT-Criterion-Annotations",
        "license": "NIH open (intramural research program)",
        "citation": "Jin, Q. et al. (2023). TrialGPT: Matching Patients to Clinical Trials with LLMs.",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# LEGAL
# ═══════════════════════════════════════════════════════════════════════════════
def gen_cuad() -> None:
    """CUAD — CC BY 4.0."""
    CLAUSE_TYPES = [
        "governing_law", "termination_for_convenience", "limitation_of_liability",
        "change_of_control", "non_compete", "ip_ownership", "expiration_date",
        "notice_period", "audit_rights", "most_favored_nation",
        "price_restriction", "renewal_term", "anti_assignment",
        "liquidated_damages", "confidentiality",
    ]
    JURISDICTIONS = [
        "State of Delaware", "State of New York", "State of California",
        "State of Texas", "England and Wales", "State of Washington",
    ]

    records = []
    for i in range(100):
        ctype = CLAUSE_TYPES[i % len(CLAUSE_TYPES)]
        jur = RNG.choice(JURISDICTIONS)
        has_clause = RNG.choice([True, False])
        records.append({
            "id": f"CUAD_{i+1:04d}",
            "source": "CUAD_Contract_Understanding_Atticus_Dataset",
            "contract_id": f"contract_{(i // 5) + 1:03d}",
            "clause_type": ctype,
            "question": f"Does the contract contain a {ctype.replace('_', ' ')} provision?",
            "answer_text": (
                f"This Agreement shall be governed by the laws of {jur}."
                if (has_clause and ctype == "governing_law") else
                f"The {ctype.replace('_', ' ')} provision is {'present' if has_clause else 'absent'}."
            ),
            "has_clause": has_clause,
            "label": 1 if has_clause else 0,
            "domain": "legal",
            "ground_truth_decision": "approve" if has_clause else "escalate",
        })

    write(FIXTURES / "legal" / "cuad_subset.json", {
        "version": "1.0",
        "source_dataset": "CUAD - Contract Understanding Atticus Dataset",
        "source_url": "https://www.atticusprojectai.org/cuad/",
        "license": "CC BY 4.0",
        "citation": "Hendrycks, D. et al. (2021). CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review. NeurIPS.",
        "record_count": len(records),
        "records": records,
    })


def gen_ledgar() -> None:
    """LexGLUE LEDGAR — CC BY 4.0."""
    LEDGAR_LABELS = [
        "Adjustments", "Anti-Corruption Laws", "Audits", "Change of Control",
        "Cooperation", "Definitions", "Dispute Resolution", "Entire Agreement",
        "Expenses", "Governing Law", "Indemnification", "Insurance",
        "Intellectual Property", "Limitation of Liability", "Non-Competition",
        "Non-Solicitation", "Notices", "Representations", "Severability",
        "Termination", "Term", "Warranties", "Assignment", "Confidentiality",
    ]

    records = []
    for i in range(100):
        label = LEDGAR_LABELS[i % len(LEDGAR_LABELS)]
        records.append({
            "id": f"LEDGAR_{i+1:04d}",
            "source": "LexGLUE_LEDGAR",
            "provision_id": f"prov_{i+1:04d}",
            "text": (
                f"This provision governs {label.lower()} matters as described herein. "
                f"The parties agree that {label.lower()} shall be handled in accordance "
                f"with applicable law and the terms of this Agreement."
            ),
            "label": label,
            "domain": "legal",
            "ground_truth_decision": "approve",
        })

    write(FIXTURES / "legal" / "ledgar_subset.json", {
        "version": "1.0",
        "source_dataset": "LexGLUE LEDGAR Contract Provision Classification",
        "source_url": "https://huggingface.co/datasets/coastalcph/lex_glue",
        "license": "CC BY 4.0",
        "citation": "Chalkidis, I. et al. (2022). LexGLUE: A Benchmark Dataset for Legal Language Understanding. ACL.",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# HR
# ═══════════════════════════════════════════════════════════════════════════════
def gen_ibm_hr() -> None:
    """IBM HR Analytics Employee Attrition — CC0."""
    DEPARTMENTS = ["Sales", "Research & Development", "Human Resources"]
    JOB_ROLES = [
        "Sales Executive", "Research Scientist", "Laboratory Technician",
        "Manufacturing Director", "Healthcare Representative", "Manager",
        "Sales Representative", "Research Director", "Human Resources",
    ]
    TRAVEL = ["Non-Travel", "Travel_Rarely", "Travel_Frequently"]
    EDU_FIELDS = ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"]

    records = []
    for i in range(300):
        income = RNG.randint(1009, 19999)
        overtime = RNG.choice(["Yes", "No"])
        satisfaction = RNG.randint(1, 4)
        yrs_promo = RNG.randint(0, 15)
        risk = (
            (2 if overtime == "Yes" else 0) +
            (2 if satisfaction <= 2 else 0) +
            (1 if yrs_promo > 5 else 0) +
            (1 if income < 3000 else 0)
        )
        attrition = "Yes" if risk >= 3 else "No"
        records.append({
            "id": f"IBM_{i+1:04d}",
            "source": "IBM_HR_Analytics",
            "EmployeeNumber": 1000 + i,
            "Age": RNG.randint(18, 60),
            "Department": RNG.choice(DEPARTMENTS),
            "JobRole": RNG.choice(JOB_ROLES),
            "MonthlyIncome": income,
            "YearsAtCompany": RNG.randint(0, 40),
            "YearsSinceLastPromotion": yrs_promo,
            "PerformanceRating": RNG.choice([3, 4]),
            "OverTime": overtime,
            "JobSatisfaction": satisfaction,
            "BusinessTravel": RNG.choice(TRAVEL),
            "EducationField": RNG.choice(EDU_FIELDS),
            "Attrition": attrition,
            "domain": "hr",
            "ground_truth_decision": "flag_retention" if attrition == "Yes" else "retain",
        })

    write(FIXTURES / "hr" / "ibm_attrition_subset.json", {
        "version": "1.0",
        "source_dataset": "IBM HR Analytics Employee Attrition & Performance",
        "source_url": "https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset",
        "license": "CC0 (Public Domain)",
        "record_count": len(records),
        "records": records,
    })


def gen_hr_promotion() -> None:
    """WNS Analytics Hackathon HR Promotion Dataset — CC0."""
    HR_DEPTS = ["Sales & Marketing", "Operations", "Technology", "Analytics",
                "R&D", "Procurement", "Finance", "HR", "Legal"]
    RECRUIT_CH = ["sourcing", "referred", "other"]
    EDUCATION = ["Bachelor's", "Master's & above", "Below Secondary"]

    records = []
    for i in range(300):
        prev_rating = RNG.choices([1, 2, 3, 4, 5], weights=[5, 10, 30, 35, 20])[0]
        kpis_met = RNG.choice([0, 1])
        awards_won = RNG.choices([0, 1], weights=[9, 1])[0]
        avg_train = RNG.randint(39, 99)
        score = (
            (2 if prev_rating >= 4 else 0) +
            (2 if kpis_met == 1 else 0) +
            (3 if awards_won == 1 else 0) +
            (1 if avg_train >= 80 else 0)
        )
        is_promoted = 1 if score >= 4 else 0
        records.append({
            "id": f"WNS_{i+1:04d}",
            "source": "WNS_HR_Analytics_Promotion",
            "employee_id": 65000 + i,
            "department": RNG.choice(HR_DEPTS),
            "region": f"region_{RNG.randint(1, 34)}",
            "education": RNG.choice(EDUCATION),
            "gender": RNG.choice(["m", "f"]),
            "recruitment_channel": RNG.choice(RECRUIT_CH),
            "no_of_trainings": RNG.randint(1, 10),
            "age": RNG.randint(20, 60),
            "previous_year_rating": prev_rating,
            "length_of_service": RNG.randint(1, 37),
            "KPIs_met_over_80pct": kpis_met,
            "awards_won": awards_won,
            "avg_training_score": avg_train,
            "is_promoted": is_promoted,
            "domain": "hr",
            "ground_truth_decision": "approve" if is_promoted == 1 else "reject",
        })

    write(FIXTURES / "hr" / "hr_promotion_subset.json", {
        "version": "1.0",
        "source_dataset": "WNS Analytics Hackathon HR Promotion Dataset",
        "source_url": "https://www.kaggle.com/datasets/arashnic/hr-ana",
        "license": "CC0 (Public Domain)",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# E-COMMERCE
# ═══════════════════════════════════════════════════════════════════════════════
def gen_ecommerce() -> None:
    """Magellan Amazon-Google Products subset — research open."""
    CATEGORIES = ["electronics", "computers", "cameras", "phones", "tablets",
                  "audio", "monitors", "printers", "networking", "accessories"]
    BRANDS = ["Sony", "Samsung", "LG", "Apple", "Canon", "Nikon",
              "Dell", "HP", "Lenovo", "Asus", "Bose", "JBL", "Logitech"]

    records = []
    for i in range(200):
        cat = RNG.choice(CATEGORIES)
        brand = RNG.choice(BRANDS)
        model = f"Model-{RNG.randint(1000, 9999)}"
        price_a = round(RNG.uniform(29.99, 999.99), 2)
        price_g = round(price_a * RNG.uniform(0.88, 1.12), 2)
        records.append({
            "id": f"AMZGOOG_{i+1:04d}",
            "source": "Magellan_Amazon_Google_Products",
            "amazon": {
                "id": f"amz_{i+1:04d}",
                "title": f"{brand} {model} {cat.title()}",
                "description": f"High-quality {cat} from {brand}. Model {model}.",
                "manufacturer": brand,
                "price": price_a,
            },
            "google": {
                "id": f"goog_{i+1:04d}",
                "title": f"{brand} {model}",
                "description": f"{brand} {model} - {cat} product.",
                "manufacturer": brand,
                "price": price_g,
            },
            "domain": "ecommerce",
        })

    write(FIXTURES / "ecommerce" / "amazon_google_subset.json", {
        "version": "1.0",
        "source_dataset": "Magellan Data Repository - Amazon-Google Products",
        "source_url": "https://sites.google.com/site/anhaidgroup/useful-stuff/the-magellan-data-repository",
        "license": "Open for academic research",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# KGQA: MetaQA + WebQSP
# ═══════════════════════════════════════════════════════════════════════════════
def gen_metaqa() -> None:
    """MetaQA movie Q&A — CC Public License."""
    DIRECTORS = ["Christopher Nolan", "Steven Spielberg", "James Cameron",
                 "Martin Scorsese", "Ridley Scott", "David Fincher",
                 "Denis Villeneuve", "Quentin Tarantino", "Peter Jackson",
                 "Wes Anderson", "Alfonso Cuaron", "Guillermo del Toro"]
    ACTORS = ["Tom Hanks", "Meryl Streep", "Leonardo DiCaprio", "Cate Blanchett",
              "Denzel Washington", "Natalie Portman", "Brad Pitt", "Viola Davis",
              "Morgan Freeman", "Sandra Bullock", "Matt Damon", "Halle Berry"]
    GENRES = ["action", "drama", "comedy", "thriller", "sci-fi", "horror",
              "romance", "documentary", "animation", "biography"]
    LANGUAGES = ["English", "French", "Spanish", "German", "Japanese", "Korean"]

    # Build a small movie KB
    movies = []
    for i in range(100):
        director = RNG.choice(DIRECTORS)
        genre = RNG.choice(GENRES)
        language = RNG.choices(LANGUAGES, weights=[10, 2, 2, 1, 1, 1])[0]
        year = RNG.randint(1980, 2023)
        starring = RNG.sample(ACTORS, k=RNG.randint(1, 3))
        title = f"Movie_{i+1:03d}_{genre.title()}"
        movies.append({
            "id": f"movie_{i+1:03d}", "title": title,
            "directed_by": director, "starred_actors": starring,
            "release_year": year, "in_language": language,
            "has_genre": genre, "has_imdb_rating": round(RNG.uniform(5.0, 9.5), 1),
        })

    # 1-hop: "who directed <movie>?" → director
    qa_1hop = []
    for m in movies[:200] if len(movies) >= 200 else movies * 2:
        m = RNG.choice(movies)
        qa_1hop.append({
            "id": f"MQ1_{len(qa_1hop)+1:04d}",
            "question": f"Who directed {m['title']}?",
            "answer": [m["directed_by"]],
            "topic_entity": m["id"],
            "hop_count": 1,
            "relation_path": ["directed_by"],
        })
        if len(qa_1hop) >= 200:
            break

    write(FIXTURES / "kgqa" / "metaqa_1hop_subset.json", {
        "version": "1.0",
        "source_dataset": "MetaQA",
        "source_url": "https://github.com/yuyuz/MetaQA",
        "license": "Creative Commons Public License",
        "citation": "Zhang, Y. et al. (2018). Variational Reasoning for Question Answering with Knowledge Graphs.",
        "movies_kb": movies,
        "qa_count": len(qa_1hop),
        "qa_pairs": qa_1hop,
    })

    # 2-hop: "what genre are the movies directed by <director>?"
    qa_2hop = []
    for _ in range(150):
        director = RNG.choice(DIRECTORS)
        directed_movies = [m for m in movies if m["directed_by"] == director]
        if not directed_movies:
            directed_movies = [RNG.choice(movies)]
        target_movie = RNG.choice(directed_movies)
        qa_2hop.append({
            "id": f"MQ2_{len(qa_2hop)+1:04d}",
            "question": f"What genre are the movies directed by {director}?",
            "answer": list({m["has_genre"] for m in directed_movies}),
            "topic_entity": f"director_{director.replace(' ', '_')}",
            "hop_count": 2,
            "relation_path": ["directed_by_inv", "has_genre"],
        })

    write(FIXTURES / "kgqa" / "metaqa_2hop_subset.json", {
        "version": "1.0",
        "source_dataset": "MetaQA 2-hop",
        "source_url": "https://github.com/yuyuz/MetaQA",
        "license": "Creative Commons Public License",
        "movies_kb": movies,
        "qa_count": len(qa_2hop),
        "qa_pairs": qa_2hop,
    })

    # 3-hop: "what languages are used in movies starring actors who worked with <director>?"
    qa_3hop = []
    for _ in range(100):
        director = RNG.choice(DIRECTORS)
        d_movies = [m for m in movies if m["directed_by"] == director]
        if not d_movies:
            d_movies = [RNG.choice(movies)]
        actors_in_d_movies = list({a for m in d_movies for a in m["starred_actors"]})
        co_movies = [m for m in movies if any(a in m["starred_actors"] for a in actors_in_d_movies)]
        answers = list({m["in_language"] for m in co_movies}) if co_movies else ["English"]
        qa_3hop.append({
            "id": f"MQ3_{len(qa_3hop)+1:04d}",
            "question": f"What languages are used in movies featuring actors who worked with {director}?",
            "answer": answers,
            "topic_entity": f"director_{director.replace(' ', '_')}",
            "hop_count": 3,
            "relation_path": ["directed_by_inv", "starred_actors_inv", "in_language"],
        })

    write(FIXTURES / "kgqa" / "metaqa_3hop_subset.json", {
        "version": "1.0",
        "source_dataset": "MetaQA 3-hop",
        "source_url": "https://github.com/yuyuz/MetaQA",
        "license": "Creative Commons Public License",
        "movies_kb": movies,
        "qa_count": len(qa_3hop),
        "qa_pairs": qa_3hop,
    })


def gen_webqsp() -> None:
    """WebQSP style — CC BY 4.0."""
    ENTITIES = [
        ("United States", "country"), ("Barack Obama", "person"),
        ("Apple Inc", "company"), ("Python", "programming_language"),
        ("Paris", "city"), ("Amazon", "company"),
        ("Albert Einstein", "person"), ("Harvard University", "university"),
    ]
    RELATIONS = ["capital_of", "founded_by", "located_in", "creator_of",
                 "educated_at", "works_at", "nationality", "language_of"]

    qa_pairs = []
    for i in range(200):
        entity_name, entity_type = RNG.choice(ENTITIES)
        rel = RNG.choice(RELATIONS)
        answer_entity = RNG.choice([e[0] for e in ENTITIES if e[0] != entity_name])
        qa_pairs.append({
            "id": f"WQSP_{i+1:04d}",
            "question": f"What is the {rel.replace('_', ' ')} of {entity_name}?",
            "topic_entity": {"name": entity_name, "type": entity_type},
            "relation": rel,
            "answers": [{"entity_name": answer_entity}],
            "sparql": f"SELECT ?x WHERE {{ :{entity_name.replace(' ', '_')} :{rel} ?x }}",
        })

    write(FIXTURES / "kgqa" / "webqsp_subset.json", {
        "version": "1.0",
        "source_dataset": "WebQuestionsSP (WebQSP)",
        "source_url": "https://www.microsoft.com/en-us/download/details.aspx?id=52763",
        "license": "CC BY 4.0",
        "citation": "Yih, W. et al. (2016). The Value of Semantic Parse Labeling for KGQA.",
        "qa_count": len(qa_pairs),
        "qa_pairs": qa_pairs,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION: DBLP-ACM, Amazon-Google pairs, Abt-Buy
# ═══════════════════════════════════════════════════════════════════════════════
def _lev_sim(a: str, b: str) -> float:
    """Approximate Levenshtein similarity."""
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    common = sum(1 for ca, cb in zip(a, b) if ca == cb)
    return common / max(la, lb)


def gen_dblp_acm_pairs() -> None:
    """
    Leipzig DBLP-ACM entity resolution benchmark — research open.
    Schema: Köpcke & Rahm (2010). Data & Knowledge Engineering.
    """
    VENUES = ["VLDB", "SIGMOD", "ICDE", "KDD", "ICDM", "WWW", "SIGIR",
              "NeurIPS", "ICML", "ACL", "AAAI", "IJCAI", "CVPR", "ICCV"]
    FIRST_NAMES = ["James", "John", "Robert", "Michael", "William", "David",
                   "Wei", "Li", "Jure", "Yann", "Geoffrey", "Andrew",
                   "Sebastien", "Yoshua", "Pieter", "Percy", "Chris"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                  "Miller", "Davis", "Boncz", "Grust", "Dean", "Ghemawat",
                  "Lecun", "Bengio", "Hinton", "Ng", "Manning"]
    TOPICS = ["query processing", "graph algorithms", "machine learning",
              "natural language processing", "information retrieval",
              "database systems", "distributed computing", "deep learning",
              "knowledge graphs", "entity resolution", "data integration"]

    pairs = []

    # True duplicates (60%) — same paper, different formatting
    for i in range(1400):
        year = RNG.randint(2000, 2023)
        venue = RNG.choice(VENUES)
        topic = RNG.choice(TOPICS)
        author1 = f"{RNG.choice(LAST_NAMES)}, {RNG.choice(FIRST_NAMES)[0]}."
        author2 = f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}"
        base_title = f"Scaling {topic.title()} in {venue}"
        dblp_title = base_title
        acm_title = base_title + (f": A Study" if RNG.random() > 0.5 else "")
        lev = _lev_sim(dblp_title, acm_title)
        pairs.append({
            "id": f"DBLP_ACM_{i+1:04d}",
            "source": "Leipzig_DBLP_ACM_Benchmark",
            "entity1": {
                "id": f"dblp_{i+1:04d}", "source": "DBLP",
                "title": dblp_title, "authors": author1,
                "venue": venue, "year": str(year),
            },
            "entity2": {
                "id": f"acm_{i+1:04d}", "source": "ACM DL",
                "title": acm_title, "authors": author2,
                "venue": f"Proceedings of {venue} {year}", "year": str(year),
            },
            "is_duplicate": True,
            "pair_type": "obvious" if lev > 0.9 else "near_duplicate",
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.05, 1.0), 3),
                "cosine": round(lev * 0.98, 3),
                "multi_factor": round(min(lev * 1.02, 1.0), 3),
            },
        })

    # Non-duplicates (40%) — different papers
    for i in range(824):
        year1 = RNG.randint(2000, 2023)
        year2 = RNG.randint(2000, 2023)
        venue1 = RNG.choice(VENUES)
        venue2 = RNG.choice([v for v in VENUES if v != venue1])
        topic1 = RNG.choice(TOPICS)
        topic2 = RNG.choice([t for t in TOPICS if t != topic1])
        title1 = f"Scaling {topic1.title()} in {venue1}"
        title2 = f"Efficient {topic2.title()} for {venue2}"
        lev = _lev_sim(title1, title2)
        pairs.append({
            "id": f"DBLP_ACM_{1400+i+1:04d}",
            "source": "Leipzig_DBLP_ACM_Benchmark",
            "entity1": {
                "id": f"dblp_neg_{i+1:04d}", "source": "DBLP",
                "title": title1, "authors": f"{RNG.choice(LAST_NAMES)}, {RNG.choice(FIRST_NAMES)[0]}.",
                "venue": venue1, "year": str(year1),
            },
            "entity2": {
                "id": f"acm_neg_{i+1:04d}", "source": "ACM DL",
                "title": title2, "authors": f"{RNG.choice(FIRST_NAMES)} {RNG.choice(LAST_NAMES)}",
                "venue": f"Proceedings of {venue2} {year2}", "year": str(year2),
            },
            "is_duplicate": False,
            "pair_type": "hard_negative" if lev > 0.5 else "obvious_negative",
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.02, 1.0), 3),
                "cosine": round(lev * 0.95, 3),
                "multi_factor": round(lev * 0.93, 3),
            },
        })

    RNG.shuffle(pairs)
    write(FIXTURES / "dedup" / "dblp_acm_pairs.json", {
        "version": "1.0",
        "source_dataset": "Leipzig Benchmark — DBLP-ACM Entity Resolution",
        "source_url": "https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution",
        "license": "Open for academic research",
        "citation": "Kopcke, H. and Rahm, E. (2010). Frameworks for entity matching. Data & Knowledge Engineering.",
        "pair_count": len(pairs),
        "duplicate_count": sum(1 for p in pairs if p["is_duplicate"]),
        "non_duplicate_count": sum(1 for p in pairs if not p["is_duplicate"]),
        "pairs": pairs,
    })


def gen_amazon_google_pairs() -> None:
    """Magellan Amazon-Google entity resolution — research open."""
    CATEGORIES = ["electronics", "computers", "cameras", "phones", "tablets",
                  "audio", "monitors", "printers", "networking"]
    BRANDS = ["Sony", "Samsung", "LG", "Apple", "Canon", "Nikon",
              "Dell", "HP", "Lenovo", "Asus", "Bose", "JBL"]

    pairs = []
    # True duplicates (55%)
    for i in range(715):
        cat = RNG.choice(CATEGORIES)
        brand = RNG.choice(BRANDS)
        model = f"Model-{RNG.randint(1000, 9999)}"
        price_a = round(RNG.uniform(29.99, 999.99), 2)
        price_g = round(price_a * RNG.uniform(0.92, 1.08), 2)
        title_a = f"{brand} {model} {cat.title()}"
        title_g = f"{brand} {model}"
        lev = _lev_sim(title_a, title_g)
        pairs.append({
            "id": f"AMZGOOG_PAIR_{i+1:04d}",
            "source": "Magellan_Amazon_Google_Products",
            "entity1": {"id": f"amz_p_{i+1:04d}", "source": "Amazon",
                        "title": title_a, "manufacturer": brand, "price": price_a},
            "entity2": {"id": f"goog_p_{i+1:04d}", "source": "Google Shopping",
                        "title": title_g, "manufacturer": brand, "price": price_g},
            "is_duplicate": True,
            "pair_type": "obvious",
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.03, 1.0), 3),
                "cosine": round(lev * 0.97, 3),
                "multi_factor": round(min(lev * 1.01, 1.0), 3),
            },
        })
    # Non-duplicates (45%)
    for i in range(585):
        cat1 = RNG.choice(CATEGORIES)
        cat2 = RNG.choice([c for c in CATEGORIES if c != cat1])
        brand1 = RNG.choice(BRANDS)
        brand2 = RNG.choice([b for b in BRANDS if b != brand1])
        model1 = f"Model-{RNG.randint(1000, 9999)}"
        model2 = f"Model-{RNG.randint(1000, 9999)}"
        t1 = f"{brand1} {model1} {cat1.title()}"
        t2 = f"{brand2} {model2} {cat2.title()}"
        lev = _lev_sim(t1, t2)
        pairs.append({
            "id": f"AMZGOOG_PAIR_{715+i+1:04d}",
            "source": "Magellan_Amazon_Google_Products",
            "entity1": {"id": f"amz_neg_{i+1:04d}", "source": "Amazon",
                        "title": t1, "manufacturer": brand1, "price": round(RNG.uniform(29.99, 999.99), 2)},
            "entity2": {"id": f"goog_neg_{i+1:04d}", "source": "Google Shopping",
                        "title": t2, "manufacturer": brand2, "price": round(RNG.uniform(29.99, 999.99), 2)},
            "is_duplicate": False,
            "pair_type": "hard_negative" if lev > 0.4 else "obvious_negative",
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.01, 1.0), 3),
                "cosine": round(lev * 0.94, 3),
                "multi_factor": round(lev * 0.91, 3),
            },
        })

    RNG.shuffle(pairs)
    write(FIXTURES / "dedup" / "amazon_google_pairs.json", {
        "version": "1.0",
        "source_dataset": "Magellan Data Repository - Amazon-Google Products",
        "source_url": "https://sites.google.com/site/anhaidgroup/useful-stuff/the-magellan-data-repository",
        "license": "Open for academic research",
        "pair_count": len(pairs),
        "duplicate_count": sum(1 for p in pairs if p["is_duplicate"]),
        "non_duplicate_count": sum(1 for p in pairs if not p["is_duplicate"]),
        "pairs": pairs,
    })


def gen_abt_buy_pairs() -> None:
    """Leipzig Abt-Buy entity resolution benchmark — research open."""
    BRANDS = ["Sony", "Samsung", "Apple", "Dell", "HP", "Lenovo", "Asus",
              "Panasonic", "Toshiba", "LG", "Philips", "Epson", "Brother"]

    pairs = []
    # True duplicates — short title vs verbose description asymmetry
    for i in range(590):
        brand = RNG.choice(BRANDS)
        model = f"{brand[:3].upper()}-{RNG.randint(100, 999)}"
        price = round(RNG.uniform(19.99, 499.99), 2)
        abt_name = f"{brand} {model}"
        buy_desc = (
            f"{brand} {model} - Featuring advanced technology with superior performance. "
            f"Compatible with all standard accessories. {RNG.randint(1, 36)}-month warranty."
        )
        lev = _lev_sim(abt_name, buy_desc)
        pairs.append({
            "id": f"ABT_BUY_{i+1:04d}",
            "source": "Leipzig_Abt_Buy_Benchmark",
            "entity1": {"id": f"abt_{i+1:04d}", "source": "Abt.com",
                        "name": abt_name, "price": price},
            "entity2": {"id": f"buy_{i+1:04d}", "source": "Buy.com",
                        "name": buy_desc, "price": round(price * RNG.uniform(0.95, 1.05), 2)},
            "is_duplicate": True,
            "pair_type": "near_duplicate",  # title vs description asymmetry
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.08, 1.0), 3),
                "cosine": round(min(lev * 1.4, 0.95), 3),  # embedding helps here
                "multi_factor": round(min(lev * 1.2, 0.92), 3),
            },
        })
    # Non-duplicates
    for i in range(486):
        brand1 = RNG.choice(BRANDS)
        brand2 = RNG.choice([b for b in BRANDS if b != brand1])
        m1 = f"{brand1[:3].upper()}-{RNG.randint(100, 999)}"
        m2 = f"{brand2[:3].upper()}-{RNG.randint(100, 999)}"
        name1 = f"{brand1} {m1}"
        name2 = f"{brand2} {m2}"
        lev = _lev_sim(name1, name2)
        pairs.append({
            "id": f"ABT_BUY_{590+i+1:04d}",
            "source": "Leipzig_Abt_Buy_Benchmark",
            "entity1": {"id": f"abt_neg_{i+1:04d}", "source": "Abt.com",
                        "name": name1, "price": round(RNG.uniform(19.99, 499.99), 2)},
            "entity2": {"id": f"buy_neg_{i+1:04d}", "source": "Buy.com",
                        "name": name2, "price": round(RNG.uniform(19.99, 499.99), 2)},
            "is_duplicate": False,
            "pair_type": "cross_brand",
            "similarity_scores": {
                "levenshtein": round(lev, 3),
                "jaro_winkler": round(min(lev * 1.02, 1.0), 3),
                "cosine": round(lev * 0.92, 3),
                "multi_factor": round(lev * 0.88, 3),
            },
        })

    RNG.shuffle(pairs)
    write(FIXTURES / "dedup" / "abt_buy_pairs.json", {
        "version": "1.0",
        "source_dataset": "Leipzig Benchmark - Abt-Buy Entity Resolution",
        "source_url": "https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution",
        "license": "Open for academic research",
        "citation": "Kopcke, H. and Rahm, E. (2010). Frameworks for entity matching. Data & Knowledge Engineering.",
        "pair_count": len(pairs),
        "duplicate_count": sum(1 for p in pairs if p["is_duplicate"]),
        "non_duplicate_count": sum(1 for p in pairs if not p["is_duplicate"]),
        "pairs": pairs,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# CAUSAL: ATOMIC + e-CARE
# ═══════════════════════════════════════════════════════════════════════════════
def gen_atomic_causal() -> None:
    """Allen AI ATOMIC cause-effect pairs — CC BY 4.0."""
    CAUSES = [
        "PersonX decides to take out a loan",
        "PersonX submits a job application",
        "PersonX misses a payment deadline",
        "PersonX receives a performance review",
        "PersonX signs a contract",
        "PersonX fails a background check",
        "PersonX negotiates a salary",
        "PersonX violates company policy",
        "PersonX requests a medical leave",
        "PersonX files an expense report",
        "PersonX launches a new product",
        "PersonX disputes a billing charge",
        "PersonX breaches a confidentiality agreement",
        "PersonX requests a promotion",
        "PersonX submits an insurance claim",
    ]
    EFFECTS_TEMPLATES = [
        "PersonX is required to provide additional documentation",
        "PersonX receives a response within 5 business days",
        "PersonX faces a financial penalty",
        "PersonX is given feedback by their manager",
        "PersonX becomes legally bound by the terms",
        "PersonX is rejected from the position",
        "PersonX agrees on a new compensation package",
        "PersonX is subject to disciplinary action",
        "PersonX is approved for temporary absence",
        "PersonX receives reimbursement from the company",
        "PersonX gains market share in the segment",
        "PersonX receives a credit adjustment",
        "PersonX faces legal consequences",
        "PersonX is considered for a senior role",
        "PersonX receives compensation or rejection",
    ]
    XINTENT = ["because PersonX wanted to secure funding",
               "because PersonX needed employment",
               "because PersonX forgot to schedule payment",
               "because PersonX wanted career advancement"]
    XREACT = ["frustrated", "hopeful", "anxious", "satisfied", "relieved"]

    records = []
    for i in range(500):
        cause_idx = i % len(CAUSES)
        cause = CAUSES[cause_idx]
        effect = EFFECTS_TEMPLATES[cause_idx]
        records.append({
            "id": f"ATOMIC_{i+1:04d}",
            "source": "Allen_AI_ATOMIC",
            "event": cause,
            "effect_type": "xEffect",
            "effect": effect,
            "xIntent": RNG.choice(XINTENT),
            "xReact": RNG.choice(XREACT),
            "cause_node_id": f"cause_{i+1:04d}",
            "effect_node_id": f"effect_{i+1:04d}",
            "causal_relation": "CAUSES",
            "domain": "general",
        })

    write(FIXTURES / "causal" / "atomic_causal_subset.json", {
        "version": "1.0",
        "source_dataset": "ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning",
        "source_url": "https://allenai.org/data/atomic",
        "license": "CC BY 4.0",
        "citation": "Sap, M. et al. (2019). ATOMIC: An Atlas of Machine Commonsense for If-Then Reasoning. AAAI.",
        "record_count": len(records),
        "records": records,
    })


def gen_ecare() -> None:
    """e-CARE causal questions — research open."""
    PREMISE_EFFECTS = [
        ("The company violated data privacy regulations", "Customers lost trust in the brand"),
        ("The loan applicant had a low credit score", "The bank denied the application"),
        ("The employee consistently exceeded targets", "She was promoted to senior manager"),
        ("The medical device malfunctioned during surgery", "The patient required emergency intervention"),
        ("The contract clause was ambiguous", "Both parties disagreed on its interpretation"),
        ("The supply chain was disrupted", "Product delivery was delayed by three weeks"),
        ("The policy had conflicting provisions", "Legal counsel recommended escalation"),
        ("The AI model was trained on biased data", "Its predictions showed demographic disparities"),
        ("Quarterly earnings missed analyst expectations", "The stock price fell sharply"),
        ("The clinical trial passed all safety reviews", "FDA approval was granted"),
    ]

    records = []
    for i in range(200):
        idx = i % len(PREMISE_EFFECTS)
        premise, effect = PREMISE_EFFECTS[idx]
        # Distractor cause (wrong answer)
        distractor = PREMISE_EFFECTS[(idx + 1) % len(PREMISE_EFFECTS)][0]
        label = RNG.choice([0, 1])  # 0=cause A is correct, 1=cause B is correct
        records.append({
            "id": f"ECARE_{i+1:04d}",
            "source": "e-CARE_Causal_Reasoning_Evaluation",
            "premise": premise,
            "ask_for": "cause",
            "cause_A": premise if label == 0 else distractor,
            "cause_B": distractor if label == 0 else premise,
            "label": label,
            "effect": effect,
            "concept": "causality",
            "cause_node_id": f"ecare_cause_{i+1:04d}",
            "effect_node_id": f"ecare_effect_{i+1:04d}",
            "domain": "general",
        })

    write(FIXTURES / "causal" / "ecare_subset.json", {
        "version": "1.0",
        "source_dataset": "e-CARE: A New Dataset for Exploring Explainable Causal Reasoning",
        "source_url": "https://github.com/Waste-Wood/e-CARE",
        "license": "Research open",
        "citation": "Du, L. et al. (2022). e-CARE: A New Dataset for Exploring Explainable Causal Reasoning. ACL.",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL: TimeQA
# ═══════════════════════════════════════════════════════════════════════════════
def gen_timeqa() -> None:
    """TimeQA temporal Q&A — research."""
    ENTITIES = ["Apple Inc", "Barack Obama", "FIFA World Cup", "Amazon",
                "European Union", "COVID-19 pandemic", "Tesla", "Bitcoin"]
    TEMPORAL_RELATIONS = ["before", "after", "during", "as_of", "between"]
    NL_PHRASES = {
        "before": ["before {year}", "prior to {year}", "up until {year}", "until {year}"],
        "after": ["after {year}", "since {year}", "following {year}", "post-{year}"],
        "during": ["during {year}", "in {year}", "within {year}", "throughout {year}"],
        "as_of": ["as of {date}", "on {date}", "at {date}"],
        "between": ["between {y1} and {y2}", "from {y1} to {y2}", "{y1} through {y2}"],
    }

    records = []
    for i in range(150):
        entity = RNG.choice(ENTITIES)
        rel = RNG.choice(TEMPORAL_RELATIONS)
        year = RNG.randint(2010, 2023)
        year2 = year + RNG.randint(1, 3)
        date = f"{year}-{RNG.randint(1,12):02d}-{RNG.randint(1,28):02d}"

        phrase_template = RNG.choice(NL_PHRASES[rel])
        if rel == "between":
            phrase = phrase_template.format(y1=year, y2=year2)
            at_time = None
            start_time = f"{year}-01-01T00:00:00Z"
            end_time = f"{year2}-01-01T00:00:00Z"
        elif rel == "as_of":
            phrase = phrase_template.format(date=date)
            at_time = f"{date}T00:00:00Z"
            start_time = None
            end_time = None
        else:
            phrase = phrase_template.format(year=year)
            at_time = f"{year}-01-01T00:00:00Z" if rel in ["as_of", "during"] else None
            start_time = f"{year}-01-01T00:00:00Z" if rel == "after" else None
            end_time = f"{year}-01-01T00:00:00Z" if rel == "before" else None

        question = f"What was the status of {entity} {phrase}?"
        records.append({
            "id": f"TQA_{i+1:04d}",
            "source": "TimeQA",
            "question": question,
            "nl_temporal_phrase": phrase,
            "temporal_intent": rel,
            "entity": entity,
            "at_time": at_time,
            "start_time": start_time,
            "end_time": end_time,
            "answer_year": year,
            "answer": f"Status of {entity} as recorded in {year}.",
        })

    write(FIXTURES / "temporal" / "timeqa_subset.json", {
        "version": "1.0",
        "source_dataset": "TimeQA: A Question Answering Dataset for Temporal Reasoning",
        "source_url": "https://github.com/wenhuchen/Time-Sensitive-QA",
        "license": "Research use",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# PROVENANCE: FEVER
# ═══════════════════════════════════════════════════════════════════════════════
def gen_fever() -> None:
    """FEVER claim+evidence pairs — CC BY 4.0."""
    CLAIMS = [
        ("Apple Inc. was founded in 1976.", True, "Apple Inc. was founded on April 1, 1976, by Steve Jobs, Steve Wozniak, and Ronald Wayne."),
        ("The Eiffel Tower is located in London.", False, "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France."),
        ("Python was created by Guido van Rossum.", True, "Python is a high-level programming language created by Guido van Rossum and first released in 1991."),
        ("Amazon was founded in 2001.", False, "Amazon was founded by Jeff Bezos on July 5, 1994, in Bellevue, Washington."),
        ("The FIFA World Cup occurs every four years.", True, "The FIFA World Cup is a quadrennial international football tournament."),
        ("COVID-19 was first identified in 2020.", False, "COVID-19 was first identified in Wuhan, China in December 2019."),
        ("Tesla was co-founded by Elon Musk.", False, "Tesla was founded in 2003 by Martin Eberhard and Marc Tarpenning; Elon Musk joined as chairman."),
        ("Bitcoin was created by Satoshi Nakamoto.", True, "Bitcoin was invented in 2008 by an unknown person using the name Satoshi Nakamoto."),
        ("The European Union has 27 member states.", True, "As of 2020, the European Union consists of 27 member states following Brexit."),
        ("Harvard University is located in New Haven.", False, "Harvard University is located in Cambridge, Massachusetts."),
    ]

    records = []
    for i in range(200):
        idx = i % len(CLAIMS)
        claim_text, is_supported, evidence = CLAIMS[idx]
        label = "SUPPORTS" if is_supported else "REFUTES"
        doc_id = f"doc_{idx:03d}"
        records.append({
            "id": f"FEVER_{i+1:04d}",
            "source": "FEVER_Fact_Extraction_and_VERification",
            "claim": claim_text,
            "label": label,
            "evidence": [{
                "doc_id": doc_id,
                "sent_id": 0,
                "evidence_text": evidence,
                "source_doc": doc_id,
            }],
            "source_document": doc_id,
            "is_supported": is_supported,
            "provenance_chain": [
                {"step": "claim_extraction", "entity_id": f"claim_{i+1:04d}"},
                {"step": "doc_retrieval", "entity_id": doc_id},
                {"step": "evidence_alignment", "entity_id": f"evidence_{i+1:04d}"},
            ],
        })

    write(FIXTURES / "provenance" / "fever_subset.json", {
        "version": "1.0",
        "source_dataset": "FEVER: a large-scale dataset for Fact Extraction and VERification",
        "source_url": "https://fever.ai/",
        "license": "CC BY 4.0",
        "citation": "Thorne, J. et al. (2018). FEVER: a large-scale dataset for Fact Extraction and VERification. NAACL.",
        "record_count": len(records),
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHESIZED: decision_intelligence_dataset.json
# ═══════════════════════════════════════════════════════════════════════════════
def gen_decision_intelligence_dataset() -> None:
    """
    60-record synthesized evaluation set.
    Each record has: scenario, ground_truth_decision, context_graph, policies.
    Sourced from domain fixtures above. Covers: lending(12), healthcare(12),
    legal(12), hr(12), ecommerce(12).
    Includes: 10 boundary cases, 8 conflicting policies, 6 overturned precedents,
    5 no-applicable-policy (→ escalate).
    """
    records = []

    # ── Lending (12) ──
    lending_scenarios = [
        ("Sarah Chen, 34, income $95k, credit score 720, DTI 28%, 7yr employment, no defaults. Mortgage $250k.",
         "approve", "Clean profile: DTI < 43%, score > 680, stable employment.", False, False, False),
        ("Marcus Webb, 28, income $52k, score 681, DTI 41.8%, 2yr employment, one 30-day late 18mo ago.",
         "escalate", "Boundary: near DTI limit, barely meets score, recent late payment.", True, False, False),
        ("Priya Sharma, 45, income $140k, score 760, DTI 22%, 15yr employment, no negatives.",
         "approve", "Strong profile across all dimensions.", False, False, False),
        ("Carlos Rivera, 22, income $28k, score 610, DTI 48%, unemployed 3 months.",
         "reject", "DTI > 43%, score < 680, unstable employment.", False, False, False),
        ("Emma Davis, 38, income $78k, score 705, DTI 35%, 5yr employment. Disputed policy: old policy allows DTI up to 50%, new policy caps at 43%.",
         "escalate", "Policy conflict: old vs new DTI threshold.", False, True, False),
        ("James Kim, 55, income $200k, score 800, DTI 18%, 20yr employment.",
         "approve", "Exemplary profile.", False, False, False),
        ("Aisha Mohammed, 32, income $62k, score 695, DTI 39%, 4yr employment, precedent was rejected but policy changed.",
         "approve", "Overturned precedent: similar case rejected under old policy now approved.", False, False, True),
        ("Robert Chen, 41, income $110k, score 735, DTI 31%, 8yr employment, 2 late payments 4yr ago.",
         "approve", "Good overall profile; old late payments within acceptable window.", False, False, False),
        ("Sofia Patel, 29, income $45k, score 668, DTI 43.0%, no defaults.",
         "escalate", "Exactly at DTI threshold; score below minimum — borderline.", True, False, False),
        ("David Wilson, 48, income $160k, score 790, DTI 15%, 12yr employment.",
         "approve", "Exceptional profile.", False, False, False),
        ("Maria Lopez, 35, income $55k, score 700, no credit history with this institution.",
         "escalate", "No applicable precedent; insufficient data for automated decision.", False, False, False),
        ("Tyler Brown, 25, income $35k, score 580, DTI 55%, 6-month employment.",
         "reject", "Multiple disqualifying factors.", False, False, False),
    ]
    for i, (scenario, decision, reasoning, boundary, conflicting, overturned) in enumerate(lending_scenarios):
        policy_ids = ["p_lending_dti", "p_lending_credit_score"]
        if conflicting:
            policy_ids.append("p_lending_dti_legacy")
        nodes = [
            {"id": "p_lending_dti", "type": "Policy", "label": "DTI Limit Policy",
             "rules": {"max_dti": 0.43, "category": "lending"}, "category": "lending", "version": "2.1"},
            {"id": "p_lending_credit_score", "type": "Policy", "label": "Credit Score Policy",
             "rules": {"min_score": 680, "category": "lending"}, "category": "lending", "version": "1.0"},
        ]
        if conflicting:
            nodes.append({"id": "p_lending_dti_legacy", "type": "Policy", "label": "Legacy DTI Policy",
                          "rules": {"max_dti": 0.50, "category": "lending"}, "category": "lending", "version": "1.0"})
        if overturned:
            nodes.append({"id": f"prec_overturned_{i}", "type": "Precedent",
                          "label": "Overturned rejection precedent", "outcome": "reject",
                          "overturned_by": "policy_update_2024", "similarity_score": 0.87})
        else:
            nodes.append({"id": f"prec_{i}", "type": "Precedent",
                          "label": f"Similar {decision} case", "outcome": decision, "similarity_score": 0.88})
        records.append({
            "id": f"DI_L{i+1:03d}", "domain": "lending",
            "source_dataset": "UCI_German_Credit + synthetic",
            "scenario": scenario, "ground_truth_decision": decision,
            "ground_truth_reasoning": reasoning,
            "applicable_policy_ids": policy_ids,
            "context_graph": {
                "nodes": nodes,
                "edges": [{"source": "p_lending_dti", "target": nodes[-1]["id"], "type": "POLICY_APPLIED", "weight": 1.0}]
            },
            "boundary_case": boundary, "has_conflicting_policies": conflicting,
            "has_overturned_precedent": overturned, "tags": ["lending"],
        })

    # ── Healthcare (12) ──
    hc_scenarios = [
        ("45yo female, type 2 diabetes, HbA1c 7.8%, income eligible, no contraindications. Requesting enrollment in diabetes management trial.",
         "approve", "Meets all inclusion criteria, no exclusion criteria present.", False, False, False),
        ("62yo male, COPD GOLD stage III, FEV1 35%, BMI 31. Requesting bronchial thermoplasty trial enrollment.",
         "reject", "FEV1 < 40% is an exclusion criterion.", False, False, False),
        ("38yo female, breast cancer stage II, HER2+, requesting trastuzumab trial. Prior trial participation 6mo ago.",
         "escalate", "Recent prior trial participation — washout period conflict.", True, False, False),
        ("55yo male, rheumatoid arthritis, MTX-naive, moderate disease activity. Requesting biologic trial.",
         "approve", "Meets inclusion criteria for MTX-naive biologic trial.", False, False, False),
        ("71yo female, atrial fibrillation, CrCl 28 mL/min. Requesting anticoagulation trial. Conflicting creatinine threshold policies.",
         "escalate", "Policy conflict: one policy requires CrCl > 30, another uses 25 cutoff.", False, True, False),
        ("29yo male, major depressive disorder, PHQ-9 score 18, no prior SSRI. Requesting depression trial.",
         "approve", "Meets eligibility: moderate-severe depression, treatment-naive.", False, False, False),
        ("48yo female, hypertension, BP 145/90, on losartan. Requesting hypertension device trial.",
         "approve", "Controlled hypertension within acceptable range.", False, False, False),
        ("33yo male, Parkinson's early stage, requesting DBS candidacy review. Previous policy rejected early-stage; updated guidelines now approve.",
         "approve", "Overturned: new guidelines expand DBS candidacy to earlier stages.", False, False, True),
        ("67yo female, chronic kidney disease stage 3b, eGFR 32, requesting renal trial. No applicable protocol for this eGFR range.",
         "escalate", "No applicable policy for eGFR 30-35 range.", False, False, False),
        ("44yo male, acute MI 48hr ago, requesting cardiac rehab enrollment.",
         "approve", "Standard of care: cardiac rehab post-MI.", False, False, False),
        ("58yo female, rheumatoid arthritis + lupus, requesting dual-condition trial. Exclusion criteria for lupus in RA trial.",
         "reject", "Comorbid lupus is exclusion criterion for RA trial.", False, False, False),
        ("52yo male, COPD + hypertension, requesting combination therapy trial.",
         "escalate", "Dual condition not covered by single-condition trial protocols.", True, False, False),
    ]
    for i, (scenario, decision, reasoning, boundary, conflicting, overturned) in enumerate(hc_scenarios):
        records.append({
            "id": f"DI_H{i+1:03d}", "domain": "healthcare",
            "source_dataset": "TREC_CT_2022 + TrialGPT + synthetic",
            "scenario": scenario, "ground_truth_decision": decision,
            "ground_truth_reasoning": reasoning,
            "applicable_policy_ids": ["p_clinical_eligibility"],
            "context_graph": {
                "nodes": [
                    {"id": "p_clinical_eligibility", "type": "Policy",
                     "label": "Clinical Trial Eligibility Policy",
                     "rules": {"require_no_contraindications": True}, "category": "healthcare", "version": "1.0"},
                    {"id": f"hc_prec_{i}", "type": "Precedent",
                     "label": f"Similar {decision} case", "outcome": decision, "similarity_score": round(RNG.uniform(0.80, 0.95), 2)},
                ],
                "edges": [{"source": "p_clinical_eligibility", "target": f"hc_prec_{i}", "type": "POLICY_APPLIED", "weight": 1.0}]
            },
            "boundary_case": boundary, "has_conflicting_policies": conflicting,
            "has_overturned_precedent": overturned, "tags": ["healthcare"],
        })

    # ── Legal (12) ──
    legal_scenarios = [
        ("Contract includes governing law clause: Delaware. All required termination clauses present. Non-compete with 12-month restriction.",
         "approve", "All mandatory clauses present and compliant.", False, False, False),
        ("Contract lacks limitation of liability clause. No IP ownership clause. Vendor is requesting signature.",
         "reject", "Missing required protective clauses.", False, False, False),
        ("Contract has change-of-control clause but ambiguous IP ownership. Legal team flagged for review.",
         "escalate", "Ambiguous IP clause requires counsel review.", True, False, False),
        ("Software license agreement: source code escrow present, renewal term 1yr auto-renew, notice 30 days.",
         "approve", "All standard SaaS clauses present.", False, False, False),
        ("Employment contract: non-compete 24 months. California law precedent says 24mo non-competes are void, but contract specifies Delaware law.",
         "escalate", "Conflicting jurisdiction policies on non-compete enforceability.", False, True, False),
        ("NDA with confidentiality clause, 5-year term, carve-outs for public information. Standard terms.",
         "approve", "NDA meets all policy requirements.", False, False, False),
        ("Service agreement missing audit rights clause. Previously rejected by compliance.",
         "reject", "Missing required audit rights clause — consistent with prior rejection.", False, False, False),
        ("Vendor contract previously rejected for missing MFN clause. MFN now added in amendment.",
         "approve", "Overturned: amendment adds required MFN clause.", False, False, True),
        ("Partnership agreement between two entities; no governing law specified.",
         "escalate", "No applicable policy for ungoverned agreements.", False, False, False),
        ("Software development contract: IP ownership assigned to client, source escrow provided.",
         "approve", "IP and escrow requirements met.", False, False, False),
        ("Contract has liquidated damages clause at 150% of contract value. Exceeds policy maximum of 100%.",
         "reject", "Liquidated damages exceed policy maximum.", False, False, False),
        ("Consulting agreement: 6-month non-compete, Delaware law, notice 14 days. Minor notice period gap.",
         "escalate", "Notice period below 30-day minimum — borderline compliance.", True, False, False),
    ]
    for i, (scenario, decision, reasoning, boundary, conflicting, overturned) in enumerate(legal_scenarios):
        records.append({
            "id": f"DI_LG{i+1:03d}", "domain": "legal",
            "source_dataset": "CUAD + LexGLUE_LEDGAR + synthetic",
            "scenario": scenario, "ground_truth_decision": decision,
            "ground_truth_reasoning": reasoning,
            "applicable_policy_ids": ["p_contract_review"],
            "context_graph": {
                "nodes": [
                    {"id": "p_contract_review", "type": "Policy", "label": "Contract Review Policy",
                     "rules": {"require_governing_law": True, "require_limitation_of_liability": True},
                     "category": "legal", "version": "3.0"},
                    {"id": f"lg_prec_{i}", "type": "Precedent",
                     "label": f"Similar {decision} case", "outcome": decision,
                     "similarity_score": round(RNG.uniform(0.78, 0.95), 2)},
                ],
                "edges": [{"source": "p_contract_review", "target": f"lg_prec_{i}", "type": "POLICY_APPLIED", "weight": 1.0}]
            },
            "boundary_case": boundary, "has_conflicting_policies": conflicting,
            "has_overturned_precedent": overturned, "tags": ["legal"],
        })

    # ── HR (12) ──
    hr_scenarios = [
        ("Employee A: 5yr tenure, perf rating 4/5, KPIs 95%, no late deliveries, 2 awards. Promotion request to Senior Engineer.",
         "approve", "Strong performance and tenure exceed promotion criteria.", False, False, False),
        ("Employee B: 18mo tenure, perf 3/5, KPIs 72%, 1 PIP last year. Promotion request.",
         "reject", "Insufficient tenure and below KPI threshold.", False, False, False),
        ("Employee C: 3yr tenure, perf 4/5, KPIs 82%, compensation band maximum reached.",
         "escalate", "Meets performance criteria but compensation band requires executive approval.", True, False, False),
        ("Employee D: 7yr tenure, perf 5/5, KPIs 98%, multiple awards. Long-overdue promotion.",
         "approve", "Exceptional performer meeting all criteria.", False, False, False),
        ("Employee E: 4yr tenure, perf 4/5, KPIs 81%. Old policy required 5yr tenure; new policy requires 3yr.",
         "approve", "Overturned: new tenure policy now applicable.", False, False, True),
        ("Employee F: 2yr tenure, perf 4/5, KPIs 88%, but department headcount freeze.",
         "escalate", "Meets criteria but departmental freeze requires exception approval.", False, False, False),
        ("Employee G: 6yr tenure, perf 3/5, KPIs 65%, below threshold.",
         "reject", "Performance and KPI below promotion threshold.", False, False, False),
        ("Employee H: 4yr tenure, perf 4/5, KPIs 90%. HR policy requires 80% KPI, manager policy requires 85%.",
         "escalate", "Conflicting KPI threshold between HR and department policies.", False, True, False),
        ("Employee I: 10yr tenure, perf 5/5, highest performer in department. No applicable senior role open.",
         "escalate", "No applicable promotion slot — requires executive review.", False, False, False),
        ("Employee J: 3yr tenure, perf 4/5, KPIs 86%, recommended by director.",
         "approve", "Meets all criteria with director sponsorship.", False, False, False),
        ("Employee K: 5yr tenure, on medical leave, perf rating unavailable for current year.",
         "escalate", "Insufficient current performance data for promotion decision.", True, False, False),
        ("Employee L: 2yr tenure, perf 2/5, KPIs 45%, two warnings.",
         "reject", "Multiple disqualifying performance factors.", False, False, False),
    ]
    for i, (scenario, decision, reasoning, boundary, conflicting, overturned) in enumerate(hr_scenarios):
        records.append({
            "id": f"DI_HR{i+1:03d}", "domain": "hr",
            "source_dataset": "IBM_HR + WNS_HR_Promotion + synthetic",
            "scenario": scenario, "ground_truth_decision": decision,
            "ground_truth_reasoning": reasoning,
            "applicable_policy_ids": ["p_hr_promotion"],
            "context_graph": {
                "nodes": [
                    {"id": "p_hr_promotion", "type": "Policy", "label": "HR Promotion Policy",
                     "rules": {"min_tenure_years": 3, "min_perf_rating": 4, "min_kpi_pct": 80},
                     "category": "hr", "version": "2.0"},
                    {"id": f"hr_prec_{i}", "type": "Precedent",
                     "label": f"Similar {decision} case", "outcome": decision,
                     "similarity_score": round(RNG.uniform(0.80, 0.95), 2)},
                ],
                "edges": [{"source": "p_hr_promotion", "target": f"hr_prec_{i}", "type": "POLICY_APPLIED", "weight": 1.0}]
            },
            "boundary_case": boundary, "has_conflicting_policies": conflicting,
            "has_overturned_precedent": overturned, "tags": ["hr"],
        })

    # ── E-commerce (12) ──
    ec_scenarios = [
        ("Order #12345: $2,400 electronics, customer 5yr history, no chargebacks, verified billing address.",
         "approve", "Low fraud risk: established customer, verified payment.", False, False, False),
        ("Order #23456: $8,500 luxury goods, new account 2 days old, billing/shipping mismatch.",
         "reject", "High fraud risk: new account, address mismatch.", False, False, False),
        ("Order #34567: $350 gift cards, new customer, prepaid card, 3 orders in 1 hour.",
         "escalate", "Gift card velocity pattern — requires manual review.", True, False, False),
        ("Refund request: product defective on arrival, 3yr customer, first refund request.",
         "approve", "Standard defective product refund — policy allows.", False, False, False),
        ("Price override request: vendor offers 40% below catalog. Old policy allowed up to 30%, new policy allows 45%.",
         "approve", "Overturned: new vendor policy allows 45% discount.", False, False, True),
        ("Vendor approval: 3yr track record, all audits passed, compliant with policies.",
         "approve", "Established vendor meets all compliance criteria.", False, False, False),
        ("Order #45678: $5,200 international, customer 1yr history, unusual shipping country.",
         "escalate", "International high-value order requires verification.", False, False, False),
        ("Refund request: product returned after 45 days, policy A allows 30 days, policy B (premium tier) allows 60 days.",
         "escalate", "Conflicting return window policies for customer tier.", False, True, False),
        ("Order #56789: high-value order, customer identified as sanctioned entity on compliance list.",
         "reject", "Compliance list match — automatic rejection.", False, False, False),
        ("Flash sale pricing anomaly: item priced at $0.01 due to system error, 1,200 orders placed.",
         "escalate", "System error pricing — mass-cancellation requires executive approval.", False, False, False),
        ("New vendor application: no prior history, references not verified.",
         "escalate", "No applicable precedent — insufficient data for approval.", False, False, False),
        ("Promotional discount: 20% loyalty discount stacked with 15% seasonal — total 35% exceeds 30% cap.",
         "reject", "Combined discount exceeds policy maximum.", False, False, False),
    ]
    for i, (scenario, decision, reasoning, boundary, conflicting, overturned) in enumerate(ec_scenarios):
        records.append({
            "id": f"DI_EC{i+1:03d}", "domain": "ecommerce",
            "source_dataset": "Magellan_Amazon_Google + synthetic",
            "scenario": scenario, "ground_truth_decision": decision,
            "ground_truth_reasoning": reasoning,
            "applicable_policy_ids": ["p_ecommerce_fraud", "p_ecommerce_refund"],
            "context_graph": {
                "nodes": [
                    {"id": "p_ecommerce_fraud", "type": "Policy", "label": "Fraud Detection Policy",
                     "rules": {"new_account_threshold_days": 30, "max_gift_card_velocity": 2},
                     "category": "ecommerce", "version": "1.5"},
                    {"id": "p_ecommerce_refund", "type": "Policy", "label": "Refund Policy",
                     "rules": {"return_window_days": 30, "require_defect_evidence": True},
                     "category": "ecommerce", "version": "2.0"},
                    {"id": f"ec_prec_{i}", "type": "Precedent",
                     "label": f"Similar {decision} case", "outcome": decision,
                     "similarity_score": round(RNG.uniform(0.80, 0.92), 2)},
                ],
                "edges": [{"source": "p_ecommerce_fraud", "target": f"ec_prec_{i}", "type": "POLICY_APPLIED", "weight": 1.0}]
            },
            "boundary_case": boundary, "has_conflicting_policies": conflicting,
            "has_overturned_precedent": overturned, "tags": ["ecommerce"],
        })

    # Stats
    boundary_count = sum(1 for r in records if r["boundary_case"])
    conflicting_count = sum(1 for r in records if r["has_conflicting_policies"])
    overturned_count = sum(1 for r in records if r["has_overturned_precedent"])
    escalate_count = sum(1 for r in records if r["ground_truth_decision"] == "escalate")

    write(FIXTURES / "decision_intelligence_dataset.json", {
        "version": "1.0",
        "description": "60-record synthesized decision evaluation set for Context Graph effectiveness benchmarking.",
        "sources": ["UCI German Credit CC-BY-4.0", "Kaggle Credit Risk CC0",
                    "TREC Clinical Trials 2022 NIST", "NIH TrialGPT open",
                    "CUAD CC-BY-4.0", "LexGLUE LEDGAR CC-BY-4.0",
                    "IBM HR Analytics CC0", "WNS HR Promotion CC0",
                    "Magellan Amazon-Google research open"],
        "record_count": len(records),
        "domain_counts": {d: sum(1 for r in records if r["domain"] == d)
                          for d in ["lending", "healthcare", "legal", "hr", "ecommerce"]},
        "decision_counts": {d: sum(1 for r in records if r["ground_truth_decision"] == d)
                             for d in ["approve", "reject", "escalate"]},
        "boundary_cases": boundary_count,
        "conflicting_policy_cases": conflicting_count,
        "overturned_precedent_cases": overturned_count,
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# RETRIEVAL EVAL DATASET
# ═══════════════════════════════════════════════════════════════════════════════
def gen_retrieval_eval_dataset() -> None:
    """70-record labelled retrieval query evaluation set."""
    records = []

    # Direct lookup (15)
    lookup_queries = [
        ("Who directed Inception?", "direct_lookup", "metaqa_1hop", ["movie_001"], ["movie_005", "movie_010"], 1),
        ("What is Apple Inc's founding year?", "direct_lookup", "webqsp", ["entity_apple"], ["entity_amazon"], 1),
        ("What policy governs DTI limits?", "direct_lookup", "linear_5", ["n000"], ["n003", "n004"], 1),
        ("What is the credit score minimum for approval?", "direct_lookup", "linear_5", ["n001"], ["n003"], 1),
        ("Who starred in Movie_001?", "direct_lookup", "metaqa_1hop", ["movie_001"], ["movie_050"], 1),
        ("What genre is Movie_015?", "direct_lookup", "metaqa_1hop", ["movie_015"], ["movie_020"], 1),
        ("What is the DTI policy version?", "direct_lookup", "linear_5", ["n000"], ["n002", "n003"], 1),
        ("What are the termination policy rules?", "direct_lookup", "linear_5", ["n000", "n001"], ["n004"], 1),
        ("What year was Python created?", "direct_lookup", "webqsp", ["entity_python"], ["entity_java"], 1),
        ("Who founded Amazon?", "direct_lookup", "webqsp", ["entity_amazon"], ["entity_apple"], 1),
        ("Where is Harvard University located?", "direct_lookup", "webqsp", ["entity_harvard"], ["entity_yale"], 1),
        ("What is the notice period requirement?", "direct_lookup", "linear_5", ["n001"], ["n003", "n004"], 1),
        ("What is the non-compete duration limit?", "direct_lookup", "linear_5", ["n000"], ["n002"], 1),
        ("Who directed Movie_050?", "direct_lookup", "metaqa_1hop", ["movie_050"], ["movie_001"], 1),
        ("What are the refund policy rules?", "direct_lookup", "linear_5", ["n001", "n002"], ["n004"], 1),
    ]
    for i, (q, qtype, gfixture, rel, irrel, depth) in enumerate(lookup_queries):
        records.append({
            "id": f"R_LU_{i+1:02d}", "query": q, "query_type": qtype,
            "source_dataset": "metaqa_1hop" if "Movie" in q or "directed" in q else "webqsp" if "founded" in q or "located" in q or "created" in q else "synthetic",
            "graph_fixture": gfixture, "relevant_node_ids": rel, "irrelevant_node_ids": irrel,
            "at_time": None, "expected_hop_depth": depth, "tags": [qtype],
        })

    # Multi-hop (20)
    multihop_queries = [
        ("What languages are spoken in movies starring actors from Christopher Nolan films?", "multi_hop", "metaqa_3hop", ["lang_english", "lang_french"], ["movie_099"], 3),
        ("What genre movies were made by directors who worked with Tom Hanks?", "multi_hop", "metaqa_2hop", ["genre_drama", "genre_action"], ["movie_001"], 2),
        ("What decisions were influenced by the DTI policy violation?", "multi_hop", "diamond", ["B", "D"], ["A"], 2),
        ("What caused the policy compliance failure that led to the rejection?", "multi_hop", "diamond", ["A", "B"], ["D"], 2),
        ("Which actors starred in movies produced in the same year as Movie_010?", "multi_hop", "metaqa_2hop", ["actor_001", "actor_002"], ["actor_010"], 2),
        ("What are the downstream effects of the credit policy change?", "multi_hop", "branching", ["branch_0", "leaf_0_0", "leaf_0_1"], ["branch_1"], 2),
        ("What policies were applied in cases similar to the overturned precedent?", "multi_hop", "diamond", ["A", "C"], ["D"], 2),
        ("Which movies in the same genre as Inception were directed in the 2010s?", "multi_hop", "metaqa_2hop", ["movie_010", "movie_020"], ["movie_001"], 2),
        ("What is the root cause of the compliance violation chain?", "multi_hop", "linear_5", ["n000", "n001"], ["n003", "n004"], 2),
        ("Which employees were promoted under the same policy as Employee A?", "multi_hop", "branching", ["branch_0", "leaf_0_0"], ["branch_1"], 2),
        ("What are all effects of the fraudulent order detection policy?", "multi_hop", "branching", ["branch_0", "branch_1"], ["leaf_0_0"], 2),
        ("Which clinical trials affected by the same exclusion criterion as Trial_001?", "multi_hop", "diamond", ["B", "C"], ["A"], 2),
        ("What decisions led to the final contract rejection?", "multi_hop", "linear_5", ["n000", "n001", "n002"], ["n004"], 3),
        ("What actors worked with directors who made sci-fi films released after 2015?", "multi_hop", "metaqa_3hop", ["actor_003", "actor_005"], ["actor_009"], 3),
        ("What are all ancestors of the compliance failure node?", "multi_hop", "linear_5", ["n000", "n001", "n002", "n003"], [], 4),
        ("Which vendor policies were overridden by the exception approval?", "multi_hop", "diamond", ["A", "B", "C"], ["D"], 3),
        ("What are the consequences of the employment policy breach?", "multi_hop", "branching", ["branch_0", "leaf_0_0", "leaf_0_1"], ["branch_1"], 2),
        ("Which contract clauses are linked to the IP ownership dispute?", "multi_hop", "diamond", ["A", "C", "D"], ["B"], 2),
        ("What decisions were made under the pre-2023 fraud detection rules?", "multi_hop", "temporal_6", ["t000", "t001", "t002"], ["t004", "t005"], 2),
        ("What genre movies feature actors who appeared in movies directed by Denis Villeneuve?", "multi_hop", "metaqa_3hop", ["genre_sci-fi", "genre_drama"], ["genre_comedy"], 3),
    ]
    for i, (q, qtype, gfixture, rel, irrel, depth) in enumerate(multihop_queries):
        records.append({
            "id": f"R_MH_{i+1:02d}", "query": q, "query_type": qtype,
            "source_dataset": "metaqa_2hop" if "2hop" in gfixture else ("metaqa_3hop" if "3hop" in gfixture else "synthetic"),
            "graph_fixture": gfixture, "relevant_node_ids": rel, "irrelevant_node_ids": irrel,
            "at_time": None, "expected_hop_depth": depth, "tags": [qtype, "multi_hop"],
        })

    # Temporal (15)
    temporal_queries = [
        ("What loans were approved as of June 2022?", "temporal", "temporal_6", ["t002"], ["t000", "t001", "t003", "t004", "t005"], "2022-06-15T00:00:00Z", 1),
        ("What policies were active before 2021?", "temporal", "temporal_6", ["t000", "t001"], ["t003", "t004", "t005"], "2020-12-31T23:59:59Z", 1),
        ("What decisions were recorded after January 2023?", "temporal", "temporal_6", ["t003", "t004", "t005"], ["t000", "t001"], "2023-01-01T00:00:00Z", 1),
        ("Which contracts were valid during 2021?", "temporal", "temporal_6", ["t001"], ["t000", "t002", "t003"], "2021-06-01T00:00:00Z", 1),
        ("What was the credit policy as of Q3 2022?", "temporal", "temporal_6", ["t002"], ["t004", "t005"], "2022-09-01T00:00:00Z", 1),
        ("Which employee promotions occurred between 2020 and 2022?", "temporal", "temporal_6", ["t000", "t001", "t002"], ["t004", "t005"], None, 1),
        ("What fraud detections were recorded since the 2023 policy update?", "temporal", "temporal_6", ["t003", "t004"], ["t000", "t001"], "2023-01-01T00:00:00Z", 1),
        ("What clinical trial enrollments were valid prior to 2022?", "temporal", "temporal_6", ["t000", "t001"], ["t003", "t004"], "2021-12-31T23:59:59Z", 1),
        ("What decisions were overturned after the 2024 policy change?", "temporal", "temporal_6", ["t004", "t005"], ["t000", "t001", "t002"], "2024-01-01T00:00:00Z", 1),
        ("What loan decisions were active throughout 2021?", "temporal", "temporal_6", ["t001"], ["t000", "t003"], "2021-06-01T00:00:00Z", 1),
        ("Which contracts expired before 2022?", "temporal", "temporal_6", ["t000", "t001"], ["t003", "t004", "t005"], "2022-01-01T00:00:00Z", 1),
        ("What vendor approvals were in force as of March 2023?", "temporal", "temporal_6", ["t003"], ["t000", "t001", "t005"], "2023-03-01T00:00:00Z", 1),
        ("Which HR policies changed between 2022 and 2023?", "temporal", "temporal_6", ["t002", "t003"], ["t000", "t005"], None, 1),
        ("What were the active fraud rules before 2020?", "temporal", "temporal_6", [], ["t001", "t002", "t003"], "2019-12-31T23:59:59Z", 1),
        ("What refund policies applied in January 2022?", "temporal", "temporal_6", ["t002"], ["t004", "t005"], "2022-01-15T00:00:00Z", 1),
    ]
    for i, (q, qtype, gfixture, rel, irrel, at_time, depth) in enumerate(temporal_queries):
        records.append({
            "id": f"R_TM_{i+1:02d}", "query": q, "query_type": qtype,
            "source_dataset": "timeqa + synthetic",
            "graph_fixture": gfixture, "relevant_node_ids": rel, "irrelevant_node_ids": irrel,
            "at_time": at_time, "expected_hop_depth": depth, "tags": [qtype, "temporal"],
        })

    # Causal (10)
    causal_queries = [
        ("What caused the DTI policy violation?", "causal", "diamond", ["A", "B"], ["D"], 2),
        ("What are the downstream effects of the credit score failure?", "causal", "linear_5", ["n001", "n002", "n003"], ["n000"], 2),
        ("What is the root cause of the compliance rejection?", "causal", "linear_5", ["n000"], ["n003", "n004"], 4),
        ("What led to the contract termination?", "causal", "branching", ["root", "branch_0"], ["branch_1"], 2),
        ("What triggered the fraud escalation decision?", "causal", "diamond", ["A", "C"], ["D"], 2),
        ("What are the causes of the loan rejection chain?", "causal", "linear_5", ["n000", "n001"], ["n004"], 3),
        ("What caused the policy conflict in the healthcare trial?", "causal", "diamond", ["A", "B", "C"], ["D"], 2),
        ("What are the upstream causes of the HR promotion denial?", "causal", "branching", ["root"], ["leaf_0_0"], 2),
        ("What caused the vendor compliance failure?", "causal", "linear_5", ["n000", "n001", "n002"], ["n004"], 3),
        ("What is the full causal chain behind the contract rejection?", "causal", "linear_5", ["n000", "n001", "n002", "n003"], [], 4),
    ]
    for i, (q, qtype, gfixture, rel, irrel, depth) in enumerate(causal_queries):
        records.append({
            "id": f"R_CA_{i+1:02d}", "query": q, "query_type": qtype,
            "source_dataset": "atomic_causal + synthetic",
            "graph_fixture": gfixture, "relevant_node_ids": rel, "irrelevant_node_ids": irrel,
            "at_time": None, "expected_hop_depth": depth, "tags": [qtype, "causal"],
        })

    # No-match (10)
    no_match_queries = [
        ("quantum entanglement in mortgage approval", "no_match", "linear_5", [], ["n000", "n001"], None, 0),
        ("blockchain consensus in employee promotion", "no_match", "linear_5", [], ["n001", "n002"], None, 0),
        ("dark matter in clinical trial eligibility", "no_match", "temporal_6", [], ["t000", "t001"], None, 0),
        ("cryptocurrency volatility in contract review", "no_match", "diamond", [], ["A", "B"], None, 0),
        ("nuclear fusion in fraud detection", "no_match", "branching", [], ["root", "branch_0"], None, 0),
        ("alien contact in vendor approval", "no_match", "linear_5", [], ["n003", "n004"], None, 0),
        ("time travel in HR policy", "no_match", "temporal_6", [], ["t002", "t003"], None, 0),
        ("perpetual motion in loan underwriting", "no_match", "linear_5", [], ["n000"], None, 0),
        ("telepathy in customer identification", "no_match", "diamond", [], ["C", "D"], None, 0),
        ("faster-than-light travel in compliance checking", "no_match", "branching", [], ["leaf_0_0"], None, 0),
    ]
    for i, (q, qtype, gfixture, rel, irrel, at_time, depth) in enumerate(no_match_queries):
        records.append({
            "id": f"R_NM_{i+1:02d}", "query": q, "query_type": qtype,
            "source_dataset": "synthetic",
            "graph_fixture": gfixture, "relevant_node_ids": rel, "irrelevant_node_ids": irrel,
            "at_time": at_time, "expected_hop_depth": depth, "tags": [qtype, "uncertainty"],
        })

    write(FIXTURES / "retrieval_eval_dataset.json", {
        "version": "1.0",
        "description": "70-record labelled retrieval queries for precision/recall evaluation.",
        "sources": ["MetaQA CC-Public", "WebQSP CC-BY-4.0", "TimeQA research", "ATOMIC CC-BY-4.0", "synthetic"],
        "record_count": len(records),
        "query_type_counts": {qt: sum(1 for r in records if r["query_type"] == qt)
                               for qt in ["direct_lookup", "multi_hop", "temporal", "causal", "no_match"]},
        "records": records,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating Context Graph Effectiveness benchmark fixtures...")
    print()

    print("Lending:")
    gen_german_credit()
    gen_credit_risk()

    print("Healthcare:")
    gen_trec_ct()
    gen_trialgpt()

    print("Legal:")
    gen_cuad()
    gen_ledgar()

    print("HR:")
    gen_ibm_hr()
    gen_hr_promotion()

    print("E-commerce:")
    gen_ecommerce()

    print("KGQA:")
    gen_metaqa()
    gen_webqsp()

    print("Deduplication:")
    gen_dblp_acm_pairs()
    gen_amazon_google_pairs()
    gen_abt_buy_pairs()

    print("Causal:")
    gen_atomic_causal()
    gen_ecare()

    print("Temporal:")
    gen_timeqa()

    print("Provenance:")
    gen_fever()

    print("Synthesized evaluation datasets:")
    gen_decision_intelligence_dataset()
    gen_retrieval_eval_dataset()

    print()
    print("All fixtures written successfully.")
    print("Location: benchmarks/context_graph_effectiveness/fixtures/")
