# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

- GitHub Actions CI for pytest, Ruff, and mypy on Python 3.11 and 3.12.
- Structured postflop equity diagnostics (estimated equity, required equity, assumed range, sample counts) with severity estimates explicitly labeled as non-solver.

### Changed

- Completed package metadata for source distributions, wheels, and project links.
- Expanded SUMMARY parsing to recognize showdown, muck, fold, and collected variants while keeping unknown lines visible in `raw_unparsed`.

## 0.1.0 - 2026-06-06

### Added

- Natural8 and GGPoker tournament hand-history parsing with tolerant unknown-line reporting.
- Hero-centric context enrichment for position, effective stack, M-ratio, and decision nodes.
- Preflop GTO range-chart lookup and pluggable postflop equity or external-solver backends.
- Per-decision quality grading, estimated EV-loss severity, session statistics, and leak detection.
- Opponent profiling with lightweight assumed-range labels.
- Rich CLI reports, JSON export, and a local Web UI with hand replay and `.txt` upload.
- TexasSolver adapter contract and import tooling for preflop charts.
