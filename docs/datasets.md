# Dataset contracts and limits

No dataset has been downloaded or evaluated in this repository. Local adapters require caller-supplied files and original dataset/target identity. Public credit benchmarks, extraction benchmarks and synthetic Agrogami records must remain separate experiments.

| Dataset | Original task / implemented local adapter | Boundary |
|---|---|---|
| Default of Credit Card Clients | Default payment next month; explicit CSV feature/target/id mapping | Taiwanese credit-card benchmark, not the project 90-DPD/180-day target. [UCI record](https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients) |
| South German Credit | Original good/bad classification; explicit CSV mapping | Preserve corrected coding documentation and target mapping; not Agrogami loan follow-up. [UCI record](https://archive.ics.uci.edu/dataset/573/south+german+credit+update) |
| FUNSD | Original form entities/links; JSON annotation adapter retains original labels, word boxes and relations | No automatic conversion of question/answer/header labels into financial fields. [Original project](https://guillaumejaume.github.io/FUNSD/) |
| BanglaWriting | Bengali handwriting; normalized local image/transcript manifest adapter | Supplied release, licensing and annotation granularity must be verified. No Bangla accuracy claim. [Dataset paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7744928/) |
| Berka | Original relational financial/loan statuses; normalized risk CSV configuration | Preserve loan-status semantics and original tables/joins. Generic adapter does not reconstruct 90-DPD labels. [Dataset archive](https://github.com/jlacko/berka-dataset) |

`datasets.py` defines DatasetIdentity, RiskDataset, LoanOutcome and document benchmark contracts. CSV callers explicitly declare target mapping, identity column, numeric feature columns and protected columns. No implicit target mapping, categorical encoding, normalization across datasets or download occurs. Missing/nonfinite risk values fail validation; censored labels are excluded from fitting. Source IDs and target columns may not enter the feature matrix.

Research target: Y=1 if an initially current loan reaches at least 90 days past due within 180 days of origination. Positive observed outcomes can be labeled even with short follow-up. Negative requires explicitly complete follow-up through day 180. Incomplete follow-up without an observed qualifying outcome is censored (None), never negative. Not-initially-current loans are outside target scope. Features must be available strictly before decision time. Public benchmark rows must not be relabeled as real linked outcomes.

RiskDataset JSON contains one identity, sample_ids, feature_names, values, binary-or-censored labels, declared protected_columns, and optional aligned decision_times/feature_available_times. Real-linked training requires the exact research target plus temporal metadata. Splits use stable dataset-qualified sample identities; model training, calibration and final evaluation must be disjoint. Multiple loans from one applicant also require applicant-level split governance outside this simple sample-ID check.

TokenSample JSONL contains sample_id, dataset_id, original text, tokens, matching character offsets and BIO labels. DocumentAnnotation JSONL contains sample_id, dataset_id, image (relative to declared data root), optional text, words, normalized 0–1000 boxes and financial BIO labels. TrOCR uses image/text; LayoutLMv3 uses image/words/boxes/labels. Only explicit financial annotations may map benchmark material into that task; generic LayoutLMv3 base weights are not a financial extractor.

BanglaWriting's normalized manifest uses sample_id, image_reference (relative to root) and transcript. FUNSD loads original form JSON via `load_funsd_annotation`; label/relationship identity is retained for separate benchmark evaluation. Berka CSV normalization and joins are a caller-authored experiment with documented availability cutoffs, not an implemented end-to-end underwriting validation.

## Local product scope

UI sample scenarios are invented SYNTHETIC SMS records, not public dataset benchmarks or real provider evidence. Uploaded raster scope is explicitly persisted. Stored evaluation artifacts retain dataset identity/target/scope and are not fabricated to populate UI charts. No public dataset is downloaded by the application/tests.
