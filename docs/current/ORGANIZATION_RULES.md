# ORGANIZATION RULES - ENFORCED

**Status:** MANDATORY - No exceptions
**Purpose:** Prevent directory chaos, maintain professional quant infrastructure

---

## ROOT DIRECTORY RULES

### ALLOWED in Root (5 files max)
- `README.md` - Project overview
- `HANDOFF.md` - Current session handoff ONLY
- `SESSION_STATE.md` - Current state ONLY
- `00_START_HERE.md` - Getting started guide
- `AGENTS.md` - Agent usage guide

### BANNED from Root
- ❌ Test scripts (test_*.py)
- ❌ Validation scripts (validate_*.py)
- ❌ Analysis scripts (analyze_*.py)
- ❌ Experimental scripts
- ❌ CSV/JSON results
- ❌ PNG charts
- ❌ Historical documentation
- ❌ Audit reports
- ❌ Multiple versions (v2, final, clean)

**Violation:** Immediate move to appropriate directory

---

## DIRECTORY STRUCTURE

```
/Users/zstoc/rotation-engine/
├── src/                          # Production code ONLY
│   ├── data/                     # Data loaders
│   ├── trading/                  # Trading logic
│   ├── analysis/                 # Analysis tools
│   └── utils/                    # Utilities
├── scripts/                      # Production scripts ONLY
│   └── backtest_with_full_tracking.py  # THE production backtest
├── tests/                        # Unit tests
│   └── test_*.py
├── archive/                      # Historical/experimental
│   ├── experiments/              # Old scripts, tests, validations
│   ├── audits/                   # Historical audit reports
│   └── analysis/                 # Historical analysis docs
├── data/                         # Data files
│   └── backtest_results/         # Results with metadata
├── docs/                         # Documentation
│   ├── current/                  # Current state docs
│   └── archive/                  # Historical docs
├── reports/                      # Generated reports
│   └── backtest_results/         # CSV/JSON results
└── .claude/                      # Configuration
    └── LESSONS_LEARNED.md
```

---

## FILE NAMING RULES

### Production Code
**Format:** `descriptive_name.py`
**Example:** `backtest_with_full_tracking.py`
**Rule:** ONE version only. Git tracks changes, not filenames.

### BANNED Naming Patterns
- ❌ `script_v2.py` (use git, not versions in filename)
- ❌ `final_script.py` (nothing is ever "final")
- ❌ `clean_backtest.py` (implies other versions exist)
- ❌ `simple_test.py` (use proper test structure)
- ❌ `FINAL_regime_test.py` (CAPS + FINAL = disaster)

### Test Scripts
**Format:** `test_<component>.py`
**Location:** `/tests/` directory ONLY
**Example:** `test_execution_model.py`

### Analysis Scripts
**Format:** `analyze_<topic>.py`
**Location:** `/archive/experiments/` or `/scripts/` if production
**Example:** `analyze_peak_timing.py`

---

## RESULT FILES

### Format
**Filename:** `<script>_<date>_<git_hash>.{csv,json}`
**Example:** `backtest_results_2025-11-16_a3f2c9e.json`

### Required Metadata
Every result file must include:
- Git commit hash
- Date/time generated
- Code version/tag
- Parameters used
- Source script

### Location
- `/data/backtest_results/` - Primary storage
- `/reports/` - Generated reports/charts
- **NEVER in root**

---

## DOCUMENTATION RULES

### Current State (docs/current/)
- `VALIDATED_STATE.md` - What's validated/broken
- `ORGANIZATION_RULES.md` - This file
- `ARCHITECTURE.md` - System design
- `DEVELOPMENT_PLAN.md` - What's next

**Rule:** Current state ONLY. Archive historical docs.

### Historical (archive/)
- Audit reports
- Old analysis
- Historical state snapshots
- Session summaries

**Rule:** Move to archive when no longer current.

---

## AGENT-CREATED FILES

### Rule
**ALL agent-created files must specify output location in the prompt.**

**Example:**
```
Create audit report and save to:
/Users/zstoc/rotation-engine/docs/current/AUDIT_REPORT.md
```

**NOT:**
```
Create audit report.
(Agent dumps file in root)
```

### Enforcement
When orchestrating agents:
1. Specify exact file path
2. Verify file goes to correct location
3. Move if agent placed incorrectly

---

## GIT WORKFLOW

### Branches
- `main` - Production-ready code only
- `dev` - Development work
- `experiment/<name>` - Experiments (delete when done)

### Commits
**Message Format:**
```
<type>: <description>

<details>

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**Types:**
- `fix:` - Bug fixes
- `feat:` - New features
- `refactor:` - Code restructuring
- `docs:` - Documentation
- `test:` - Test additions
- `chore:` - Maintenance

### Tags
- `v0.x` - Pre-validation
- `v1.x` - Validated (after all bugs fixed)
- `v2.x` - Production-deployed

**Rule:** Tag after major milestones, not every commit.

---

## SESSION-END CHECKLIST

Before ending ANY session:

### 1. Root Directory Check
```bash
ls -1 *.py *.md *.txt *.csv *.json 2>/dev/null | wc -l
```
**Expected:** ≤5 files (README, HANDOFF, SESSION_STATE, START_HERE, AGENTS)
**Action:** Move any extras to proper locations

### 2. Untracked Files Check
```bash
git status --short | grep "^??" | wc -l
```
**Action:** Commit production code, archive experiments

### 3. Documentation Update
- [ ] HANDOFF.md reflects current session
- [ ] SESSION_STATE.md shows what's working/broken
- [ ] docs/current/VALIDATED_STATE.md is accurate

### 4. Archive Historical
- [ ] Old audit reports moved to archive/audits/
- [ ] Old analysis moved to archive/analysis/
- [ ] Experimental scripts moved to archive/experiments/

---

## ENFORCEMENT

### Automated Checks (Future)
- Pre-commit hook: Block if >5 files in root
- CI check: Verify organization structure
- Session end: Auto-move misplaced files

### Manual Checks (Now)
- Claude verifies at session end
- User spot-checks directory structure
- Immediate cleanup if violations found

---

## WHY THIS MATTERS

**For Quantitative Trading:**
- Must know EXACTLY what code is validated
- Must know EXACTLY what version produced results
- Must trust that production code is production-grade
- Must prevent "quick tests" from polluting results

**For ADHD Management:**
- External structure compensates for executive function
- Clear organization prevents "where did I put that?"
- One source of truth prevents decision paralysis
- Automation prevents forgetting to organize

**For Real Capital:**
- Disorganization = can't trust what's validated
- Can't trust = can't deploy
- Can't deploy = no returns
- Clean infrastructure = confidence to trade

---

## RECOVERY FROM VIOLATIONS

**If root directory has >5 files:**
1. Stop all work immediately
2. Run cleanup protocol (move to archive/)
3. Verify structure matches rules
4. Document what happened in LESSONS_LEARNED.md
5. Resume work

**If experimental code in src/:**
1. Move to archive/experiments/
2. Mark as experimental in docs
3. Identify production version

**If results in root:**
1. Move to data/backtest_results/ or reports/
2. Add metadata (git hash, date, source)
3. Document in backtest metadata file

---

## LESSON LEARNED (2025-11-16)

**What Happened:** 132 files accumulated in root directory over multiple sessions.

**Why:** No organization discipline. "Quick tests" created files everywhere. Never cleaned up after experiments.

**Impact:** Cannot tell what's validated. Cannot trust any results. Complete chaos.

**Fix:** Created this document. Cleaned root (132 → 5 files). Archived historical files.

**Rule:** This NEVER happens again. Organization is NOT optional.

---

**Last Updated:** 2025-11-16
**Status:** ENFORCED - Mandatory for all sessions
**Violations:** Immediate cleanup required
