"""Utility script to generate realistic example datasets for Project Apollo and BioNexus Diagnostics."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import docx
from docx.shared import Inches, Pt, RGBColor
from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.dml.color import RGBColor as PptxRGBColor


def draw_rounded_rect(draw, coords, fill, outline, width=2, radius=12):
    x0, y0, x1, y1 = coords
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=fill, outline=outline, width=width)


def create_apollo_diagram(output_path: Path):
    """Generate high-resolution architecture diagram for Project Apollo."""
    width, height = 1200, 650
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, width, 70], fill=(30, 41, 59))  # slate-800
    draw.text((40, 22), "PROJECT APOLLO // AVIONICS & SENSOR FUSION TOPOLOGY", fill=(56, 189, 248))

    # Boxes definitions: (x, y, w, h, title, subtitle, color_accent)
    nodes = [
        (60, 130, 280, 140, "Primary IMU & GPS Arrays", "Dual Redundant IMU (1000Hz)\nRTK-GNSS + Barometric Altimeter", (14, 165, 233)),
        (60, 320, 280, 140, "Optical Flow & LiDAR", "Downfacing ToF LiDAR Rangefinder\nStereo Optical Flow Camera (60fps)", (56, 189, 248)),
        (460, 200, 300, 200, "Extended Kalman Filter (EKF3)", "State Estimation Core (400Hz)\nAttitude, Position & Velocity Fusion\nOutlier Rejection & Covariance Check", (129, 140, 248)),
        (880, 130, 260, 140, "Motor ESC & Actuators", "8x DShot1200 BLDC ESCs\nActive Braking & RPM Feedback", (52, 211, 153)),
        (880, 320, 260, 140, "Failsafe Recovery Unit", "Autonomous Parachute Ejection\nEmergency Motor Cutoff Relay", (244, 63, 94)),
        (460, 480, 300, 110, "Telemetry Uplink / Downlink", "Encrypted Dual-Band UHF (915MHz)\nLTE Telemetry Relay & MAVLink Stream", (251, 146, 60)),
    ]

    for x, y, w, h, title, sub, accent in nodes:
        draw_rounded_rect(draw, (x, y, x + w, y + h), fill=(30, 41, 59), outline=accent, width=2)
        # Accent top bar
        draw.rounded_rectangle([x + 2, y + 2, x + w - 2, y + 8], radius=3, fill=accent)
        draw.text((x + 16, y + 20), title, fill=(241, 245, 249))
        draw.text((x + 16, y + 55), sub, fill=(148, 163, 184))

    # Arrows between nodes
    # IMU -> EKF
    draw.line([(340, 200), (460, 250)], fill=(56, 189, 248), width=3)
    # Optical -> EKF
    draw.line([(340, 390), (460, 320)], fill=(56, 189, 248), width=3)
    # EKF -> ESC
    draw.line([(760, 260), (880, 200)], fill=(52, 211, 153), width=3)
    # EKF -> Failsafe
    draw.line([(760, 330), (880, 380)], fill=(244, 63, 94), width=3)
    # EKF <-> Telemetry
    draw.line([(610, 400), (610, 480)], fill=(251, 146, 60), width=3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")


def create_bionexus_diagram(output_path: Path):
    """Generate high-resolution bioinformatics pipeline schema for BioNexus."""
    width, height = 1200, 650
    img = Image.new("RGB", (width, height), color=(15, 23, 42))  # slate-900
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, width, 70], fill=(30, 41, 59))
    draw.text((40, 22), "BIONEXUS CLINICAL GENOMICS // SECONDARY ANALYSIS & ACMG PIPELINE", fill=(52, 211, 153))

    steps = [
        (50, 160, 180, 280, "Stage 1: Sample & Prep", "Illumina NovaSeq 6000\nPaired-End 2x150bp\nTarget: >100x Coverage\nQuality Gate: Q30 >= 85%", (16, 185, 129)),
        (280, 160, 180, 280, "Stage 2: Alignment", "Fastp Adapter Trimming\nBWA-MEM v0.7.17 (GRCh38)\nSamtools Sort & Index\nMarkDuplicates (Picard)", (14, 165, 233)),
        (510, 160, 180, 280, "Stage 3: Variant Calling", "GATK HaplotypeCaller 4.4\nDeepVariant v1.6 (CNN)\nJoint Genotyping & BQSR\nVCF / gVCF Emission", (129, 140, 248)),
        (740, 160, 180, 280, "Stage 4: Annotation", "Ensembl VEP v112\ngnomAD Population AF\nClinVar Pathogenicity\nAlphaGenome Impact Score", (244, 114, 182)),
        (970, 160, 180, 280, "Stage 5: Interpretation", "ACMG 5-Tier Classification:\n- Pathogenic (PVS1, PS1)\n- Likely Pathogenic\n- VUS (Class 3)\n- Benign / Likely Benign", (251, 146, 60)),
    ]

    for x, y, w, h, title, sub, accent in steps:
        draw_rounded_rect(draw, (x, y, x + w, y + h), fill=(30, 41, 59), outline=accent, width=2)
        draw.rounded_rectangle([x + 2, y + 2, x + w - 2, y + 8], radius=3, fill=accent)
        draw.text((x + 12, y + 20), title, fill=(241, 245, 249))
        draw.text((x + 12, y + 65), sub, fill=(148, 163, 184))

    # Connect consecutive stages with arrows
    for i in range(len(steps) - 1):
        x1 = steps[i][0] + steps[i][2]
        y1 = 300
        x2 = steps[i + 1][0]
        y2 = 300
        draw.line([(x1, y1), (x2, y2)], fill=(226, 232, 240), width=4)
        # arrowhead
        draw.polygon([(x2, y2), (x2 - 10, y2 - 6), (x2 - 10, y2 + 6)], fill=(226, 232, 240))

    # Bottom SLA compliance banner
    draw_rounded_rect(draw, (50, 480, 1150, 580), fill=(24, 33, 47), outline=(71, 85, 105), width=1)
    draw.text((70, 500), "CLINICAL QUALITY ASSURANCE & REGULATORY COMPLIANCE", fill=(241, 245, 249))
    draw.text((70, 530), "CAP/CLIA Compliant Automated Run Verification - Mean coverage depth >= 100x required for diagnostic signoff.", fill=(148, 163, 184))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")


def generate_apollo_dataset(base_dir: Path):
    """Generate all files for Project Apollo dataset."""
    pkg_dir = base_dir / "project_apollo"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = pkg_dir / "assets"
    docs_dir = pkg_dir / "documents"
    assets_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Diagram Image
    diagram_img = assets_dir / "apollo_telemetry_flowchart.png"
    create_apollo_diagram(diagram_img)

    # 2. Metadata
    metadata = {
        "id": "project_apollo",
        "name": "Project Apollo: Autonomous Avionics",
        "description": "Avionics system specifications, telemetry pipelines, and safety envelope criteria for autonomous aerial vehicles.",
        "tags": ["aerospace", "avionics", "telemetry", "failsafe", "kalman-filter"],
        "sample_queries": [
            "What triggers an emergency recovery mode in Project Apollo?",
            "Explain the sensor fusion architecture and EKF estimation rate.",
            "What are the communication timeout specifications for the lost-link failsafe?",
            "Describe the motor ESC array and braking specifications.",
        ],
    }
    (pkg_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # 3. DOCX with embedded diagram
    doc = docx.Document()
    title_p = doc.add_heading("Project Apollo: Autonomous Avionics Platform", level=0)
    doc.add_paragraph(
        "Project Apollo defines the reference mission avionics, real-time sensor fusion topologies, "
        "and deterministic safety envelopes for heavy-payload autonomous aerial systems."
    )

    doc.add_heading("1. Flight Control & Core Hardware Architecture", level=1)
    doc.add_paragraph(
        "The flight control unit is powered by a triple-core Cortex-M7 microcontroller operating at 480 MHz. "
        "All critical flight guidance loops run within a deterministic RTOS partition guaranteed at 1000 Hz. "
        "Dual isolated power distribution buses supply independent 5V regulated rails to redundant flight sensors."
    )

    doc.add_heading("2. High-Rate Telemetry & Sensor Fusion Architecture", level=1)
    doc.add_paragraph(
        "The sensor fusion subsystem combines redundant 3-axis gyroscopes, accelerometers, RTK-GNSS positioning, "
        "and downward-facing optical flow. The fusion pipeline is structured as shown in Figure 1 below:"
    )

    # Embed diagram into DOCX
    doc.add_picture(str(diagram_img), width=Inches(6.0))
    caption = doc.add_paragraph("Figure 1: Apollo High-Reliability Avionics & Telemetry Topology Flowchart.")
    caption.runs[0].font.italic = True
    caption.runs[0].font.size = Pt(9)

    doc.add_paragraph(
        "Sensor measurements from the dual IMU array are fed into an Extended Kalman Filter (EKF3) "
        "at 400 Hz to generate real-time estimates of attitude, position, and velocity."
    )

    doc.add_heading("3. Redundant CAN Bus Communication Protocol", level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Message ID"
    hdr_cells[1].text = "Rate (Hz)"
    hdr_cells[2].text = "Priority"
    hdr_cells[3].text = "Payload Description"

    specs = [
        ("0x101", "1000", "Critical", "Raw IMU Accelerometer and Gyroscope vectors"),
        ("0x204", "400", "High", "Fused EKF Attitude & Velocity State Vector"),
        ("0x308", "50", "Medium", "RTK-GNSS Dilution of Precision & Satellite Fix"),
        ("0x410", "10", "Low", "Battery Cell Voltages, Current Draw & Pack Temp"),
    ]
    for msg_id, rate, prio, desc in specs:
        row_cells = table.add_row().cells
        row_cells[0].text = msg_id
        row_cells[1].text = rate
        row_cells[2].text = prio
        row_cells[3].text = desc

    doc.save(docs_dir / "01_apollo_avionics_architecture.docx")

    # 4. Markdown Document (Flight Safety Envelope)
    safety_md = """# Apollo Flight Envelope & Safety Verification Guidelines

## 1. Emergency Failsafe Trigger Conditions
The autonomous flight supervisory monitor continuously evaluates system telemetry against hard safety constraints. A transition to an emergency recovery state is triggered when any of the following parameters are breached:

1. **Lost Link Timeout**: Absence of valid telemetry heartbeat packets across both primary UHF (915 MHz) and LTE cellular channels for more than **1500 ms**.
2. **Critical Low Battery (Voltage Floor)**: Total battery bus voltage dropping below **18.2 V** under load for greater than 3.0 continuous seconds.
3. **Severe Sensor Divergence**: Innovation residuals between primary and secondary IMU vectors exceeding 3.5 standard deviations for more than 50 consecutive milliseconds.
4. **Attitude Loss-of-Control**: Pitch exceeding ±45 degrees or roll exceeding ±60 degrees without operator stick deflection.

## 2. Geofence Containment Protocols
- **Inclusion Geofence**: All flight trajectories must remain within the pre-cleared polygon.
- **Buffer Zone**: A 50-meter warning perimeter triggers automatic speed restriction to a maximum of 5.0 m/s.
- **Hard Breach Action**: Crossing the physical inclusion perimeter immediately disengages autonomous cruise and executes an emergency Return-to-Home (RTH) path at a minimum altitude of 60 meters above ground level.

## 3. Autonomous Parachute Deployment Envelope
In the event of unrecoverable catastrophic motor or structural failure, the autonomous ballistic parachute is ejected via pyrotechnic initiator under the following conditions:
- Vertical descent rate exceeds **12.0 m/s** downward velocity while barometric altimeter registers altitude > 25 meters AGL.
- Total vehicle inverted roll orientation lasting longer than 400 milliseconds below 100 meters altitude.
"""
    (docs_dir / "02_flight_safety_specifications.md").write_text(safety_md, encoding="utf-8")

    # 5. PPTX Presentation (Sensor Telemetry Flow)
    prs = Presentation()
    prs.slide_width = PptxInches(10.0)
    prs.slide_height = PptxInches(5.625)

    blank_layout = prs.slide_layouts[6]
    slide1 = prs.slides.add_slide(blank_layout)

    tb = slide1.shapes.add_textbox(PptxInches(0.8), PptxInches(0.6), PptxInches(8.4), PptxInches(1.2))
    p = tb.text_frame.add_paragraph()
    p.text = "Project Apollo: Mission Avionics Overview"
    p.font.size = PptxPt(28)
    p.font.bold = True
    p.font.color.rgb = PptxRGBColor(15, 23, 42)

    p2 = tb.text_frame.add_paragraph()
    p2.text = "High-Reliability Multi-Rotor Autonomous Guidance System"
    p2.font.size = PptxPt(16)
    p2.font.color.rgb = PptxRGBColor(100, 116, 139)

    # Slide 2: Diagram slide
    slide2 = prs.slides.add_slide(blank_layout)
    tb2 = slide2.shapes.add_textbox(PptxInches(0.8), PptxInches(0.4), PptxInches(8.4), PptxInches(0.8))
    p_s2 = tb2.text_frame.add_paragraph()
    p_s2.text = "Avionics Interconnect & Actuator Data Bus"
    p_s2.font.size = PptxPt(22)
    p_s2.font.bold = True

    slide2.shapes.add_picture(
        str(diagram_img),
        PptxInches(0.8),
        PptxInches(1.3),
        width=PptxInches(8.4),
        height=PptxInches(3.8),
    )

    prs.save(docs_dir / "03_sensor_telemetry_flow.pptx")


def generate_bionexus_dataset(base_dir: Path):
    """Generate all files for BioNexus Diagnostics dataset."""
    pkg_dir = base_dir / "bionexus_diagnostics"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = pkg_dir / "assets"
    docs_dir = pkg_dir / "documents"
    assets_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Diagram Image
    diagram_img = assets_dir / "bionexus_pipeline_diagram.png"
    create_bionexus_diagram(diagram_img)

    # 2. Metadata
    metadata = {
        "id": "bionexus_diagnostics",
        "name": "BioNexus: Clinical Genomics & Diagnostics",
        "description": "Standard operating procedures, bioinformatics secondary analysis pipelines, and ACMG clinical variant interpretation rules.",
        "tags": ["genomics", "bioinformatics", "acmg", "next-gen-sequencing", "clinical-diagnostics"],
        "sample_queries": [
            "What are the clinical sequencing quality gates for BioNexus assays?",
            "Explain the ACMG criteria for classifying pathogenic variants (PVS1, PS1).",
            "What alignment and variant calling tools are used in the secondary analysis pipeline?",
            "How are gnomAD population allele frequency cutoffs applied in variant filtering?",
        ],
    }
    (pkg_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # 3. DOCX with embedded diagram
    doc = docx.Document()
    doc.add_heading("BioNexus Clinical Genomics Platform: Standard Operating Procedure", level=0)
    doc.add_paragraph(
        "This document describes the secondary bioinformatics analysis, alignment standards, "
        "and automated variant filtration criteria used in BioNexus diagnostic assays."
    )

    doc.add_heading("1. High-Throughput Sequencing Pipeline Overview", level=1)
    doc.add_paragraph(
        "Raw sequencing data is generated on Illumina NovaSeq 6000 platforms using 2x150 bp paired-end chemistry. "
        "The standard diagnostic pipeline workflow from raw reads to clinical interpretation is shown in Figure 1 below:"
    )

    doc.add_picture(str(diagram_img), width=Inches(6.0))
    caption = doc.add_paragraph("Figure 1: BioNexus Clinical Sequencing & ACMG Variant Interpretation Flowchart.")
    caption.runs[0].font.italic = True
    caption.runs[0].font.size = Pt(9)

    doc.add_heading("2. Primary Alignment & Secondary Variant Calling", level=1)
    doc.add_paragraph(
        "Raw FASTQ reads undergo adapter trimming and poly-G tail clipping with fastp. "
        "Filtered reads are aligned to the GRCh38 human reference genome using BWA-MEM (v0.7.17). "
        "Duplicate reads are flagged with Picard MarkDuplicates, followed by Base Quality Score Recalibration (BQSR). "
        "Single nucleotide variants (SNVs) and small insertions/deletions (indels) are called using GATK HaplotypeCaller 4.4 "
        "in conjunction with DeepVariant v1.6 for orthogonal cross-validation."
    )

    doc.add_heading("3. Quality Control Standards for Diagnostic Release", level=1)
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Quality Metric"
    hdr_cells[1].text = "Acceptance Threshold"
    hdr_cells[2].text = "Action on Failure"
    hdr_cells[3].text = "Clinical Impact"

    specs = [
        ("Base Quality (Q30)", ">= 85.0% of bases", "Re-sequence flowcell lane", "Minimizes false positive calls"),
        ("Mean Target Depth", ">= 100x coverage", "Top-up library sequencing", "Ensures high detection sensitivity"),
        ("20x Target Coverage", ">= 98.5% of target bases", "Inspect target capture gaps", "Guarantees complete exon view"),
        ("Transition/Transversion (Ti/Tv)", "2.0 - 2.2 (Exome)", "Bioinformatics QC flag", "Verifies overall callset purity"),
    ]
    for metric, thresh, action, impact in specs:
        row_cells = table.add_row().cells
        row_cells[0].text = metric
        row_cells[1].text = thresh
        row_cells[2].text = action
        row_cells[3].text = impact

    doc.save(docs_dir / "01_clinical_genomics_pipeline.docx")

    # 4. Markdown Document (ACMG Variant Classification Rules)
    acmg_md = """# ACMG/AMP Clinical Variant Interpretation Framework

## 1. Pathogenic Evidence Criteria (5-Tier Framework)
Variants identified in diagnostic sequencing assays are evaluated in accordance with the ACMG/AMP clinical guidelines:

- **PVS1 (Pathogenic Very Strong)**: Null variant (nonsense, frameshift, canonical ±1 or 2 splice sites, initiation codon, single or multi-exon deletion) in a gene where loss of function (LoF) is an established mechanism of disease.
- **PS1 (Pathogenic Strong)**: Same amino acid change as a previously established pathogenic variant regardless of nucleotide change.
- **PS2 (De Novo)**: De novo mutation (with parental identity confirmed) in a patient with the disease and no family history.
- **PM2 (Pathogenic Moderate)**: Absent from controls (or at extremely low frequency if recessive) in ExAC/gnomAD population cohorts (allele frequency < 0.00005).
- **PP3 (Pathogenic Supporting)**: Multiple lines of computational evidence support a deleterious effect on the gene or gene product (REVEL score > 0.75, AlphaGenome impact > 0.8).

## 2. Benign Evidence Criteria
- **BA1 (Stand-Alone Benign)**: Allele frequency is greater than 5.0% in the ExAC or gnomAD population databases.
- **BS1 (Benign Strong)**: Allele frequency is greater than expected for disorder.
- **BS2 (Benign Strong)**: Observed in healthy adult individuals for a recessive (homozygous) or dominant (heterozygous) condition with full penetrance.

## 3. Final Pathogenicity Combinations
A variant is classified as:
- **Pathogenic**: 1 Very Strong (PVS1) AND at least 1 Strong (PS1-PS4), OR 2 Strong criteria.
- **Likely Pathogenic**: 1 Very Strong AND 1 Moderate, OR 1 Strong AND 1-2 Moderate.
- **Variant of Uncertain Significance (VUS)**: Conflicting criteria or insufficient evidence.
"""
    (docs_dir / "02_acmg_variant_classification.md").write_text(acmg_md, encoding="utf-8")

    # 5. PPTX Presentation (Sequencing Quality Gates)
    prs = Presentation()
    prs.slide_width = PptxInches(10.0)
    prs.slide_height = PptxInches(5.625)
    blank_layout = prs.slide_layouts[6]

    slide1 = prs.slides.add_slide(blank_layout)
    tb = slide1.shapes.add_textbox(PptxInches(0.8), PptxInches(0.6), PptxInches(8.4), PptxInches(1.2))
    p = tb.text_frame.add_paragraph()
    p.text = "BioNexus: Clinical Sequencing Quality Gates"
    p.font.size = PptxPt(28)
    p.font.bold = True
    p.font.color.rgb = PptxRGBColor(15, 23, 42)

    p2 = tb.text_frame.add_paragraph()
    p2.text = "CAP / CLIA Compliant Secondary Analysis & ACMG Tiering"
    p2.font.size = PptxPt(16)
    p2.font.color.rgb = PptxRGBColor(100, 116, 139)

    slide2 = prs.slides.add_slide(blank_layout)
    tb2 = slide2.shapes.add_textbox(PptxInches(0.8), PptxInches(0.4), PptxInches(8.4), PptxInches(0.8))
    p_s2 = tb2.text_frame.add_paragraph()
    p_s2.text = "Automated Secondary Pipeline Workflow"
    p_s2.font.size = PptxPt(22)
    p_s2.font.bold = True

    slide2.shapes.add_picture(
        str(diagram_img),
        PptxInches(0.8),
        PptxInches(1.3),
        width=PptxInches(8.4),
        height=PptxInches(3.8),
    )

    prs.save(docs_dir / "03_sequencing_quality_standards.pptx")


def main():
    base_dir = Path("examples/datasets").resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating example datasets in: {base_dir}")
    generate_apollo_dataset(base_dir)
    print("✓ Generated Project Apollo dataset with diagram, docx, md, and pptx.")
    generate_bionexus_dataset(base_dir)
    print("✓ Generated BioNexus Diagnostics dataset with diagram, docx, md, and pptx.")


if __name__ == "__main__":
    main()

