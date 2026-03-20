# Helper Modules Index

Reusable visualization utilities based on Cole Nussbaumer Knaflic's *Storytelling with Data* methodology:

| File | Purpose |
|------|---------|
| `helpers/chart_helpers.py` | Core: `swd_style()`, `highlight_bar()`, `highlight_line()`, `action_title()`, `annotate_point()`, `save_chart()`. Advanced: `stacked_bar()`, `add_trendline()`, `add_event_span()`, `fill_between_lines()`, `big_number_layout()`, `retention_heatmap()`. Analytical: `sensitivity_table()`, `funnel_waterfall()`, `check_label_collisions()` |
| `helpers/tieout_helpers.py` | Source tie-out: `read_source_direct()` (pandas-only file reader), `profile_dataframe()` (row count, nulls, sums, distinct counts, date ranges), `compare_profiles()` (dual-path comparison with tolerances), `format_tieout_table()`, `overall_status()` |
| `helpers/analytics_chart_style.mplstyle` | Matplotlib style file — warm off-white bg (#F7F6F2), no top/right spines, no grid, sans-serif, 150 DPI |
| `helpers/chart_style_guide.md` | Full SWD reference: color palette, declutter checklist, chart decision tree, anti-patterns, review checklist |
| `helpers/marp_linter.py` | Validates Marp decks: frontmatter completeness, HTML component usage (min 3 types), valid slide classes, slide count, pacing, title collisions. Functions: `lint_deck()`, `format_report()` |
| `helpers/marp_export.py` | Exports Marp decks to PDF and HTML via Marp CLI with theme resolution. Functions: `export_both()`, `check_ready()` |
| `helpers/sql_helpers.py` | SQL sanity checks: `check_join_cardinality()`, `check_percentages_sum()`, `check_date_bounds()`, `check_no_duplicates()`, `warn_temporal_join()`. DQ extensions: `check_temporal_coverage()`, `check_value_domain()`, `check_monotonic()` + safe wrappers |
| `helpers/sql_dialect.py` | SQL dialect router for ClickHouse, Postgres, BigQuery, Snowflake. Use `get_dialect(connection_type)` to get warehouse-specific SQL helpers (date_trunc, safe_divide, etc.) |
| `helpers/connection_manager.py` | Unified interface for multi-warehouse connections (ClickHouse, Postgres, BigQuery, Snowflake) |
| `helpers/schema_profiler.py` | Automated schema discovery and documentation for connected datasets |
| `helpers/stats_helpers.py` | Statistical tests: `two_sample_proportion_test()`, `two_sample_mean_test()`, `mann_whitney_test()`, `confidence_interval()`, `chi_squared_test()`, `bootstrap_ci()`, `format_significance()`, `interpret_effect_size()` |
| `helpers/data_helpers.py` | Data source access: `detect_active_source()`, `check_connection()`, `get_local_connection()`, `read_table()`, `list_tables()`, `get_data_source_info()`. Profiling: `get_connection_for_profiling()`, `schema_to_markdown()` |
| `helpers/analytics_helpers.py` | Analytical utilities for segmentation, decomposition, and driver analysis |
| `helpers/forecast_helpers.py` | Time-series forecasting with trend and seasonality detection |
| `helpers/deep_profiler.py` | Advanced data quality profiling: distributions, correlations, completeness, anomalies |
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
| `helpers/pipeline_state.py` | V1→V2 pipeline state migration: `detect_schema_version()`, `migrate_v1_to_v2()` |
| `helpers/lineage_tracker.py` | Tracks data lineage from source tables through transformations to findings |
| `helpers/theme_loader.py` | Theme loading, caching, deep merge: `load_theme()`, `get_color()`, `list_themes()` |
| `helpers/chart_palette.py` | Theme-aware palettes, WCAG contrast: `apply_theme_colors()`, `palette_for_n()` |
| `helpers/context_loader.py` | Tiered content loading with token budget: `load_tiered()`, `estimate_tokens()` |
| `helpers/schema_migration.py` | Schema migration framework (inert in V2): `migrate_if_needed()` |
| `helpers/examples/` | 4 before/after pairs showing bar, stacked bar, line, and multi-panel transformations |
