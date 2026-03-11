# HaluRust

LLM-based Rust Undefined Behavior (UB) auto-fixer, powered by Miri + Tree-sitter.

## Architecture

```
Rust Code + Test
       │
       ├──> Miri Test ──> Error Report
       │
       └──> Tree-sitter ──> AST Summary
                                │
       UB Example Library ──> Few-shot Examples (RAG, placeholder)
                                │
       Hallucination Agent ──> Quick Fix Reference
                                │
                    ┌───────────┴───────────┐
                    │     Plan Agent         │
                    │  (analyze + plan)      │
                    └───────────┬───────────┘
                                │ Fix Plan
                    ┌───────────┴───────────┐
                    │      Fix Agent         │
                    │  (generate fix code)   │
                    └───────────┬───────────┘
                                │ Candidate Code
                    ┌───────────┴───────────┐
                    │       Critic           │
                    │  (re-run Miri test)    │
                    └───────────┬───────────┘
                                │
                    Passed? ──> Done
                    Failed? ──> Loop (up to max_iterations)
```

## Prerequisites

- Python 3.11+
- Rust nightly toolchain with Miri: `rustup +nightly component add miri`
- OpenAI API key (or compatible endpoint)

## Setup

```bash
pip install -r requirements.txt
```

## Usage

### Single file fix

```bash
export OPENAI_API_KEY="your-key"
python run.py path/to/buggy.rs path/to/test.rs -o fixed.rs
```

### Pilot Study

```bash
export OPENAI_API_KEY="your-key"

# Run all cases
python pilot_study/run_pilot.py

# Run specific case
python pilot_study/run_pilot.py case1_use_after_free
```

## Project Structure

```
halurust/
├── __init__.py
├── config.py          # Global configuration
├── models.py          # Data models (MiriReport, FixPlan, etc.)
├── miri_runner.py     # Miri test executor & error parser
├── ast_parser.py      # Tree-sitter Rust AST parser
├── rag.py             # UB Example Library (RAG, placeholder)
├── llm_client.py      # OpenAI API wrapper
├── prompts.py         # Prompt templates for all agents
├── agents.py          # Plan Agent, Fix Agent, Hallucination Agent
├── critic.py          # Critic evaluation (re-run Miri)
└── pipeline.py        # Main iterative fix loop

pilot_study/
├── cases/             # UB test cases (source + test files)
├── results/           # Output JSON results
└── run_pilot.py       # Pilot study runner

ub_example_library/    # Future: few-shot examples from Miri repo
```
