"""Evaluation infrastructure for AI Analyst.

The package keeps model reasoning separate from evaluation mechanics. Skills
describe the student's intention. These helpers own records, isolation,
grading, comparison, and reporting.
"""

from .schema import EvaluationCase, GradeRecord, RunManifest, TrialRecord

__all__ = ["EvaluationCase", "GradeRecord", "RunManifest", "TrialRecord"]
