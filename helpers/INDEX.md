# Helper Modules Index

Reusable visualization utilities based on Cole Nussbaumer Knaflic's *Storytelling with Data* methodology:

| File | Purpose |
|------|---------|
| `helpers/chart_helpers.py` | Core: `swd_style()`, `highlight_bar()`, `highlight_line()`, `action_title()`, `annotate_point()`, `save_chart()`. Advanced: `stacked_bar()`, `add_trendline()`, `add_event_span()`, `fill_between_lines()`, `big_number_layout()`, `retention_heatmap()`. Analytical: `sensitivity_table()`, `funnel_waterfall()` |
| `helpers/analytics_helpers.py` | Higher-level analytics: `rfm_analysis()`, `concentration_analysis()`, `compare_segments()`, `score_findings()`, `control_chart()`, `synthesize_insights()` |
| `helpers/cross_verification.py` | Cross-verification (Types A-D): `run_boundary_checks()`, `run_parts_to_whole()`, `run_ratio_recompute()`, `run_algebraic_identity()`, `score_cross_verification()`, `score_reproducibility()`, `build_raw_provenance()`, `format_verification_table()`, `safe_run_verification()` |
| `helpers/data_quality_extras.py` | Data quality utilities: `check_null_concentration()`, `check_outliers()`, `safe_check_outliers()` |
| `helpers/tolerance_config.py` | Warehouse-specific tolerance adjustments: `ToleranceConfig` dataclass, `merge_with_base()`, `for_connection_type()` factory, `detect_cost_sensitivity()`, `get_query_budget()` |
| `helpers/reproducibility.py` | Reproducibility checks: `reproducibility_check()` (runs query N times, compares checksums), `diagnose_variance()` (per-warehouse variance detection) |
| `helpers/reliability_stats.py` | Deterministic reliability stats from N independent analysis runs (backs the `/reliability` skill): `parse_number()`, `compute()` (distinct values, range, CV, agreement rate, STABLE/DRIFT verdict), `write_report()`. CLI: `python3 helpers/reliability_stats.py <run_dir>` → writes `stats.json` + `report.md`, appends to `.knowledge/reliability/log.jsonl` |
| `helpers/query_log.py` | Query log utilities: `append_entry()`, `read_log()`, `match_claims()`, `backfill_entry()`, `to_markdown()`, `coverage_report()`. JSONL format at `working/query_log_{dataset}_{date}.jsonl` |
| `helpers/provenance_assembler.py` | Provenance builder: `build_provenance_blocks()`, `build_data_stamp()`, `format_row_count()`, `render_data_stamp()`, `render_provenance_appendix()`. TypedDicts: `DataStamp`, `SQLBlock`, `Methodology`, `CrossVerificationSummary`, `ValidationSummary`, `ReproducibilityInfo`, `ProvenanceBlock` |
| `helpers/analytics_chart_style.mplstyle` | Matplotlib style file — warm off-white bg (#F7F6F2), no top/right spines, no grid, sans-serif, 150 DPI |
| `helpers/chart_style_guide.md` | Full SWD reference: color palette, declutter checklist, chart decision tree, anti-patterns, review checklist |
| `helpers/sql_dialect.py` | Warehouse-specific SQL adapter: `get_dialect(connection_type)` for date_trunc, safe_divide, string functions, etc. Never write raw warehouse-specific SQL — use this adapter. |
| `helpers/sql_helpers.py` | SQL sanity checks: `check_join_cardinality()`, `check_percentages_sum()`, `check_date_bounds()`, `check_no_duplicates()`, `warn_temporal_join()`. DQ extensions: `check_temporal_coverage()`, `check_value_domain()`, `check_monotonic()` + safe wrappers |
| `helpers/forecast_helpers.py` | Time-series forecasting: `naive_forecast()`, `detect_seasonality()`, `exponential_smoothing()` |
| `helpers/schema_profiler.py` | Automated schema discovery: `profile_source()`, `compare_snapshots()`, `discover_relationships()`, `list_sources()`, `get_table_reference()` |
| `helpers/stats_helpers.py` | Statistical tests: `two_sample_proportion_test()`, `two_sample_mean_test()`, `mann_whitney_test()`, `confidence_interval()`, `chi_squared_test()`, `bootstrap_ci()`, `format_significance()`, `interpret_effect_size()` |
| `helpers/connection_manager.py` | Unified multi-warehouse connections (MotherDuck, DuckDB, PostgreSQL, BigQuery, Snowflake): `ConnectionManager()`, `connect()`, `test_connection()`, `list_tables()`, `close()` |
| `helpers/data_helpers.py` | Data source access: `detect_active_source()`, `check_connection()`, `get_local_connection()`, `read_table()`, `list_tables()`, `get_data_source_info()`. Profiling: `get_connection_for_profiling()`, `schema_to_markdown()` |
| `helpers/deep_profiler.py` | Advanced data quality and statistical profiling: `profile_distributions()`, `profile_temporal_patterns()`, `profile_correlations()`, `profile_completeness()`, `profile_anomalies()` |
| `helpers/error_helpers.py` | User-friendly errors: `friendly_error()`, `safe_query()`, `check_empty_dataframe()`, `suggest_column()` |
| `helpers/file_helpers.py` | Atomic writes, content hashing, YAML helpers: `atomic_write()`, `safe_read_yaml()`, `content_hash()`, `has_content_changed()` |
| `helpers/structural_validator.py` | Schema/PK/completeness checks for validation layer 1 |
| `helpers/logical_validator.py` | Aggregation and trend consistency checks for validation layer 2 |
| `helpers/business_rules.py` | Plausibility checks for validation layer 3 |
| `helpers/simpsons_paradox.py` | Simpson's paradox detection for validation layer 4 |
| `helpers/confidence_scoring.py` | A-F confidence grading from 4-layer validation results |
| `helpers/business_validation.py` | Knowledge-backed metric rules and guardrail pairs |
| `helpers/health_check.py` | System health: setup state, knowledge integrity, data connectivity, imports |
| `helpers/metric_validator.py` | Metric definition validation against schema |
| `helpers/entity_resolver.py` | Entity disambiguation across org knowledge |
| `helpers/miss_rate_logger.py` | JSONL miss tracking for knowledge gaps |
| `helpers/business_context.py` | Load org business context: glossary, products, metrics, teams |
| `helpers/archaeology_helpers.py` | Write-side for query archaeology: capture and search cookbook entries |
| `helpers/lineage_tracker.py` | Data lineage tracking through pipeline: `LineageTracker`, `track()`, `get_tracker()`, `record()` |
| `helpers/pipeline_state.py` | V1→V2 pipeline state migration: `detect_schema_version()`, `migrate_v1_to_v2()` |
| `helpers/theme_loader.py` | Theme loading, caching, deep merge: `load_theme()`, `get_color()`, `list_themes()` |
| `helpers/chart_palette.py` | Theme-aware palettes, WCAG contrast: `apply_theme_colors()`, `palette_for_n()` |
| `helpers/context_loader.py` | Tiered content loading with token budget: `load_tiered()`, `estimate_tokens()` |
| `helpers/schema_migration.py` | Schema migration framework (inert in V2): `migrate_if_needed()` |
| `helpers/gdoc_builder.py` | Google Doc builder: `build_readout()` generates .docx Analysis Readout from structured data (python-docx). Handles heading hierarchy, chart embedding, SQL code blocks, bookmark links, figure captions, confidence badge. |
| `helpers/gdoc_narrative_parser.py` | Pipeline artifact parser: `parse_pipeline_outputs()` reads narrative, pipeline summary, validation, close-the-loop, and SQL files → returns `AnalysisData` for `build_readout()`. All files optional. |
| `helpers/marp_export.py` | Marp CLI export wrapper: `export_pdf()`, `export_html()`, `export_both()`, `check_ready()` |
| `helpers/marp_linter.py` | Marp deck validation: `lint_deck()`, `format_report()`. Checks frontmatter, HTML components, CSS classes, slide count, R2/R6 rules, image embedding |
| `helpers/deck_parser.py` | Parses Marp markdown and Google Slides into `SlideObject` dataclass for critique/transform pipelines |
| `helpers/postgres_helpers.py` | PostgreSQL connectivity: `get_postgres_connection()`, `execute_query()`, `test_connection()`, `list_postgres_tables()`, `get_postgres_schema()`, `get_table_row_count()`, `release_connection()`, `close_all_connections()`. Connection pooling, schema introspection, auto-quoting for mixed-case columns. |
| `helpers/examples/` | 4 before/after pairs showing bar, stacked bar, line, and multi-panel transformations |
