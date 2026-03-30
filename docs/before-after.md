# Before/After: Why Governed Memory Matters

A concrete example of what goes wrong without governance, and how agentmem fixes it.

## The Scenario

You're building a web app. Over 3 weeks, your AI assistant accumulates memories about your audio processing pipeline. Some are current. Some are outdated. Some contradict each other.

## Before: Ungoverned Memory

Your agent stores everything it learns. No status, no provenance, no lifecycle.

```python
from agentmem import Memory

mem = Memory("./ungoverned.db")

# Week 1: You discover a bug
mem.add(type="bug", title="loudnorm breaks voice quality",
        content="loudnorm on voice files lifts the noise floor. Audio sounds robotic.")

# Week 1: You set a rule
mem.add(type="decision", title="Audio normalization policy",
        content="Always apply loudnorm to voice audio before mixing.")

# Week 3: You fix the approach
mem.add(type="decision", title="Updated audio policy",
        content="Never apply loudnorm to voice audio. Use per-track volume instead.")
```

**What happens when the agent recalls "how to process audio"?**

```python
context = mem.recall("audio processing voice normalization", max_tokens=2000)
```

The agent gets back ALL THREE memories. The week 1 rule says "always apply loudnorm." The week 3 rule says "never apply loudnorm." The agent picks one at random — or worse, tries to follow both.

**Your agent just repeated a bug you already fixed.**

## After: Governed Memory

Same scenario, but with lifecycle management.

```python
from agentmem import Memory

mem = Memory("./governed.db")

# Week 1: Store the bug
bug = mem.add(type="bug", title="loudnorm breaks voice quality",
              content="loudnorm on voice files lifts the noise floor.",
              status="active")

# Week 1: Set a rule (later proven wrong)
old_rule = mem.add(type="decision", title="Audio normalization policy",
                   content="Always apply loudnorm to voice audio before mixing.",
                   status="active")

# Week 3: You learn the right approach
new_rule = mem.add(type="decision", title="Audio normalization policy v2",
                   content="Never apply loudnorm to voice audio. Use per-track volume.",
                   status="validated")

# Supersede the old rule — it now points to the replacement
mem.supersede(old_rule.id, new_rule.id)

# Promote the bug to validated (confirmed real)
mem.promote(bug.id)
```

**Now when the agent recalls "how to process audio":**

```python
context = mem.recall("audio processing voice normalization", max_tokens=2000)
```

It gets:
1. The **validated** new rule (highest trust, ranked first)
2. The **validated** bug report (confirmed real)
3. The old rule is **superseded** — excluded from results entirely

**No contradiction. No confusion. The agent only sees current truth.**

## Check the Difference

```bash
# See the health of your governed memory
agentmem --db ./governed.db health
# Memory Health: 90/100
# Total: 3
# By status: validated: 2, superseded: 1
# Conflicts: 0

# Compare with the ungoverned version
agentmem --db ./ungoverned.db health
# Memory Health: 60/100
# Total: 3
# By status: active: 3
# Conflicts: 1
#   !! "Audio normalization policy" vs "Updated audio policy"
#      Contradiction on shared topic (audio, loudnorm, voice)
```

## The Pattern

| Without governance | With governance |
|---|---|
| Old and new rules both active | Old rule superseded, points to replacement |
| Agent picks randomly between contradictions | Agent only sees validated truth |
| Stale rules accumulate silently | Staleness detection flags outdated memories |
| No way to audit what the agent "knows" | Health check scores system 0-100 |
| Flat confidence: all memories equal | Trust ranking: validated > active > hypothesis |

## Real-World Impact

This isn't theoretical. agentmem was built during 2+ months of daily production work:

- **65+ YouTube videos** produced with zero repeated production bugs
- **330+ memories** governing voice generation, video assembly, image prompting
- **7 real contradictions** detected and resolved by the governance engine
- **104 stale duplicates** identified and superseded in one migration

Every bug was caught once, fixed once, and never repeated — because the memory system knows what's current and what's not.
