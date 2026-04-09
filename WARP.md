# WARP.md

## Scope
Guidance for agent-assisted development in the standalone `SolarSim` repository.

## Principles
- Maintain deterministic simulation behavior where possible.
- Keep model assumptions and constants documented near code changes.
- Separate experimental notebooks/scripts from stable simulation modules.

## Safety
- Do not commit secrets or private operational data.
- Avoid destructive changes to reference datasets without explicit approval.

## Verification
- Run smoke simulations after core logic updates.
- Keep README and parameter documentation synchronized with implementation.
