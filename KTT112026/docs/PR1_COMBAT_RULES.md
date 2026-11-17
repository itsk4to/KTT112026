# PR1 — Combat rules (baseline V1.6.3 → 1.6.4)

## Scope
- Add pure module `src/ktt112026/game/rules/combat_rules.py`
- Unit tests `tests/unit/game/test_combat_rules.py`
- **No** combat_service, commands, PvP, secret realm, schema, Dockerfile changes

## API
- hit_chance, calculate_damage, critical_hit, mastery_*, tick_dot, apply_shield
- resolve_attack (helper for future service)
- combat_power_from_effective (bridge to StatsService)

## Exclusion
Secret Realm / Bí cảnh: not touched.
