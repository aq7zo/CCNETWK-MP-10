# Repository Guidelines

## Project Structure & Module Organization
This repository implements the peer to peer PokeProtocol stack. Core gameplay flows live in `peer.py`, which coordinates sockets, reliability, and battle orchestration. Turn logic is modeled in `battle_state.py`, damage math in `damage_calculator.py`, and protocol definitions in `messages.py` and `reliability.py`. Supporting data loaders reside in `moves.py` and `pokemon_data.py`, while `example_battle.py` wires the pieces together for quick manual runs. Domain notes, RFCs, and testing references live in `docs/`, and the raw plus cleaned datasets are `pokemon.csv` and `pokemon_cleaned.csv`.

## Build, Test, and Development Commands
- `python example_battle.py host` - start the host peer on UDP 8888; run this before any joiner and watch console logs for the handshake sequence.
- `python example_battle.py joiner` - connect to the host (default 127.0.0.1:8888) to simulate a remote player; pair this with a second terminal or machine.
- `python test_suite.py` - execute the 21 unit and integration tests across pokemon data, move logic, message serialization, reliability, and the end to end battle; run before every commit.
- `python data_cleaning.py` - regenerate `pokemon_cleaned.csv` from `pokemon.csv`; rerun whenever base stats or type tables change.

## Coding Style & Naming Conventions
Follow PEP 8 with four space indentation, descriptive snake_case functions, and PascalCase classes (see `BattleStateMachine` and `HostPeer`). Continue using type hints (`Optional`, `Tuple`, etc.) and module docstrings mirroring the existing triple quoted headers. When introducing protocol changes, update `MessageType`, serializers in `messages.py`, and the corresponding handlers in `peer.py` so enums and dispatch tables stay aligned. CSV column names should remain lowercase_with_underscores to match the loaders.

## Testing Guidelines
`test_suite.py` uses `unittest`; group new cases by subsystem (e.g., extend `TestReliabilityLayer` when altering retransmission rules) and keep method names in the `test_<scenario>` format. Preserve coverage over battle resolution and reliability branches, documenting any intentionally skipped paths inside `docs/TESTING_GUIDE.md`. For manual validation, follow the dual terminal workflow in `docs/TESTING_GUIDE.md` so both peers exchange ATTACK/DEFENSE/CALCULATION messages while you monitor seed sync in the logs.

## Commit & Pull Request Guidelines
Write commits in the imperative mood with a short subsystem prefix, for example `battle_state: guard illegal turn swap`. Each pull request should explain the motivation, call out impacted modules, and include evidence that `python test_suite.py` passed (plus relevant host or joiner transcripts). Reference RFC or doc sections whenever protocol semantics change, and attach screenshots or log excerpts if you modified runtime output or chat UX.

## Security & Configuration Tips
Keep UDP ports 8888 and 8889 exposed only on machines participating in tests, and prefer localhost during development. Never commit external datasets without cleaning them through `python data_cleaning.py`. Confirm that both peers share the handshake seed before verifying networking changes to avoid false mismatch reports.
