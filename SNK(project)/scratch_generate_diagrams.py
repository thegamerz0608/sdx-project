"""
Draws high-resolution visual diagrams for SDS using Pillow and saves them in diagrams/ directory.
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DIAGRAM_DIR = Path("D:/SNK(project)/diagrams")
DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)

def get_font(size=14, bold=False):
    # Try Windows system fonts
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf"]
    for f in font_names:
        p = Path("C:/Windows/Fonts") / f
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_round_rect(draw, box, radius=8, fill="white", outline="#1B365D", width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def draw_arrow(draw, start, end, color="#1B365D", width=2, arrow_size=6):
    x1, y1 = start
    x2, y2 = end
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    if x1 == x2: # Vertical
        if y2 > y1: # Down
            draw.polygon([(x2, y2), (x2 - arrow_size, y2 - arrow_size * 1.5), (x2 + arrow_size, y2 - arrow_size * 1.5)], fill=color)
        else: # Up
            draw.polygon([(x2, y2), (x2 - arrow_size, y2 + arrow_size * 1.5), (x2 + arrow_size, y2 + arrow_size * 1.5)], fill=color)
    elif y1 == y2: # Horizontal
        if x2 > x1: # Right
            draw.polygon([(x2, y2), (x2 - arrow_size * 1.5, y2 - arrow_size), (x2 - arrow_size * 1.5, y2 + arrow_size)], fill=color)
        else: # Left
            draw.polygon([(x2, y2), (x2 + arrow_size * 1.5, y2 - arrow_size), (x2 + arrow_size * 1.5, y2 + arrow_size)], fill=color)

# -----------------------------------------------------------------------------
# 1. System Context Diagram
# -----------------------------------------------------------------------------
def make_context_diagram():
    img = Image.new("RGB", (900, 700), "white")
    d = ImageDraw.Draw(img)
    f_title = get_font(15, bold=True)
    f_body = get_font(12)
    f_label = get_font(11)
    
    # Cylinder / DB on top
    d.rounded_rectangle([320, 30, 580, 110], radius=15, fill="#E3F2FD", outline="#1565C0", width=2)
    d.text((360, 48), "Biometric Attendance &\nAcademic Leave Corpus", fill="#0D47A1", font=f_title, align="center")
    
    # Arrow to Core App
    draw_arrow(d, (450, 110), (450, 200), color="#1565C0", width=2)
    d.text((460, 145), "Ingest attendance logs &\ntrain NLP leave models", fill="#333333", font=f_label)
    
    # Core Application Box
    draw_round_rect(d, [270, 200, 630, 320], radius=10, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((330, 235), "FACULTY_ERP APPLICATION", fill="#1B365D", font=f_title)
    d.text((310, 265), "(Attendance, NLP Leave Classifier,\nRisk Evaluation & Substitute Allocation)", fill="#555555", font=f_body, align="center")
    
    # User on right
    draw_round_rect(d, [710, 380, 860, 480], radius=8, fill="#FFFFFF", outline="#333333", width=2)
    d.text((760, 420), "User\n(Faculty / HOD /\nAdmin)", fill="#333333", font=f_title, align="center")
    
    # Arrows between Core App and User
    # 1. User -> App
    d.line([(785, 380), (785, 230), (630, 230)], fill="#333333", width=2)
    draw_arrow(d, (640, 230), (630, 230), color="#333333", width=2)
    d.text((645, 210), "Upload Attendance / Submit Leave", fill="#333333", font=f_label)
    
    # 2. App -> User
    d.line([(630, 270), (750, 270), (750, 380)], fill="#333333", width=2)
    draw_arrow(d, (750, 370), (750, 380), color="#333333", width=2)
    d.text((540, 280), "Screening report, NLP predictions,\nrisk & substitute allocations", fill="#333333", font=f_label)
    
    # 3. Notification to User
    d.line([(450, 320), (450, 440), (710, 440)], fill="#333333", width=2)
    draw_arrow(d, (700, 440), (710, 440), color="#333333", width=2)
    d.text((465, 420), "Duty notifications & approval status", fill="#333333", font=f_label)
    
    # Downstream Report Service on left
    draw_round_rect(d, [80, 390, 270, 480], radius=8, fill="#FFFFFF", outline="#333333", width=2)
    d.text((105, 415), "Institutional Report &\nExport Service", fill="#333333", font=f_title, align="center")
    
    d.line([(350, 320), (350, 435), (270, 435)], fill="#333333", width=2)
    draw_arrow(d, (280, 435), (270, 435), color="#333333", width=2)
    d.text((285, 415), "Generate PDFs & CSVs", fill="#333333", font=f_label)
    
    # Attendance & Leave Reports Box
    draw_round_rect(d, [80, 540, 270, 630], radius=8, fill="#F5F5F5", outline="#333333", width=2)
    d.text((95, 565), "Official Attendance Rosters &\nLeave Ledgers", fill="#333333", font=f_body, align="center")
    
    draw_arrow(d, (175, 480), (175, 540), color="#333333", width=2)
    
    img.save(DIAGRAM_DIR / "diagram_context.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# 2. End-to-End ML Pipeline Diagram
# -----------------------------------------------------------------------------
def make_ml_pipeline_diagram():
    img = Image.new("RGB", (900, 1150), "white")
    d = ImageDraw.Draw(img)
    f_b = get_font(12, bold=True)
    f_t = get_font(11)
    
    # Top 4 boxes
    boxes_top = [
        ("1. Data Ingestion\nBiometric Logs &\nLeave Text Corpus", (40, 30, 220, 120), "#E3F2FD", "#1565C0"),
        ("2. Data Validation\nCheck formats, labels,\nmissing records &\nduplicates", (260, 30, 440, 120), "#E3F2FD", "#1565C0"),
        ("3. Preprocessing\nTokenization, lower,\nstopwords, stemming,\nTF-IDF vectorizer", (480, 30, 660, 120), "#E8F5E9", "#2E7D32"),
        ("4. Dataset Splitting\nStratified 80:10:10\nTrain, Validation &\nHeld-out Test Set", (700, 30, 880, 120), "#E3F2FD", "#1565C0"),
    ]
    
    for text, box, bg, border in boxes_top:
        d.rounded_rectangle(box, radius=8, fill=bg, outline=border, width=2)
        d.text((box[0] + 12, box[1] + 12), text, fill="#1B365D", font=f_b)
        
    # Arrows across top row
    draw_arrow(d, (220, 75), (260, 75), color="#1565C0", width=2)
    draw_arrow(d, (440, 75), (480, 75), color="#1565C0", width=2)
    draw_arrow(d, (660, 75), (700, 75), color="#1565C0", width=2)
    
    # Arrow from box 4 down to training
    d.line([(790, 120), (790, 160), (130, 160), (130, 190)], fill="#1B365D", width=2)
    draw_arrow(d, (130, 180), (130, 190), color="#1B365D", width=2)
    
    # Box 5: Model Training
    d.rounded_rectangle([40, 190, 220, 280], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((50, 205), "5. Model Training\nTrain pure-NumPy\nNaive Bayes, LogReg\nand Linear SVM", fill="#1B365D", font=f_b)
    
    # Arrow to Validation
    draw_arrow(d, (220, 235), (550, 235), color="#1B365D", width=2)
    
    # Box 6: Model Validation
    d.rounded_rectangle([550, 190, 730, 280], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((560, 205), "6. Model Validation\nEvaluate accuracy,\nmacro F1-score and\ntune hyperparameters", fill="#1B365D", font=f_b)
    
    # Arrow down to diamond
    draw_arrow(d, (640, 280), (640, 330), color="#1B365D", width=2)
    
    # Diamond: Performance acceptable?
    d.polygon([(340, 380), (440, 320), (540, 380), (440, 440)], fill="#FFF3E0", outline="#E65100", width=2)
    d.text((375, 365), "Performance\nacceptable?", fill="#BF360C", font=f_b, align="center")
    
    # Arrow from 6 down to diamond
    d.line([(640, 380), (540, 380)], fill="#1B365D", width=2)
    draw_arrow(d, (550, 380), (540, 380), color="#1B365D", width=2)
    
    # No branch -> Adjust parameters
    draw_arrow(d, (340, 380), (220, 380), color="#E65100", width=2)
    d.text((270, 360), "No", fill="#E65100", font=f_b)
    
    d.rounded_rectangle([40, 340, 220, 420], radius=8, fill="#FFF3E0", outline="#E65100", width=2)
    d.text((55, 355), "Adjust parameters\n(L2 C, Laplace alpha)\nand retrain", fill="#BF360C", font=f_b)
    
    # Loop back to training
    d.line([(130, 340), (130, 280)], fill="#E65100", width=2)
    draw_arrow(d, (130, 290), (130, 280), color="#E65100", width=2)
    
    # Yes branch -> Model Registry
    draw_arrow(d, (440, 440), (440, 490), color="#2E7D32", width=2)
    d.text((450, 455), "Yes", fill="#2E7D32", font=f_b)
    
    d.rounded_rectangle([340, 490, 540, 580], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((365, 505), "7. Model Registry /\nModel Artifact Storage\nSave selected model\nand configuration", fill="#1B365D", font=f_b, align="center")
    
    # Final Test Set Evaluation (on left)
    d.line([(340, 535), (220, 535), (220, 630)], fill="#1565C0", width=2)
    draw_arrow(d, (220, 620), (220, 630), color="#1565C0", width=2)
    
    d.rounded_rectangle([120, 630, 320, 710], radius=8, fill="#E3F2FD", outline="#1565C0", width=2)
    d.text((140, 645), "Final Test Evaluation\nEvaluate selected model\non held-out test set", fill="#0D47A1", font=f_b, align="center")
    
    # Inference Branch (on right)
    d.line([(540, 535), (660, 535), (660, 410), (750, 410)], fill="#1B365D", width=2)
    draw_arrow(d, (740, 410), (750, 410), color="#1B365D", width=2)
    
    d.rounded_rectangle([660, 410, 880, 490], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((675, 425), "8. Real-Time Inference\nReceive faculty leave text\nand apply TF-IDF vectorizer", fill="#1B365D", font=f_b)
    
    # Arrow to prediction
    draw_arrow(d, (770, 490), (770, 530), color="#1B365D", width=2)
    
    d.rounded_rectangle([660, 530, 880, 600], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((680, 545), "Leave Type Prediction\n(CL, ML, EL, OD) &\nSoftmax Confidence Gauge", fill="#1B365D", font=f_b, align="center")
    
    # Split to NLP Explanation & Multi-Factor Risk
    draw_arrow(d, (720, 600), (600, 650), color="#1B365D", width=2)
    draw_arrow(d, (820, 600), (820, 650), color="#1B365D", width=2)
    
    d.rounded_rectangle([520, 650, 700, 720], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((535, 665), "Keyword & Token\nRelevance Explanation\n(Extracted salient terms)", fill="#1B365D", font=f_b, align="center")
    
    d.rounded_rectangle([720, 650, 890, 720], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((735, 665), "Multi-Factor Risk &\nPolicy Assessment\n(Balance, Sandwich, Proof)", fill="#1B365D", font=f_b, align="center")
    
    # Merge into Generate Evaluation Report
    d.line([(610, 720), (610, 760), (710, 760)], fill="#1B365D", width=2)
    d.line([(805, 720), (805, 760), (710, 760)], fill="#1B365D", width=2)
    draw_arrow(d, (710, 760), (710, 790), color="#6A1B9A", width=2)
    
    d.rounded_rectangle([600, 790, 820, 880], radius=8, fill="#F3E5F5", outline="#6A1B9A", width=2)
    d.text((615, 805), "Generate Screening Report\nPrediction category, confidence,\nrisk score and balance status", fill="#4A148C", font=f_b, align="center")
    
    # Split into Substitute Workload Balancer & Referral Guidance
    draw_arrow(d, (650, 880), (550, 930), color="#6A1B9A", width=2)
    draw_arrow(d, (770, 880), (770, 930), color="#6A1B9A", width=2)
    
    d.rounded_rectangle([440, 930, 650, 1010], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((455, 945), "Substitute Workload Balancer\nDetect timetable collisions,\nrank available peer faculty", fill="#1B365D", font=f_b, align="center")
    
    d.rounded_rectangle([680, 930, 880, 1010], radius=8, fill="#F3E5F5", outline="#6A1B9A", width=2)
    d.text((695, 945), "HOD Approval Guidance\nDisplay auto-feasible flag\nand suggested substitute", fill="#4A148C", font=f_b, align="center")
    
    # Merge to Display Report
    d.line([(545, 1010), (545, 1050), (660, 1050)], fill="#1B365D", width=2)
    d.line([(780, 1010), (780, 1050), (660, 1050)], fill="#1B365D", width=2)
    draw_arrow(d, (660, 1050), (660, 1080), color="#1B365D", width=2)
    
    d.rounded_rectangle([560, 1080, 760, 1130], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((585, 1095), "Display Report to User", fill="#1B365D", font=f_b)
    
    img.save(DIAGRAM_DIR / "diagram_ml_pipeline.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# 3. Model Architecture Diagram
# -----------------------------------------------------------------------------
def make_model_arch_diagram():
    img = Image.new("RGB", (800, 850), "white")
    d = ImageDraw.Draw(img)
    f_b = get_font(13, bold=True)
    f_t = get_font(11)
    
    # Flow down
    steps = [
        ("Faculty Leave Reason Text\n(e.g., 'Suffering from high fever, acute stomach pain and cold')", (220, 20, 580, 80), "#FFFFFF"),
        ("Tokenization, Cleaning & Lemmatization\n['fever', 'acut', 'stomach', 'pain', 'cold']", (220, 120, 580, 180), "#E3F2FD"),
        ("Pure-NumPy TF-IDF Feature Extraction\n(Sublinear TF, Smoothed IDF, L2 Normalization -> R^845)", (200, 220, 600, 280), "#E8F5E9"),
    ]
    
    for text, box, bg in steps:
        draw_round_rect(d, box, radius=8, fill=bg, outline="#1B365D", width=2)
        d.text((box[0] + 15, box[1] + 12), text, fill="#1B365D", font=f_b, align="center")
        
    draw_arrow(d, (400, 80), (400, 120), color="#1B365D", width=2)
    draw_arrow(d, (400, 180), (400, 220), color="#1B365D", width=2)
    
    # Diamond: Candidate Model
    d.polygon([(300, 370), (400, 320), (500, 370), (400, 420)], fill="#FFF3E0", outline="#E65100", width=2)
    d.text((345, 360), "Candidate Model", fill="#BF360C", font=f_b)
    draw_arrow(d, (400, 280), (400, 320), color="#1B365D", width=2)
    
    # Split to 2 parallel candidate models
    draw_arrow(d, (300, 370), (220, 450), color="#1B365D", width=2)
    draw_arrow(d, (500, 370), (580, 450), color="#1B365D", width=2)
    
    # Left: Multinomial Naive Bayes
    draw_round_rect(d, [120, 450, 320, 510], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((135, 465), "Multinomial Naive Bayes\n(Laplace Smoothed Priors)", fill="#1B365D", font=f_b, align="center")
    
    # Right: Softmax Logistic Regression (Selected)
    draw_round_rect(d, [480, 450, 680, 510], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((495, 465), "Softmax Logistic Regression\n(SGD Cross-Entropy, L2 Decay)", fill="#1B365D", font=f_b, align="center")
    
    # Linear Classification Layer
    draw_arrow(d, (220, 510), (220, 560), color="#1B365D", width=2)
    draw_arrow(d, (580, 510), (580, 560), color="#1B365D", width=2)
    
    draw_round_rect(d, [120, 560, 320, 620], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((140, 575), "Posterior Probability Layer\nLog P(c) + Sum(TF*log(P))", fill="#333333", font=f_b, align="center")
    
    draw_round_rect(d, [480, 560, 680, 620], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((505, 575), "Softmax Normalization Layer\nexp(z_c) / Sum(exp(z))", fill="#1B365D", font=f_b, align="center")
    
    # Probabilities output
    draw_arrow(d, (220, 620), (220, 670), color="#1B365D", width=2)
    draw_arrow(d, (580, 620), (580, 670), color="#1B365D", width=2)
    
    draw_round_rect(d, [120, 670, 320, 730], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((135, 685), "Class Log Likelihoods\n(CL, ML, EL, OD)", fill="#333333", font=f_b, align="center")
    
    draw_round_rect(d, [480, 670, 680, 730], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((505, 685), "Calibrated Class Probabilities\nP(ML)=94.2%, P(CL)=3.1%", fill="#1B365D", font=f_b, align="center")
    
    # Final Evaluate Box
    d.line([(220, 730), (220, 770), (400, 770)], fill="#1B365D", width=2)
    d.line([(580, 730), (580, 770), (400, 770)], fill="#1B365D", width=2)
    draw_arrow(d, (400, 770), (400, 790), color="#1B365D", width=2)
    
    draw_round_rect(d, [260, 790, 540, 840], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((280, 805), "Evaluate Model Performance &\nCompute Risk Recommendation", fill="#1B365D", font=f_b, align="center")
    
    img.save(DIAGRAM_DIR / "diagram_model_arch.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# 4. Storage Architecture Diagram
# -----------------------------------------------------------------------------
def make_storage_arch_diagram():
    img = Image.new("RGB", (900, 650), "white")
    d = ImageDraw.Draw(img)
    f_b = get_font(13, bold=True)
    f_t = get_font(11)
    
    # Top box: FACULTY_ERP STORAGE
    draw_round_rect(d, [350, 20, 550, 75], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((380, 35), "FACULTY_ERP\nSTORAGE", fill="#1B365D", font=f_b, align="center")
    
    # 4 storage columns
    cols = [
        ("Relational Database\n(MySQL / Fallback)", (40, 130, 220, 180)),
        ("CSV Ingestion &\nLogs Store", (260, 130, 440, 180)),
        ("Model Artifacts\nStorage", (480, 130, 660, 180)),
        ("Disaster Recovery &\nArchives", (700, 130, 880, 180)),
    ]
    
    for title, box in cols:
        draw_round_rect(d, box, radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
        d.text((box[0] + 15, box[1] + 8), title, fill="#1B365D", font=f_b, align="center")
        d.line([(box[0] + 90, 130), (box[0] + 90, 100), (450, 100), (450, 75)], fill="#1B365D", width=2)
        
    # Detail boxes below
    sub_cols = [
        ("12 Core 3NF Tables\n(Users, Attendance,\nLeaves, Substitutes)", (40, 220, 220, 290)),
        ("Attendance CSVs &\nBiometric Daily Logs", (260, 220, 440, 290)),
        ("TF-IDF Vectorizer &\nSoftmax Classifier\n(.joblib files)", (480, 220, 660, 290)),
        ("Full Zip Snapshots &\nCold Archives\n(.json.gz files)", (700, 220, 880, 290)),
    ]
    
    for title, box in sub_cols:
        draw_round_rect(d, box, radius=8, fill="#F8F9FA", outline="#555555", width=2)
        d.text((box[0] + 15, box[1] + 12), title, fill="#333333", font=f_t, align="center")
        
    draw_arrow(d, (130, 180), (130, 220), color="#1B365D", width=2)
    draw_arrow(d, (350, 180), (350, 220), color="#1B365D", width=2)
    draw_arrow(d, (570, 180), (570, 220), color="#1B365D", width=2)
    draw_arrow(d, (790, 180), (790, 220), color="#1B365D", width=2)
    
    # User Workflow Flow below
    flow_steps = [
        ("User Upload / Action", (370, 350, 530, 400)),
        ("Temporary Memory Processing", (350, 430, 550, 480)),
        ("Prediction & Policy Analysis", (355, 510, 545, 560)),
        ("Screening Report Display & Database Commit", (300, 590, 600, 640)),
    ]
    
    for title, box in flow_steps:
        draw_round_rect(d, box, radius=8, fill="#FFFFFF", outline="#333333", width=2)
        d.text((box[0] + 10, box[1] + 12), title, fill="#333333", font=f_b, align="center")
        
    draw_arrow(d, (450, 400), (450, 430), color="#333333", width=2)
    draw_arrow(d, (450, 480), (450, 510), color="#333333", width=2)
    draw_arrow(d, (450, 560), (450, 590), color="#333333", width=2)
    
    img.save(DIAGRAM_DIR / "diagram_storage_arch.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# 5. Use Case Diagram
# -----------------------------------------------------------------------------
def make_use_case_diagram():
    img = Image.new("RGB", (900, 800), "white")
    d = ImageDraw.Draw(img)
    f_b = get_font(13, bold=True)
    f_t = get_font(11)
    
    # Boundary box
    draw_round_rect(d, [260, 30, 850, 760], radius=10, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((450, 45), "FACULTY ERP SYSTEM BOUNDARY", fill="#1B365D", font=f_b)
    
    # Actors on left
    actors = [
        ("Faculty", 150),
        ("HOD", 380),
        ("Admin", 600)
    ]
    
    for name, y in actors:
        # Draw stick figure
        d.ellipse([100, y - 40, 130, y - 10], outline="#1B365D", width=2) # Head
        d.line([(115, y - 10), (115, y + 35)], fill="#1B365D", width=2)   # Body
        d.line([(90, y + 10), (140, y + 10)], fill="#1B365D", width=2)    # Arms
        d.line([(115, y + 35), (95, y + 65)], fill="#1B365D", width=2)    # Left leg
        d.line([(115, y + 35), (135, y + 65)], fill="#1B365D", width=2)   # Right leg
        d.text((95, y + 70), name, fill="#1B365D", font=f_b)
        
    # Use Case Ovals inside boundary
    cases = [
        ("Login & Authenticate Session", (320, 80, 580, 130), [150, 380, 600]),
        ("View Personal Attendance Logs", (320, 145, 580, 195), [150]),
        ("Submit NLP Leave Request", (320, 210, 580, 260), [150]),
        ("View Real-Time Prediction & Risk", (320, 275, 580, 325), [150]),
        ("Respond to Substitute Invitations", (320, 340, 580, 390), [150]),
        ("Monitor Department Attendance", (320, 405, 580, 455), [380]),
        ("Review Applications with AI Flags", (320, 470, 580, 520), [380]),
        ("Assign Conflict-Free Substitutes", (320, 535, 580, 585), [380]),
        ("Ingest Biometric Attendance CSV", (600, 180, 830, 230), [600]),
        ("Retrain Pure-NumPy Classifiers", (600, 280, 830, 330), [600]),
        ("Generate Institutional PDF Reports", (600, 380, 830, 430), [600]),
        ("Inspect Security Audit Trail", (600, 480, 830, 530), [600]),
        ("Create Backup & Run Diagnostics", (600, 580, 830, 630), [600]),
    ]
    
    for title, oval, actor_ys in cases:
        d.ellipse(oval, fill="#F0F4C3", outline="#558B2F", width=2)
        d.text((oval[0] + 15, oval[1] + 14), title, fill="#1B365D", font=f_t)
        for ay in actor_ys:
            d.line([(140, ay + 15), (oval[0], oval[1] + 25)], fill="#78909C", width=1)
            
    img.save(DIAGRAM_DIR / "diagram_use_case.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# 6. Class / Component Diagram
# -----------------------------------------------------------------------------
def make_class_component_diagram():
    img = Image.new("RGB", (900, 800), "white")
    d = ImageDraw.Draw(img)
    f_b = get_font(13, bold=True)
    f_t = get_font(11)
    
    # Top: User Interface
    draw_round_rect(d, [520, 30, 660, 90], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((545, 48), "User Interface\n(PySide6 Views)", fill="#1B365D", font=f_b, align="center")
    
    # Left column: Upload & Preprocess
    draw_round_rect(d, [260, 120, 440, 180], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((285, 138), "Attendance / Leave\nUpload Component", fill="#1B365D", font=f_b, align="center")
    
    draw_round_rect(d, [260, 220, 440, 280], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((280, 238), "NLP Preprocessing &\nTF-IDF Component", fill="#1B365D", font=f_b, align="center")
    
    draw_arrow(d, (520, 60), (350, 120), color="#1B365D", width=2)
    draw_arrow(d, (350, 180), (350, 220), color="#1B365D", width=2)
    
    # Center column: Substitute / HOD
    draw_round_rect(d, [520, 120, 660, 180], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((535, 138), "Substitute Workload\nBalancer Component", fill="#1B365D", font=f_b, align="center")
    
    draw_round_rect(d, [520, 220, 660, 280], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((540, 238), "Institutional Policy &\nGrace Ledger Component", fill="#1B365D", font=f_b, align="center")
    
    draw_arrow(d, (590, 90), (590, 120), color="#1B365D", width=2)
    draw_arrow(d, (590, 180), (590, 220), color="#1B365D", width=2)
    
    # Model components
    draw_round_rect(d, [160, 320, 340, 380], radius=8, fill="#E3F2FD", outline="#1565C0", width=2)
    d.text((185, 338), "Multinomial NB Model\n(Laplace Priors)", fill="#0D47A1", font=f_b, align="center")
    
    draw_round_rect(d, [360, 320, 540, 380], radius=8, fill="#E8F5E9", outline="#2E7D32", width=2)
    d.text((375, 338), "Softmax Logistic Reg\n(SGD Cross-Entropy)", fill="#1B365D", font=f_b, align="center")
    
    draw_arrow(d, (350, 280), (250, 320), color="#1B365D", width=2)
    draw_arrow(d, (350, 280), (450, 320), color="#1B365D", width=2)
    
    # Prediction Component below
    draw_round_rect(d, [260, 420, 440, 480], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((290, 438), "Prediction Inference\nComponent", fill="#1B365D", font=f_b, align="center")
    
    draw_arrow(d, (250, 380), (330, 420), color="#1B365D", width=2)
    draw_arrow(d, (450, 380), (370, 420), color="#1B365D", width=2)
    
    # 3 Evaluation blocks
    eval_blocks = [
        ("Keyword Token\nExplanation Component", (60, 530, 240, 600)),
        ("Multi-Factor Risk\nAssessment Component", (260, 530, 440, 600)),
        ("Substitute Collision\nDetection Component", (460, 530, 640, 600)),
    ]
    
    for title, box in eval_blocks:
        draw_round_rect(d, box, radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
        d.text((box[0] + 15, box[1] + 15), title, fill="#1B365D", font=f_b, align="center")
        draw_arrow(d, (350, 480), (box[0] + 90, box[1]), color="#1B365D", width=2)
        
    # Bottom: Screening Report Component
    draw_round_rect(d, [350, 650, 550, 720], radius=8, fill="#FFFFFF", outline="#1B365D", width=2)
    d.text((380, 672), "Screening Report &\nAudit Log Component", fill="#1B365D", font=f_b, align="center")
    
    draw_arrow(d, (150, 600), (400, 650), color="#1B365D", width=2)
    draw_arrow(d, (350, 600), (450, 650), color="#1B365D", width=2)
    draw_arrow(d, (550, 600), (500, 650), color="#1B365D", width=2)
    
    # Arrow back to UI
    d.line([(550, 685), (760, 685), (760, 60), (660, 60)], fill="#1B365D", width=2)
    draw_arrow(d, (670, 60), (660, 60), color="#1B365D", width=2)
    
    img.save(DIAGRAM_DIR / "diagram_class_component.png", dpi=(300, 300))

# -----------------------------------------------------------------------------
# Run all diagram makers
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    print("Generating all diagrams with Pillow...")
    make_context_diagram()
    print("- Generated System Context Diagram")
    make_ml_pipeline_diagram()
    print("- Generated End-to-End ML Pipeline Diagram")
    make_model_arch_diagram()
    print("- Generated Model Architecture Diagram")
    make_storage_arch_diagram()
    print("- Generated Storage Architecture Diagram")
    make_use_case_diagram()
    print("- Generated Use Case Diagram")
    make_class_component_diagram()
    print("- Generated Class / Component Diagram")
    print("All diagrams generated successfully!")
