# PR2 — CombatService + Tower PvE

## Scope
- `game/services/combat_service.py` — PvE resolve via combat_rules + StatsService
- `tower_service` floors use real attack swings instead of single power roll
- Tower UI shows last combat log lines
- **No** PvP, **no** Secret Realm, no schema change

## Flow
`.thap` → stamina → floor++ → monster_for_tower_floor → resolve_pve → win bag / lose 50% bag
