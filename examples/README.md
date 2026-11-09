# Example Knowledge Bases

This directory contains pre-configured, production-grade example datasets designed to demonstrate the full capabilities of **AI Knowledge Wrapper** (`akw`), including:

- Multimodal document ingestion (`.docx`, `.pptx`, `.md`).
- Embedded architecture & bioinformatics flowchart extraction into discrete figure chunks.
- Breadcrumb navigation and contiguous $\pm 2$ window chunk retrieval.
- Local vector embeddings and full-text FTS5 BM25 search.
- Discrete SQLite workspace isolation.

---

## Bundled Datasets

### 1. Project Apollo: Autonomous Avionics
- **Focus**: Mission avionics, sensor fusion topologies (IMU, RTK-GPS, LiDAR, optical flow), Extended Kalman Filtering (EKF3), and failsafe recovery envelopes.
- **Documents**:
  - `01_apollo_avionics_architecture.docx`: System specifications, deterministic RTOS partition, CAN bus telemetry rate table, and embedded avionics topology flowchart.
  - `02_flight_safety_specifications.md`: Emergency trigger conditions, lost-link timeouts, geofence containment rules, and ballistic parachute deployment criteria.
  - `03_sensor_telemetry_flow.pptx`: Multi-rotor flight control slides and data interconnect diagrams.
- **Figures / Diagrams**: `apollo_telemetry_flowchart.png` (high-res sensor fusion and actuator pipeline).
- **Suggested Queries**:
  - *"What triggers an emergency recovery mode in Project Apollo?"*
  - *"Explain the sensor fusion architecture and EKF estimation rate."*
  - *"What are the communication timeout specifications for the lost-link failsafe?"*

### 2. BioNexus: Clinical Genomics & Diagnostics
- **Focus**: Next-Generation Sequencing (NGS) workflows, secondary alignment (BWA-MEM), variant calling (GATK, DeepVariant), quality gates (Q30, depth of coverage), and ACMG clinical variant interpretation.
- **Documents**:
  - `01_clinical_genomics_pipeline.docx`: Standard operating procedure, Illumina NovaSeq protocol, duplicate flagging, and embedded clinical sequencing workflow flowchart.
  - `02_acmg_variant_classification.md`: 5-tier classification framework (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4) and pathogenic tiering rules.
  - `03_sequencing_quality_standards.pptx`: Quality acceptance thresholds and clinical diagnostic signoff gates.
- **Figures / Diagrams**: `bionexus_pipeline_diagram.png` (high-res clinical genomics secondary analysis pipeline).
- **Suggested Queries**:
  - *"What are the clinical sequencing quality gates for BioNexus assays?"*
  - *"Explain the ACMG criteria for classifying pathogenic variants (PVS1, PS1)."*
  - *"What alignment and variant calling tools are used in the secondary analysis pipeline?"*

---

## Usage

### Via Web Interface
In the **AI Knowledge Wrapper** web UI, click the **Workspace Selector** in the top navigation bar, expand the menu, and click:
- **🚀 Load Example Knowledge Bases** to import both workspaces.
- **🔄 Reset to Clean Examples** to wipe and re-hydrate fresh workspaces.

### Via CLI
```bash
# List available example datasets
python examples/load_examples.py --list

# Load all example knowledge bases into workspaces
python examples/load_examples.py

# Wipe and reset all workspaces to fresh example sets
python examples/load_examples.py --reset

# Load a specific example
python examples/load_examples.py --example project_apollo
```

Or via the unified `akw` CLI:
```bash
akw examples list
akw examples load --reset
```

