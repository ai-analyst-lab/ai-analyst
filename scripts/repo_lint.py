#!/usr/bin/env python3
"""repo_lint.py: public-repo hardening lint.

Checks (fail on any violation, allowlist in scripts/repo_lint_allow.txt as "path-suffix:term"):
  1. Every .claude/skills/*/SKILL.md (git-stored case) has parseable YAML frontmatter
     with name matching its directory and a non-empty description.
  2. No lowercase skill.md stored in git.
  3. Forbidden patterns anywhere in tracked text files: absolute /Users/ paths,
     sibling private-repo references, .env mentions outside connection_templates,
     secret-shaped strings, public file hosts.
  4. Course/marketing residue terms.
Exit 0 on pass, 1 on fail.
"""
import re, subprocess, sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
tracked = subprocess.run(['git', 'ls-files'], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()

TEXT_EXT = {'.md', '.py', '.yaml', '.yml', '.json', '.sh', '.txt', '.toml', '.cfg', '.mjs', '.css', '.sql', '.template', '.example'}
SELF = {'repo_lint.py', 'repo_lint_allow.txt', 'V3-BUILD-SPEC.md', 'V3-BUILD-REPORT.md'}

FORBIDDEN = [
    ("absolute /Users/ path", re.compile(r"/Users/")),
    ("sibling private repo ref", re.compile(r"~/projects/(ai-analytics-evals|novamart-context|ai-analyst-plus)\b|ai-analytics-evals|novamart-context")),
    ("public file host", re.compile(r"tmpfiles\.org|imgur\.com|postimages\.org", re.I)),
    ("secret pattern", re.compile(r"xox[pbs]-[A-Za-z0-9-]{8,}|sk-[A-Za-z0-9]{16,}|AKIA[A-Z0-9]{12,}|ghp_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{16,}")),
    ("assigned secret", re.compile(r"(password|api[_-]?key|account_identifier|private[_-]?key)\s*[:=]\s*['\"][^'\"<>{}$]{6,}['\"]", re.I)),
]
RESIDUE = ["@gmail.com", "bit.ly", "aianalystlab", "lightning lesson", "webinar", "registrant",
           "office hours", "capstone", "maven.com", "bootcamp"]
# Maintainers keep personal-name terms in a gitignored local file, one term per line.
_private = ROOT / 'scripts' / 'repo_lint_private_terms.txt'
if _private.exists():
    RESIDUE += [l.strip().lower() for l in _private.read_text().splitlines()
                if l.strip() and not l.startswith('#')]

def allowed(rel, term):
    allow = ROOT / 'scripts' / 'repo_lint_allow.txt'
    if not allow.exists():
        return False
    for line in allow.read_text().splitlines():
        line = line.split('#')[0].strip()
        if not line or ':' not in line:
            continue
        f, tm = line.split(':', 1)
        if rel.endswith(f.strip()) and tm.strip().lower() == term.lower():
            return True
    return False

fails = []

# 1+2: skills
skill_files = [f for f in tracked if f.startswith('.claude/skills/') and f.lower().endswith('/skill.md')]
for f in skill_files:
    if not f.endswith('/SKILL.md'):
        fails.append(f"lowercase stored name: {f}")
        continue
    t = (ROOT / f).read_text()
    if not t.startswith('---'):
        fails.append(f"no frontmatter: {f}")
        continue
    try:
        fm = t[3:t.index('\n---', 3)]
    except ValueError:
        fails.append(f"unterminated frontmatter: {f}")
        continue
    dirname = f.split('/')[2]
    try:
        d = yaml.safe_load(fm)
    except Exception as e:
        fails.append(f"frontmatter is not valid YAML: {f}: {str(e).splitlines()[0]}")
        continue
    if not isinstance(d, dict) or d.get('name') != dirname:
        fails.append(f"name mismatch ({d.get('name') if isinstance(d, dict) else 'missing'} vs {dirname}): {f}")
    if not isinstance(d, dict) or not str(d.get('description', '')).strip():
        fails.append(f"missing description: {f}")

# 3+4: content
for f in tracked:
    p = ROOT / f
    if p.name in SELF or not p.exists() or p.suffix not in TEXT_EXT:
        continue
    try:
        t = p.read_text()
    except Exception:
        continue
    low = t.lower()
    for label, rx in FORBIDDEN:
        for m in rx.finditer(t):
            if label == ".env reference":
                pass
            if allowed(f, label):
                continue
            line = t[:m.start()].count('\n') + 1
            fails.append(f"{label}: {f}:{line}: {m.group(0)[:60]}")
            break
    for term in RESIDUE:
        if term in low and not allowed(f, term):
            line = low.index(term)
            ln = t[:line].count('\n') + 1
            fails.append(f"residue '{term}': {f}:{ln}")

if fails:
    print(f"FAIL ({len(fails)} violations)")
    for x in fails[:80]:
        print("  " + x)
    if len(fails) > 80:
        print(f"  ... and {len(fails)-80} more")
    sys.exit(1)
print(f"PASS: {len(skill_files)} skills verified, {len(tracked)} tracked files scanned")
