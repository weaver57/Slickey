import asyncio
import unittest

from permission_system import BOT_CREATOR_ID, ROLE_PRESETS, command_keys, default_allowed, evaluate, is_broad_deny


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

    async def test_unclassified_command_fails_closed_when_strict_mode_is_enabled(self):
        decision = await evaluate(
            FakePool(), guild_id=1, user_id=7, guild_owner_id=None,
            command_name="new-command", strict_unclassified=True,
        )
        self.assertFalse(decision.allowed)
        self.assertIn("Protected", decision.reason)


if __name__ == "__main__":
    unittest.main()
