# SESSION START/END CHECKLIST

**Purpose:** Quick reference for mandatory protocols
**Use:** Check off items as you complete them

---

## 📋 SESSION START CHECKLIST

Execute in order:

- [ ] **Check location:** `pwd` (verify in project directory)
- [ ] **Read PROJECT_PHASE.md** (what phase are we in?)
- [ ] **Read CURRENT_FOCUS.md** (what are we working on?)
- [ ] **Read HANDOFF.md** (what did last session leave?)
- [ ] **Read current/METADATA.json** (what run is current?)
- [ ] **Query memory:** `search_nodes({query: "rotation_engine project_phase"})`
- [ ] **Verify phase:** Am I clear on research vs production?
- [ ] **Check for stale report:** Is CURRENT_STATE_REPORT.md > 1 day old?
- [ ] **Present session start summary** to user with phase context

**Time:** 3 minutes
**If rushed:** Minimum: Read PROJECT_PHASE.md, HANDOFF.md

---

## 📋 SESSION END CHECKLIST

Execute in order:

- [ ] **Save memory entities:**
  - Work completed (what was finished)
  - Decisions made (key choices with rationale)
  - Bugs found/fixed (if any)
  - Phase transitions (if changed)

- [ ] **Update documentation:**
  - [ ] PROJECT_PHASE.md (if phase changed)
  - [ ] CURRENT_FOCUS.md (if focus changed)
  - [ ] SESSION_STATE.md (update "Current Results" section)
  - [ ] Create HANDOFF.md (fresh for next session)

- [ ] **Archive results (if applicable):**
  - [ ] New run to timestamped directory
  - [ ] Create METADATA.json
  - [ ] Update current/ symlink

- [ ] **Present session end summary** to user

**Time:** 5 minutes
**If rushed:** Minimum: Update HANDOFF.md, save key memory entities

---

## ✅ VERIFICATION CHECKLIST

**Before presenting ANY results, verify:**

- [ ] What phase are we in? (checked PROJECT_PHASE.md)
- [ ] When was this data created? (checked timestamp)
- [ ] What run does this belong to? (checked METADATA.json)
- [ ] Is there newer data? (checked current/ symlink)
- [ ] Am I framing correctly for phase? (research vs production)
- [ ] Are timestamps explicit? (included run_id and date)

**If ANY is unchecked:** STOP. Verify before presenting.

---

## 🚨 EMERGENCY PROTOCOL

**If user says: "you're confused" / "wrong framing" / "being ignorant"**

1. **STOP immediately**
2. **Read PROJECT_PHASE.md**
3. **Ask:** "What phase are we in? What should I focus on?"
4. **Update:** Documentation with correct framing
5. **Save:** Memory entity about what I got wrong
6. **Add:** To LESSONS_LEARNED.md if new pattern

---

## Quick Commands

```bash
# Session start
cat .claude/PROJECT_PHASE.md
cat .claude/CURRENT_FOCUS.md
cat HANDOFF.md
cat data/backtest_results/current/METADATA.json

# Check current state
cat SESSION_STATE.md | head -50

# Session end
# (Update files, then create HANDOFF.md)
```
