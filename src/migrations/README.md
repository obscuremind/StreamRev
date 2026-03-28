# Migrations

Reserved for migration assets and snapshots to mirror XC_VM layout.

Current StreamRev migration flow:
- Alembic (if `alembic.ini` exists)
- fallback `python -m src.cli.console cmd:migrate`
