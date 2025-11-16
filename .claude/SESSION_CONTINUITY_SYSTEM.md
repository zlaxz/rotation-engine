# SESSION CONTINUITY SYSTEM - Bulletproof Organization

**Created:** 2025-11-16
**Purpose:** Prevent chaos, ensure perfect session-to-session continuity
**Status:** MANDATORY - Follow every session

---

## THE PROBLEM WE'RE SOLVING

**What went wrong:**
- Started sessions "ignorant" (didn't read context)
- Mixed old/new results (no versioning)
- Wrong phase framing (research vs production)
- Contradictory statements (didn't verify data)
- Poor handoffs (no session-to-session notes)

**The solution:** Mandatory protocols that MUST be followed.

---

## MANDATORY SESSION START PROTOCOL

**Execute in order, EVERY session:**

### 1. Check Location & Phase (30 seconds)
```bash
pwd  # Verify we're in /Users/zstoc/rotation-engine
```

Read in this order:
1. `.claude/PROJECT_PHASE.md` - What phase are we in?
2. `.claude/CURRENT_FOCUS.md` - What are we working on?
3. `HANDOFF.md` - What did last session leave for us?

### 2. Load Context (1 minute)

```
Read:
- data/backtest_results/current/METADATA.json (current run info)
- SESSION_STATE.md (first 50 lines - current state section)
- CURRENT_STATE_REPORT.md (if exists)

Query memory:
- search_nodes({query: "rotation_engine project_phase"})
- search_nodes({query: "rotation_engine current_focus"})
```

### 3. Verify Current State (30 seconds)

Ask yourself:
- What phase are we in? (Research/Production/etc)
- What's the current run? (check METADATA.json timestamp)
- What's working? What's broken?
- What are we NOT doing right now?

### 4. Generate Fresh Report (1 minute)

```
If CURRENT_STATE_REPORT.md is stale (>1 day old):
- Regenerate from current/METADATA.json
- Update with latest timestamps
- Present to user with phase context
```

### 5. Present Session Start Summary (present to user)

```markdown
**Session Start**
Phase: [Research/Production/etc]
Current Run: [run_id] ([date])
Working On: [from CURRENT_FOCUS.md]
Last Session: [from HANDOFF.md]

**Current State:**
[2-3 bullet summary from CURRENT_STATE_REPORT.md]

**Ready to continue. What would you like to work on?**
```

**Total time:** 3 minutes
**Mandatory:** YES - Do this EVERY session start

---

## MANDATORY SESSION END PROTOCOL

**Execute in order, EVERY session end:**

### 1. Memory Checkpoint (2 minutes)

Save to MCP memory:
```
What was completed:
- create_entities for work done
- create_entities for decisions made
- create_entities for bugs found/fixed

What was learned:
- Key insights
- Pattern discoveries
- Phase transitions
```

**Don't save:** Every little detail, file operations, routine work

### 2. Update Documentation (3 minutes)

Update in order:
```
1. PROJECT_PHASE.md (if phase changed)
2. CURRENT_FOCUS.md (what we're working on now)
3. SESSION_STATE.md (update "Current Results" section)
4. HANDOFF.md (create fresh for next session)
```

### 3. Archive Old Results (if applicable)

```
If new backtest run created:
- Move to data/backtest_results/runs/YYYYMMDD_HHMM_description/
- Create METADATA.json
- Update current/ symlink
- Archive validation reports to same timestamped directory
```

### 4. Create HANDOFF.md

```markdown
# HANDOFF - Session [Date]

**Completed This Session:**
- [What was finished]

**Current State:**
- Phase: [research/production/etc]
- Working: [what's functional]
- Broken: [what's not working]

**Next Session Priorities:**
1. [First thing to do]
2. [Second thing]
3. [Third thing]

**Context:**
- Current run: [run_id from current/METADATA.json]
- Key decisions: [any important choices made]
- Blockers: [anything preventing progress]
```

### 5. Present Session End Summary (to user)

```markdown
**Session End**
Completed: [brief summary]
Memory saved: [N entities]
Documentation updated: [list files]

Next session will start with: [from HANDOFF.md]

Would you like me to create a git commit?
```

**Total time:** 5 minutes
**Mandatory:** YES - Do this EVERY session end

---

## FILE ORGANIZATION STRUCTURE

```
/Users/zstoc/rotation-engine/
├── .claude/
│   ├── CLAUDE.md                    # Project config
│   ├── PROJECT_PHASE.md             # Current phase (research/production)
│   ├── CURRENT_FOCUS.md             # What we're working on NOW
│   └── SESSION_CONTINUITY_SYSTEM.md # This file
│
├── data/
│   └── backtest_results/
│       ├── runs/
│       │   ├── YYYYMMDD_HHMM_description/
│       │   │   ├── METADATA.json    # Run context
│       │   │   ├── results.json     # Raw data
│       │   │   └── SUMMARY.txt      # Human readable
│       │   └── ...
│       ├── current -> runs/latest/  # Symlink
│       └── RESULTS_VERSIONING_SYSTEM.md
│
├── SESSION_STATE.md                 # Project state (git-tracked)
├── CURRENT_STATE_REPORT.md          # Regenerated each session
├── HANDOFF.md                       # Session-to-session notes
└── [project files...]
```

---

## WHAT GOES WHERE

### PROJECT_PHASE.md
**Purpose:** Track current phase, prevent wrong framing
**Update:** When phase changes
**Contains:**
- Current phase (Phase 3: Analyze Traces)
- What we're doing
- What we're NOT doing
- Language standards for this phase

### CURRENT_FOCUS.md
**Purpose:** Track immediate work focus
**Update:** When focus changes (not every detail)
**Contains:**
- Current task
- Why we're doing it
- What success looks like
- Expected next steps

### SESSION_STATE.md
**Purpose:** Project-wide state (git-tracked)
**Update:** Session end, major milestones
**Contains:**
- Current Results section (run_id, date, summary)
- What's working
- What's broken
- What's in progress
- Critical rules

### HANDOFF.md
**Purpose:** Session-to-session continuity
**Update:** Every session end
**Contains:**
- What was completed
- Next priorities
- Context for next session
- Blockers

### CURRENT_STATE_REPORT.md
**Purpose:** Fresh summary for session start
**Update:** Regenerate each session start (if stale)
**Contains:**
- Current run summary
- Phase context
- What's working/broken
- Next options

---

## MEMORY SAVE STRATEGY

### What TO Save

✅ **Major work completed:**
- "Built trade tracking system (604 traces)"
- "Fixed Profile 5 entry bug (slope requirement)"

✅ **Key decisions:**
- "Decided 14-day window is measurement, not exit strategy"
- "Chose to analyze traces before building exits"

✅ **Bugs found/fixed:**
- "Profile 6 IV_rank condition was inverted"

✅ **Phase transitions:**
- "Moved from Phase 2 (tracking) to Phase 3 (analysis)"

✅ **Pattern discoveries:**
- "85% of entries find positive peaks (vs 50% random)"
- "Peak timing averages 6 days (not 14)"

### What NOT To Save

❌ **Routine operations:**
- File reads/writes
- bash commands
- Search queries

❌ **Every little detail:**
- Each file modified
- Each test run
- Every conversation turn

❌ **Transient analysis:**
- Temporary observations
- Work-in-progress thoughts

**Rule:** If it's valuable across sessions, save it. If it's transient, skip it.

---

## VERIFICATION PROTOCOL

**Before presenting ANY results, run this checklist:**

### Checklist:
- [ ] What phase are we in? (checked PROJECT_PHASE.md)
- [ ] When was this data created? (checked file timestamp)
- [ ] What run does this belong to? (checked METADATA.json)
- [ ] Is there newer data? (checked current/ symlink)
- [ ] Am I framing this correctly for the phase? (research vs production)
- [ ] Are my timestamps explicit? (included run_id and date)

**If ANY checkbox is unchecked: STOP and verify before presenting.**

---

## LANGUAGE STANDARDS BY PHASE

### Phase 3: Research (Analyzing Traces)

**✅ Use:**
- "Entries find opportunities (85% positive peaks)"
- "Peak timing averages 6 days"
- "Observing lifecycle patterns"
- "14-day observation window"
- "What do the traces show?"

**❌ Avoid:**
- "Exit system is broken"
- "Not viable for deployment"
- "Need to fix exits"
- Statistical significance tests
- Production deployment language

### Phase 5: Validation (when we get there)

**✅ Use:**
- "Statistical significance: p=X"
- "Walk-forward validation"
- "Deployment viability"
- "Transaction cost analysis"

**❌ Avoid:**
- Using validation language in research phase

---

## EMERGENCY PROTOCOL

**If user says "you're being ignorant" or "wrong framing":**

1. **STOP immediately**
2. **Read PROJECT_PHASE.md**
3. **Ask user: "What phase are we in? What should I be focusing on?"**
4. **Update documentation with correct framing**
5. **Save to memory: What I got wrong**
6. **Add to LESSONS_LEARNED.md if new pattern**

---

## SUCCESS METRICS

**Session continuity is working if:**

✅ User doesn't have to explain context every session
✅ I never mix old/new results
✅ I frame work correctly for current phase
✅ I present results with timestamps and run_ids
✅ Documentation matches reality
✅ Handoffs are clear and actionable

**Session continuity is FAILING if:**

❌ User says "you're ignorant" or "you're confused"
❌ I present contradictory statements
❌ I mix validation reports with research data
❌ I frame research as production
❌ I can't tell user what phase we're in

---

## IMPLEMENTATION CHECKLIST

**To implement this system (one-time setup):**

- [x] Create PROJECT_PHASE.md
- [x] Create SESSION_CONTINUITY_SYSTEM.md
- [ ] Create CURRENT_FOCUS.md
- [ ] Create HANDOFF.md (session end)
- [x] Update SESSION_STATE.md (current results section)
- [ ] Update global ~/.claude/CLAUDE.md (add session start/end protocol reference)
- [x] Add to LESSONS_LEARNED.md (LESSON 8 & 9)
- [x] Save to memory (project phase, continuity system)

**Status:** Partially implemented - complete remaining items now

---

**This system is MANDATORY. Follow it EVERY session.**
