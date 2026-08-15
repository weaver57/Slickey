import asyncio
import ast
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from permission_system import (BOT_CREATOR_ID, COMMAND_REGISTRY, PUBLIC_ACTION_COMMANDS, ROLE_PRESETS,
                               canonical_command_name, command_keys, default_allowed,
                               actor_can_delegate_permission, evaluate, evaluate_permission, is_broad_deny)


class _Acquire:
    def __init__(self, pool): self.pool = pool
    async def __aenter__(self): return self.pool
    async def __aexit__(self, *args): return False


class FakePool:
    def __init__(self, roles=(), rules=()): self.roles, self.rules = roles, rules
    def acquire(self): return _Acquire(self)
    async def fetch(self, query, *args):
        if "bot_role_memberships" in query:
            return [{"role_id": role} for role in self.roles]
        return self.rules


class PermissionSystemTests(unittest.IsolatedAsyncioTestCase):
    def test_command_key_order_and_defaults(self):
        self.assertEqual(command_keys("ban")[0], "command.ban")
        self.assertIn("category.moderation", command_keys("ban"))
        self.assertFalse(default_allowed("ban"))
        self.assertTrue(default_allowed("help"))
        self.assertTrue(is_broad_deny("command.*", "guild", "deny"))
        self.assertIn("administrator", ROLE_PRESETS)

    def test_every_shipped_command_is_explicitly_classified(self):
        self.assertEqual(len(COMMAND_REGISTRY), len(set(COMMAND_REGISTRY)))
        self.assertTrue(all(access in {"public", "protected", "owner_only"}
                            for _, access in COMMAND_REGISTRY.values()))
        self.assertFalse(default_allowed("a-future-command"))
        self.assertTrue(all(name in COMMAND_REGISTRY for name in PUBLIC_ACTION_COMMANDS))

        # Static registrations must be added to COMMAND_REGISTRY deliberately.
        # Dynamic social commands are covered by PUBLIC_ACTION_COMMANDS above.
        root = Path(__file__).resolve().parents[1]
        declared = set()
        for filename in ("Slickey_Main_.py", "Slickey_Secondary_.py", "ai_cog.py"):
            tree = ast.parse((root / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    target = ast.unparse(decorator.func)
                    if not any(marker in target for marker in ("bot.command", "tree.command", "app_commands.command", "commands.command")):
                        continue
                    name = next((keyword.value.value for keyword in decorator.keywords
                                 if keyword.arg == "name" and isinstance(keyword.value, ast.Constant)), None)
                    if name:
                        declared.add(name)
        self.assertTrue(declared <= set(COMMAND_REGISTRY))
        self.assertTrue({"massban", "massunban", "permissions"} <= set(COMMAND_REGISTRY))

    def test_aliases_share_one_policy_key(self):
        self.assertEqual(canonical_command_name("role_roulette"), "roleroulette")
        self.assertEqual(command_keys("role_roulette")[0], "command.roleroulette")
        self.assertEqual(canonical_command_name("/massban all"), "massban")

    def test_legacy_handler_guards_do_not_contradict_custom_policies(self):
        """High-risk handlers must use their registered policy identifiers."""
        root = Path(__file__).resolve().parents[1]
        main = (root / "Slickey_Main_.py").read_text(encoding="utf-8")
        secondary = (root / "Slickey_Secondary_.py").read_text(encoding="utf-8")
        self.assertNotIn("@app_commands.checks.has_permissions(manage_messages=True)", main)
        self.assertNotIn('"toggle_spawn")', secondary)
        self.assertIn('"spawn")', secondary)

    async def test_creator_and_owner_bypass(self):
        creator = await evaluate(None, guild_id=1, user_id=BOT_CREATOR_ID, guild_owner_id=None, command_name="ban")
        owner = await evaluate(None, guild_id=1, user_id=2, guild_owner_id=2, command_name="ban")
        self.assertTrue(creator.allowed)
        self.assertTrue(owner.allowed)

    async def test_specific_channel_user_deny_beats_role_allow(self):
        rules = [
            {"id": 1, "subject_type": "role", "subject_id": 9, "permission_key": "category.moderation", "scope_type": "guild", "scope_id": None, "effect": "allow"},
            {"id": 2, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "channel", "scope_id": 100, "effect": "deny"},
        ]
        decision = await evaluate(FakePool(roles=(9,), rules=rules), guild_id=1, user_id=7, guild_owner_id=None, command_name="ban", channel_id=100)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.matched_rule_id, 2)

    async def test_protected_command_fails_closed_without_database(self):
        decision = await evaluate(None, guild_id=1, user_id=7, guild_owner_id=None, command_name="permissions")
        self.assertFalse(decision.allowed)

    async def test_same_specificity_deny_wins(self):
        rules = [
            {"id": 1, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "allow"},
            {"id": 2, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "deny"},
        ]
        decision = await evaluate(FakePool(rules=rules), guild_id=1, user_id=7, guild_owner_id=None, command_name="ban")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.matched_rule_id, 2)

    async def test_channel_scope_beats_server_scope(self):
        rules = [
            {"id": 1, "subject_type": "member", "subject_id": None, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "deny"},
            {"id": 2, "subject_type": "member", "subject_id": None, "permission_key": "command.ban", "scope_type": "channel", "scope_id": 42, "effect": "allow"},
        ]
        decision = await evaluate(FakePool(rules=rules), guild_id=1, user_id=7, guild_owner_id=None, command_name="ban", channel_id=42)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_rule_id, 2)

    async def test_priority_breaks_an_otherwise_equal_rule_tie(self):
        rules = [
            {"id": 1, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "deny", "priority": 0},
            {"id": 2, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "allow", "priority": 10},
        ]
        decision = await evaluate(FakePool(rules=rules), guild_id=1, user_id=7, guild_owner_id=None, command_name="ban")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_rule_id, 2)

    async def test_expired_rule_no_longer_affects_a_decision(self):
        rules = [
            {"id": 1, "subject_type": "user", "subject_id": 7, "permission_key": "command.ban", "scope_type": "guild", "scope_id": None, "effect": "allow", "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)},
        ]
        decision = await evaluate(FakePool(rules=rules), guild_id=1, user_id=7, guild_owner_id=None, command_name="ban")
        self.assertFalse(decision.allowed)

    async def test_policy_capability_uses_the_same_role_and_scope_rules(self):
        rules = [
            {"id": 1, "subject_type": "role", "subject_id": 9, "permission_key": "policy.rule.read", "scope_type": "category", "scope_id": 12, "effect": "allow"},
        ]
        decision = await evaluate_permission(
            FakePool(roles=(9,), rules=rules), guild_id=1, user_id=7, guild_owner_id=None,
            permission_key="policy.rule.read", channel_id=100, category_id=12,
        )
        self.assertTrue(decision.allowed)

    async def test_delegation_cannot_expand_a_channel_grant_to_the_server(self):
        rules = [
            {"id": 1, "subject_type": "role", "subject_id": 9, "permission_key": "policy.rule.create", "scope_type": "channel", "scope_id": 100, "effect": "allow"},
            {"id": 2, "subject_type": "role", "subject_id": 9, "permission_key": "command.ban", "scope_type": "channel", "scope_id": 100, "effect": "allow"},
        ]
        pool = FakePool(roles=(9,), rules=rules)
        self.assertTrue(await actor_can_delegate_permission(
            pool, guild_id=1, user_id=7, guild_owner_id=None, permission_key="command.ban",
            scope_type="channel", scope_id=100,
        ))
        self.assertFalse(await actor_can_delegate_permission(
            pool, guild_id=1, user_id=7, guild_owner_id=None, permission_key="command.ban",
            scope_type="guild",
        ))

    async def test_unclassified_command_fails_closed_when_strict_mode_is_enabled(self):
        decision = await evaluate(
            FakePool(), guild_id=1, user_id=7, guild_owner_id=None,
            command_name="new-command", strict_unclassified=True,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("Protected", decision.reason)


if __name__ == "__main__":
    unittest.main()
