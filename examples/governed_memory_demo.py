"""
Governed Memory Demo — run this to see the difference.

Usage:
    pip install quilmem
    python governed_memory_demo.py
"""
import os
import tempfile
from agentmem import Memory, detect_conflicts, health_check

def demo():
    # Use a temp DB so this is fully self-contained
    db_path = os.path.join(tempfile.gettempdir(), "agentmem_demo.db")
    if os.path.exists(db_path):
        os.remove(db_path)

    mem = Memory(path=db_path)

    print("=" * 60)
    print("agentmem — Governed Memory Demo")
    print("=" * 60)

    # --- Step 1: Add memories with different trust levels ---
    print("\n--- Step 1: Adding memories ---\n")

    bug = mem.add(
        type="bug",
        title="CORS headers missing on /api/auth",
        content="Symptom: 403 on frontend login. Fix: add Access-Control-Allow-Origin.",
        status="validated",
    )
    print(f"  Added [validated bug]: {bug.title}")

    old_rule = mem.add(
        type="decision",
        title="Use cookie-based auth",
        content="Store session tokens in httpOnly cookies for all API routes.",
        status="active",
    )
    print(f"  Added [active decision]: {old_rule.title}")

    hypothesis = mem.add(
        type="decision",
        title="Maybe switch to JWT tokens",
        content="Hypothesis: JWTs could simplify the auth flow. Needs testing.",
        status="hypothesis",
    )
    print(f"  Added [hypothesis]: {hypothesis.title}")

    # --- Step 2: Search — trust ranking in action ---
    print("\n--- Step 2: Search 'authentication' ---\n")

    results = mem.search("authentication auth login")
    for r in results:
        print(f"  [{r.status}] {r.title} (rank: {r.rank})")

    # --- Step 3: Lifecycle — promote and supersede ---
    print("\n--- Step 3: Lifecycle changes ---\n")

    # The hypothesis proved correct — promote it
    mem.promote(hypothesis.id)  # hypothesis -> active
    mem.promote(hypothesis.id)  # active -> validated
    print(f"  Promoted '{hypothesis.title}' to validated")

    # The old rule is now replaced
    new_rule = mem.add(
        type="decision",
        title="Use JWT tokens for stateless auth",
        content="Confirmed: JWTs reduce auth middleware complexity by 60%.",
        status="validated",
    )
    mem.supersede(old_rule.id, new_rule.id)
    print(f"  Superseded '{old_rule.title}' with '{new_rule.title}'")

    # --- Step 4: Search again — superseded is gone ---
    print("\n--- Step 4: Search again after governance ---\n")

    results = mem.search("authentication auth session tokens")
    for r in results:
        print(f"  [{r.status}] {r.title} (rank: {r.rank})")

    superseded_in_results = any(r.status == "superseded" for r in results)
    print(f"\n  Superseded rule in results? {'YES (bad!)' if superseded_in_results else 'NO (correct!)'}")

    # --- Step 5: Conflict detection ---
    print("\n--- Step 5: Conflict detection ---\n")

    # Add a deliberate contradiction
    mem.add(
        type="decision",
        title="Database connection pooling",
        content="Always use connection pooling. Set pool_size to 20 minimum.",
        status="active",
    )
    mem.add(
        type="decision",
        title="Database connection management",
        content="Never use connection pooling for this project. "
                "Create fresh connections per request. Set pool_size to 0.",
        status="active",
    )

    conflicts = detect_conflicts(mem._conn)
    if conflicts:
        for c in conflicts:
            icon = "!!" if c.severity == "critical" else "?"
            print(f"  {icon} {c.kind}: {c.memory_a.title} vs {c.memory_b.title}")
    else:
        print("  No conflicts detected.")

    # --- Step 6: Health check ---
    print("\n--- Step 6: Health check ---\n")

    report = health_check(mem._conn)
    print(f"  Score: {report.health_score:.0f}/100")
    print(f"  Total memories: {report.total_memories}")
    print(f"  By status: {dict(report.by_status)}")
    print(f"  Conflicts: {len(report.conflicts)}")
    print(f"  Stale: {len(report.stale)}")

    # Cleanup
    mem.close()
    os.remove(db_path)

    print(f"\n{'=' * 60}")
    print("Demo complete. Install: pip install quilmem")
    print("Docs: https://github.com/Thezenmonster/agentmem")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    demo()
