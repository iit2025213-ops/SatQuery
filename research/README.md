# Research Extension

This directory is reserved for evaluating new remote-sensing models and
techniques discovered from arXiv or other research sources.

## Workflow

```
paper → candidate → feasibility assessment → prototype → benchmark → useful?
                                                                      ↓
                                                              NO → archive
                                                              YES → capability adapter → registry
```

## Rules

- A research model must NOT require changes to:
  - `AgentController`
  - `AgentState`
  - `LLMProvider` interface
  - Public API
- Integration is through new adapters registered in the capability registry.
- Benchmark before promoting to production.

## Directories

- `candidates/` — Papers and models under evaluation
- `experiments/` — Prototype implementations and benchmarks
- `adapters/` — Adapters for validated research models
