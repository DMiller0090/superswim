# Superswimming — Mechanics & TAS Optimization Reference

The superswim knowledge base has moved into [`knowledge/`](knowledge/), reorganized as small,
single-topic pages by layer so a specific fact is one search + one read away.

## → Start at the hub: [`knowledge/README.md`](knowledge/README.md)

It has a **question index** (find your question, follow the link) and a glossary, plus:

| Layer | What |
|-------|------|
| [`knowledge/mechanics/`](knowledge/mechanics/) | Game truth: [charging](knowledge/mechanics/charging.md) · [ESS](knowledge/mechanics/ess.md) · [decay curve](knowledge/mechanics/decay-curve.md) · [neutral](knowledge/mechanics/neutral.md) · [animation/head-bob](knowledge/mechanics/animation.md) · [turnaround](knowledge/mechanics/turnaround.md) · [arrow](knowledge/mechanics/arrow.md) · [strobo](knowledge/mechanics/strobo.md) · [pumps/x598](knowledge/mechanics/pumps.md) · [camera](knowledge/mechanics/camera.md) |
| [`knowledge/strategy/`](knowledge/strategy/) | TAS heuristics: [phase ordering](knowledge/strategy/phase-ordering.md) · [reboost](knowledge/strategy/reboost.md) · [neutral dip](knowledge/strategy/neutral-dip.md) |
| [`knowledge/model/`](knowledge/model/) | Sim/planner: [sim precision](knowledge/model/sim.md) · [planner](knowledge/model/planner.md) · [predictors](knowledge/model/predictors.md) |
| [`knowledge/reference/`](knowledge/reference/) | [constants](knowledge/reference/constants.md) · [glossary](knowledge/reference/glossary.md) · [addresses](knowledge/reference/addresses.md) · [commands](knowledge/reference/commands.md) · [data](knowledge/reference/data.md) |
| [`knowledge/history/`](knowledge/history/) | Provenance & dead ends (`status: historical`): [resolved bugs](knowledge/history/resolved-bugs.md) · [open questions](knowledge/history/open-questions.md) |

The base claims are validated bit-exact against the real game (single-precision arithmetic, the
console cosine table, the x598 pump scramble); raw measurement tables are in
[`knowledge/reference/data.md`](knowledge/reference/data.md). The KB is regression-tested by a
bounded weak-agent doc-eval under [`knowledge/_eval/`](knowledge/_eval/).
