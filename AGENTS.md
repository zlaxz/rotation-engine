# Repository Guidelines

## Project Structure & Module Organization
- `src/` holds production code: `src/data` for loaders/features, `src/regimes` for classifiers, `src/profiles` for scoring logic, and `src/trading` for the simulator plus profile implementations. Keep new modules near the layer they extend.
- `tests/` mirrors the runtime layers (`test_profiles.py`, `test_regimes.py`, `test_simulator_polygon_integration.py`)—add coverage beside the feature you touch.
- `docs/` contains specs (`docs/FRAMEWORK.md`, `docs/BUILD_CHECKLIST.md`); update the relevant doc whenever behavior or assumptions change.
- `scripts/` hosts reproducible notebooks-in-code (e.g., `scripts/statistical_validation.py`) for diagnostics; add new utilities here rather than in ad-hoc notebooks.

## Build, Test, and Development Commands
- `python3 validate_day1.py` … `python3 validate_day5.py`: layer-by-layer integration checks; run the ones covering the files you modify plus `validate_day5.py` before opening a PR.
- `pytest tests` (or a subset like `pytest tests/test_profiles.py -k vanna`): unit/regression suite.
- `python3 scripts/statistical_validation.py --regime TrendUp`: quick sanity analytics when tuning parameters.

## Coding Style & Naming Conventions
- Python 3.10+, 4-space indentation, PEP8 with explicit type hints (see `src/trading/simulator.py` for dataclass-heavy patterns).
- Module names stay snake_case; profile-specific files follow `profile_<n>.py`, and validation scripts follow `validate_day<n>.py`.
- Keep functions pure where possible and capture state via `@dataclass` configs. Document non-obvious math with concise comments above the block—not inline narrations.

## Testing Guidelines
- Prefer `pytest` for fast feedback; integration fixtures in `tests/test_simulator_polygon_integration.py` already mock Polygon data—extend them instead of building new harnesses.
- Name new tests `test_<behavior>_<condition>` so failures read like sentences.
- Target >=90% coverage for touched files; when altering scoring or execution logic, add both a deterministic unit test and a higher-level validation (e.g., extend `validate_day4.py`).

## Commit & Pull Request Guidelines
- Commit messages follow `area: imperative summary`, e.g., `profiles: tighten skew convexity guardrails`. Reference Day/Phase when relevant (`day6:`) to preserve build chronology.
- Stick to focused commits (< ~300 LOC) with passing validations; include before/after metrics when touching performance-sensitive code.
- PRs must describe the change, list impacted validations (e.g., “Ran `validate_day5.py`”), link any issue/Audit doc, and attach plots from `reports/` if visuals changed.

## Security & Data Handling
- Polygon data under `/Volumes/VelocityData/...` is read-only and contains licensed content—never commit raw extracts; rely on loaders.
- Parameter files or secrets belong in environment variables or `.env.local` (ignored); document new knobs in `docs/FRAMEWORK.md`.
