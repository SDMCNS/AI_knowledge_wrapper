# ACMG/AMP Clinical Variant Interpretation Framework

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
