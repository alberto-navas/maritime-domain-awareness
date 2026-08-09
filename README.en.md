# Maritime Domain Awareness

**English** · [Español](README.md)

[![Tests](https://github.com/alberto-navas/maritime-domain-awareness/actions/workflows/tests.yml/badge.svg)](https://github.com/alberto-navas/maritime-domain-awareness/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Analysis of real, historical AIS data to flag anomalous vessel behavior —
transmission gaps, physically implausible position/speed jumps — as leads
for a human analyst to review, not verdicts.

## Motivation

Ships above a certain size broadcast their position, speed, and identity
by radio (AIS), publicly, for navigation safety. That same system, looked
at in aggregate, also gives away behavior that falls outside the norm: a
vessel that stops transmitting in the wrong place, a position jump no
real physics explains, a declared speed that doesn't match its own
displacement. None of this proves anything on its own — but it's exactly
the kind of signal a maritime surveillance analyst wants pre-filtered and
explained before looking at the raw data. This project is that filtering
layer, applied to real, public historical data (unlike the sibling
[C-UAS Threat Triage](https://github.com/alberto-navas/cuas-threat-triage)
project, where the data has to be synthetic because no public equivalent
dataset exists).

## Capabilities

Current version (Phase 1): two detector families, each operating on a
single track (one MMSI), independent and separately auditable —
`src/detectors/`:

- **AIS transmission gaps** (`gaps.py`): flags intervals between
  consecutive position reports above what's expected, with the threshold
  calibrated by the navigational status declared right before the gap (an
  anchored vessel transmits much less often than one underway, and the
  detector accounts for that instead of confusing the two).
- **Implausible kinematic jumps** (`kinematics.py`): two rules over the
  same pair of consecutive fixes — the speed implied by the position
  displacement exceeds what any real vessel could reach (same principle
  as a "GPS glitch"), or that implied speed doesn't match the SOG (speed
  over ground) the vessel itself reports at all.

Every finding (`Finding`) carries its category, severity, position, and a
`description` explaining the concrete reasoning — which threshold was
exceeded and with what values — never a conclusion (see "What this
project deliberately does NOT do" below).

## Architecture

```
Historical AIS CSV (Danish Maritime Authority, one file per day)
        │
        ▼
src/ingest.py     (parses the CSV -> PositionReport[] + VesselIdentity[])
        │
        ▼
src/tracks.py     (groups by MMSI, sorts by time -> Track)
        │
        ▼
src/detectors/gaps.py         (transmission gaps)
src/detectors/kinematics.py   (implausible jumps + SOG mismatch)
        │
        ▼
src/pipeline.py   (orchestrates ingest -> tracks -> detectors -> Finding[])
        │
        ▼
src/report.py     (findings.json + findings.csv + static map PNG)
        ▲
        │
src/cli.py
```

`src/model.py` is the shared vocabulary (`PositionReport`,
`VesselIdentity`, `Track`, `Finding`) used across every stage: no
detector knows the source CSV format, and ingest knows nothing about any
detector.

Each detector's thresholds live in `src/config.py`, documented one by one
with the reasoning behind each value, and can be overridden without
touching code via a YAML file (see `config/thresholds.yaml`).

## Usage

```bash
# One CSV -> findings + map in output/
python -m src.cli data/samples/2024-01-01.csv

# Several consecutive days -> a single combined report
python -m src.cli data/samples/2024-01-*.csv --output output/january/

# Custom thresholds
python -m src.cli data/samples/2024-01-01.csv --config config/thresholds.yaml
```

Produces `findings.json`, `findings.csv` (same content, for opening in
any spreadsheet) and `map.png` (each track as a line, each finding as a
point colored by severity).

## Tests

```bash
pytest -v
```

37 tests covering all eight pipeline modules (geo, ingest, tracks,
config, both detectors, pipeline, report, CLI), using versioned synthetic
fixtures in `tests/fixtures/` that follow DMA's real column schema — none
depend on downloading anything external. They run automatically on every
`push` via GitHub Actions (`.github/workflows/tests.yml`), on Ubuntu and
Windows.

## Code quality

```bash
ruff check .        # lint
ruff format .       # formatting
mypy src/           # static type checking
```

Configured in `pyproject.toml`. Checked automatically on every `push` (a
`lint` job separate from the test matrix).

**Test coverage**: 98% (`pytest --cov=src`), with a CI threshold of 85%
as a safety net against a large regression, not as a line-by-line target
to chase.

## Test data

Danish Maritime Authority historical AIS files
(https://web.ais.dk/aisdata/) are free to download, but their
redistribution terms aren't clear enough to version a real excerpt in a
public repository without confirming that first. That's why
`tests/fixtures/sample_dma.csv` is synthetic, hand-written to exactly
follow DMA's real column schema (same names, same date format, same
sentinel values like `Heading = 511` for "not available"), with
deliberate cases for each detector: a transmission gap, an impossible
position jump, an SOG mismatch, and the cases that should **not** fire
(an anchored vessel with a long-but-normal gap, a base-station row that
isn't a vessel, a row with no valid MMSI).

To analyze real data: download any daily file from
https://web.ais.dk/aisdata/ and pass it directly to the CLI — the column
schema matches.

## What this project deliberately does NOT do

This is an **analysis and flagging layer for human review**, never an
interdiction or automated-decision tool:

- It does not decide or execute any action — neither interception nor
  automatic alerting to any authority. The output is a list of leads for
  a human analyst to investigate with context the system itself doesn't
  have (local traffic, weather, the area's historical pattern).
- "Flagged as suspicious" is not "guilty." Every `Finding` explains the
  concrete calculation that generated it (which threshold, with what
  values), never a conclusion about the vessel's intent.
- It is not live tracking: it only processes historical AIS data already
  published legally for research, never a real-time connection to
  vessels operating right now.
- It does not include any vessel-to-vessel rendezvous/loitering detector
  or identity-inconsistency detector yet — see "Possible extensions". v1
  deliberately limits itself to what can be audited on a single track at
  a time.
- Thresholds are explainable heuristics, not "ground truth" — a
  transmission gap has completely normal explanations (loss of VHF
  coverage offshore, channel congestion) just as often as suspicious
  ones. The detector doesn't tell those two causes apart; it only flags
  where to look.

## Possible extensions

- **Vessel-to-vessel rendezvous/loitering**: sustained proximity with low
  relative speed in open water (the classic ship-to-ship transfer
  pattern). Requires a real port/anchorage zone mask to avoid firing on
  every port — decided as a prerequisite before building this detector,
  not solved yet.
- **Identity inconsistency**: same MMSI with conflicting `VesselIdentity`
  over time, or an MMSI whose MID prefix doesn't match the declared
  behavior pattern.
- **Speed threshold by vessel type**: `VesselIdentity.ship_type` is
  already parsed; `kinematics.py`'s plausible-speed ceiling could be
  calibrated per type instead of a single global threshold.
- Multi-language report/CLI output (like the sibling projects).
- Interactive map instead of a static PNG.
