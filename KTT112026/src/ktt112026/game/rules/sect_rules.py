"""Quyền tông môn — rank leader > elder > member (PR4)."""
from __future__ import annotations

SECT_ROLES = ("leader", "elder", "member")

ROLE_LABEL = {
    "leader": "Tông Chủ",
    "elder": "Trưởng Lão",
    "member": "Đệ tử",
}

SECT_PERMISSIONS: dict[str, frozenset[str]] = {
    "sect.invite": frozenset({"leader", "elder", "member"}),
    "sect.kick": frozenset({"leader", "elder"}),
    "sect.promote": frozenset({"leader"}),
    "sect.demote": frozenset({"leader"}),
    "sect.bank": frozenset({"leader", "elder"}),
    "sect.disband": frozenset({"leader"}),
}


def normalize_role(role: str | None) -> str:
    r = (role or "member").strip().lower()
    aliases = {
        "tongchu": "leader",
        "chủ": "leader",
        "chu": "leader",
        "truonglao": "elder",
        "tl": "elder",
        "de_tu": "member",
        "detu": "member",
    }
    return aliases.get(r, r if r in SECT_ROLES else "member")


def role_rank(role: str) -> int:
    r = normalize_role(role)
    try:
        return SECT_ROLES.index(r)
    except ValueError:
        return len(SECT_ROLES)


def has_permission(role: str, perm: str) -> bool:
    allowed = SECT_PERMISSIONS.get(perm, frozenset())
    return normalize_role(role) in allowed


def can_manage_target(actor_role: str, target_role: str, permission: str) -> bool:
    if not has_permission(actor_role, permission):
        return False
    ar, tr = normalize_role(actor_role), normalize_role(target_role)
    if ar not in SECT_ROLES or tr not in SECT_ROLES:
        return False
    return role_rank(ar) < role_rank(tr)


def can_kick(actor_role: str, target_role: str) -> bool:
    if normalize_role(target_role) == "leader":
        return False
    return can_manage_target(actor_role, target_role, "sect.kick")


def can_change_role(actor_role: str, target_role: str, new_role: str, *, promote: bool) -> bool:
    nr = normalize_role(new_role)
    tr = normalize_role(target_role)
    ar = normalize_role(actor_role)
    if nr not in SECT_ROLES or tr not in SECT_ROLES:
        return False
    if nr == "leader":
        return ar == "leader"  # nhường chức — caller xử lý transfer
    perm = "sect.promote" if promote else "sect.demote"
    if not can_manage_target(ar, tr, perm):
        return False
    a, t, n = role_rank(ar), role_rank(tr), role_rank(nr)
    if n == t or n <= a:
        return False
    return n < t if promote else n > t
