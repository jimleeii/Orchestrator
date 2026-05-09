<!-- Copied from templates/AGENTS.md during workspace scaffold -->
# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

Table of contents

- [1. Think Before Coding](#1-think-before-coding)
- [2. Simplicity First](#2-simplicity-first)
- [3. Surgical Changes](#3-surgical-changes)
- [4. Goal-Driven Execution](#4-goal-driven-execution)
- [Appendix: Agent template (quick) and Karpathy guidance](#appendix-agent-template-quick-and-karpathy-guidance)

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what you must deliver.
- No abstractions for single-use code.
- No error handling for impossible scenarios.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

- Transform tasks into verifiable goals and include checks.

## Appendix: Agent template (quick) and Karpathy guidance

Use this appendix as a quick reminder; keep the main sections specific and actionable for agents.
