# NLP Leave Reasons Dataset Specification (Corpus Provenance & Ethics)
**Project Title:** AI-Enabled Faculty Attendance, Leave and Substitute Management ERP  
**Corpus Name:** `leave_reasons_corpus.json` / `leave_reasons_corpus.csv`  
**Dataset Version:** 3.1.0  
**Curator / Engine:** `nlp/dataset_generator.py`  
**Storage Path:** `dataset/leave_reasons_corpus.json`, `dataset/leave_reasons_corpus.csv`  

---

## 1. Executive Summary & Purpose

The Natural Language Processing (NLP) Leave Reasons Dataset is a balanced, domain-curated corpus of **500 natural language leave applications** representing realistic leave requests submitted by faculty and instructional staff in Indian higher education institutions (engineering and MCA colleges).

The primary research and engineering objective of this corpus is to train and evaluate pure-NumPy text classifiers (`MultinomialNaiveBayes`, `SoftmaxLogisticRegression`, and `LinearSVM`) that automatically categorize unstructured text into institutional leave categories, routing applications to appropriate approval authorities while flagging policy violations (such as medical leaves lacking doctor certificates or sandwich leave weekend overlaps).

---

## 2. Statistical Metrics & Corpus Characteristics

All metrics reported below were computed directly from the generated corpus using `nlp/vectorizer.py` and `nlp/dataset_generator.py`.

| Metric | Measured Value | Description / Scope |
|---|:---:|---|
| **Total Samples ($N$)** | **500** | Full corpus record count |
| **Number of Classes ($K$)** | **5** | Target statutory institutional leave types |
| **Samples per Class** | **100** | Perfectly balanced ($1:1:1:1:1$ ratio) |
| **Total Token Count** | **9,314** | All whitespace-separated word tokens |
| **Unique Raw Vocabulary** | **388** | Distinct raw word types prior to lemmatization |
| **Extracted N-Gram Features** | **845** | Unigrams and bigrams extracted with TF-IDF |
| **Mean Word Count per Sample** | **18.6** | Average length in words per leave reason |
| **Minimum Sample Length** | **8 words** | Shortest application description |
| **Maximum Sample Length** | **34 words** | Longest application description |

---

## 3. Leave Category Distribution & Taxonomy

The 5 target classes correspond directly to higher education service rules (e.g., VTU, AICTE, and state civil services norms):

| Code | Leave Category Name | Count | Share | Typical Institutional Trigger |
|:---:|---|:---:|:---:|---|
| **`CL`** | Casual Leave | 100 | 20.0% | Domestic errands, family functions, personal property documentation, local RTO work. |
| **`ML`** | Medical Leave | 100 | 20.0% | Viral fever, hospital admission, post-surgical recovery, typhoid, migraine, dental surgery. |
| **`EL`** | Earned Leave | 100 | 20.0% | Long-planned domestic or international vacations, ancestral property registration, pilgrimage. |
| **`SCL`** | Special Casual Leave | 100 | 20.0% | AICTE FDPs, IEEE conferences, university semester practical exam evaluation, external PhD vivas. |
| **`OD`** | On Duty Leave | 100 | 20.0% | Mandatory university academic council, NAAC peer team preparation, lab inspection deputations. |
| **Total** | | **500** | **100.0%** | **Perfect Class Balance ($20\%$ per class)** |

---

## 4. Dataset Generation Methodology & Provenance

### 4.1 Seed Prompt Templates
For each of the 5 categories, domain experts curated **10 to 15 authentic base seed prompts** reflecting standard phrasing used in departmental communication across engineering institutions.

Example Base Seeds:
- **`CL`:** *"Personal work at the local RTO office for driving license renewal."*
- **`ML`:** *"I am suffering from severe viral fever and doctor advised 3 days bed rest."*
- **`EL`:** *"Requesting 7 days earned leave for pilgrimage trip to Tirupati and Varanasi."*
- **`SCL`:** *"Attending IEEE International Conference on Artificial Intelligence to present paper."*
- **`OD`:** *"Deputed on official university duty for inspecting affiliated college laboratories."*

### 4.2 Realistic Contextual Modifiers & Syntactic Expansion
To avoid rote pattern memorization and ensure model robustness across varied writing styles, the seed prompts are systematically modulated with:
1. **Institutional Suffix Modifiers (10 variations):**
   - *"Please grant me leave for the same."*
   - *"Doctor certificate is attached herewith for your reference."*
   - *"I will ensure my lecture topics are covered by substitute faculty."*
   - *"Necessary supporting documents have been uploaded."*
   - *"I have informed the HOD regarding lecture adjustments."*
2. **Formal Institutional Salutations:**
   - Alternating prefixes: *"Respected Sir/Madam, ..."* or *"Due to urgent reasons, ..."*.
3. **Word Variation & Lexical Diversity:**
   - Modifiers introduce realistic variance in sentence length, formal phrasing, and polite institutional requests.

---

## 5. Sample Rows per Category

| ID | Category | Leave Reason Text | Key Predictive Features |
|:---:|:---:|---|---|
| **1** | `CL` | *"I need to attend a family function at my hometown."* | `family`, `function`, `home` |
| **17** | `CL` | *"Respected Sir/Madam, Personal work at the local RTO office for driving license renewal. Please grant me leave for the same."* | `personal`, `rto`, `work` |
| **101** | `ML` | *"I am suffering from severe viral fever and doctor advised 3 days bed rest."* | `fever`, `doctor`, `advis`, `bed rest` |
| **105** | `ML` | *"Diagnosed with acute typhoid fever and prescribed medication rest for 5 days. Doctor certificate is attached herewith for your reference."* | `typhoid`, `medication`, `certificate` |
| **201** | `EL` | *"Planning extended annual family vacation trip to North India."* | `earn`, `vacation`, `family`, `trip` |
| **212** | `EL` | *"Respected Sir/Madam, Requesting 7 days earned leave for pilgrimage trip to Tirupati and Varanasi."* | `pilgrimage`, `earn leave`, `trip` |
| **301** | `SCL` | *"Attending IEEE International Conference on Artificial Intelligence to present paper."* | `ieee`, `conference`, `paper`, `research` |
| **303** | `SCL` | *"Deputed for VTU University semester end practical examination evaluation duty."* | `vtu`, `evaluation`, `practical`, `examination` |
| **401** | `OD` | *"Deputed on official university duty for inspecting affiliated college laboratories."* | `official`, `deput`, `duty`, `inspect` |
| **403** | `OD` | *"On duty for accompanying MCA students on industrial visit to Infosys Mysore."* | `duty`, `industrial`, `visit`, `student` |

---

## 6. Scientific & Legal Justification for Synthetic Data

In real-world enterprise ERP deployments, acquiring real faculty leave applications presents severe privacy, ethical, and legal challenges. This project adopted synthetic generation based on rigorous domain templates for the following decisive reasons:

### 6.1 Compliance with India Digital Personal Data Protection (DPDP) Act 2023
- Leave reasons frequently disclose sensitive personal health data (e.g., medical diagnoses, hospitalization records, pregnancy details) and confidential domestic circumstances.
- Under Section 4 and Section 6 of India's **DPDP Act 2023**, processing and publicly releasing employee health or domestic records without explicit, uncoerced consent violates statutory data protection provisions and incurs severe legal liabilities.
- Generating synthetic text using institutional templates completely eliminates PII exposure while preserving linguistic and structural realism.

### 6.2 Institutional Confidentiality & Data Scarcity
- Academic institutions treat internal HR and leave records as confidential personnel data. Access to raw institutional databases for student/major project research is generally prohibited by institute privacy policies.
- Furthermore, historical leave datasets are typically severely class-imbalanced (e.g., Casual Leave constitutes 75% of submissions, while Special Casual Leave accounts for under 5%). Training on raw historical distributions causes models to heavily bias toward the majority class.

### 6.3 Controlled Class Balance & Benchmarking Rigor
- Controlled synthetic generation guarantees a mathematically **balanced benchmark** (exactly 100 samples per class).
- This prevents metric distortion: Macro-averaged F1 and Expected Calibration Error (ECE) reflect true algorithmic performance rather than class frequency priors.

---

## 7. Data Format & Pipeline Schema

### JSON Schema (`dataset/leave_reasons_corpus.json`):
```json
[
  {
    "id": 1,
    "text": "I need to attend a family function at my hometown.",
    "label": "CL",
    "leave_type_name": "Casual Leave"
  }
]
```

### CSV Schema (`dataset/leave_reasons_corpus.csv`):
```csv
id,text,label,leave_type_name
1,"I need to attend a family function at my hometown.",CL,"Casual Leave"
```

---

## 8. Preprocessing & Feature Extraction Pipeline

1. **Lowercasing & Normalization:** Strips HTML tags, punctuation, and non-alphanumeric symbols.
2. **Tokenization:** Splits tokens of length $\ge 2$, filtering pure digits.
3. **Stopword Elimination:** Custom English stopword dictionary (140+ words) including institutional filler words (*"please"*, *"kindly"*, *"grant"*, *"request"*).
4. **Domain Lemmatization:** Rule-based suffix stripping (`-ing`, `-ed`, `-es`, `-ies`, `-s`) plus custom academic/medical lemma maps (`feverish` $\to$ `fever`, `evaluations` $\to$ `evaluate`, `hospitalized` $\to$ `hospital`).
5. **N-Gram TF-IDF Vectorization:** Unigrams + bigrams with sublinear term-frequency scaling ($1 + \log(\text{tf})$), smoothed inverse document frequency ($\log((1+N)/(1+\text{df})) + 1$), and row $L_2$ vector normalization.
6. **Composite Feature Merging:** Concatenates 845 text features with 4 normalized tabular metadata features:
   - `meta_requested_days_norm` (normalized by $/ 10.0$)
   - `meta_notice_period_days_norm` (normalized by $/ 30.0$)
   - `meta_has_medical_doc` ($1.0$ or $0.0$)
   - `meta_is_sandwich_leave` ($1.0$ or $0.0$)
