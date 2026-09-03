"""Unit tests for Phase 15: Multi-Agent Swarm Collaboration & Autonomous Peer Review."""

import unittest
from app.agent.swarm import (
    AgentRole,
    ConsensusVerdict,
    SwarmAgent,
    SwarmConsensusEngine,
    SwarmDeliberationRound,
    SwarmResult,
)


class TestSwarmCollaboration(unittest.TestCase):
    def setUp(self):
        self.engine = SwarmConsensusEngine()

    def test_registered_agents_exist(self):
        """Verifies default swarm agents cover all 5 specialized roles."""
        agents = self.engine.get_registered_agents()
        self.assertEqual(len(agents), 5)
        roles = {a["role"] for a in agents}
        self.assertIn(AgentRole.ARCHITECT.value, roles)
        self.assertIn(AgentRole.CODER.value, roles)
        self.assertIn(AgentRole.CRITIC.value, roles)
        self.assertIn(AgentRole.REVIEWER.value, roles)
        self.assertIn(AgentRole.SYNTHESIZER.value, roles)

    def test_swarm_deliberation_consensus(self):
        """Verifies multi-round deliberation reaches quorum with hardened patch."""
        result = self.engine.deliberate(
            objective="Refactor cache eviction algorithm with TTL and LRU hybrid",
            context="Current eviction leaks memory under high concurrent write loads.",
        )
        self.assertIsInstance(result, SwarmResult)
        self.assertTrue(result.quorum_reached)
        self.assertEqual(result.verdict, ConsensusVerdict.APPROVED)
        self.assertGreaterEqual(result.consensus_score, 0.75)
        self.assertEqual(len(result.rounds), 2)
        self.assertIsNotNone(result.approved_patch)
        self.assertIn("Astra-Architect", result.voting_summary)
        self.assertIn("Kage-Critic", result.voting_summary)
        self.assertEqual(result.voting_summary["Kage-Critic"], "APPROVE")

    def test_deliberation_round_serialization(self):
        """Verifies round and contribution serialization to dictionary."""
        result = self.engine.deliberate(objective="Implement thread-safe event queue")
        res_dict = result.to_dict()
        self.assertIn("rounds", res_dict)
        self.assertIn("verdict", res_dict)
        self.assertIn("approved_patch", res_dict)
        self.assertIn("voting_summary", res_dict)
        self.assertIn("duration_ms", res_dict)

        # Check round 1 had adversarial critique
        round_1 = res_dict["rounds"][0]
        critic_contrib = next(
            c for c in round_1["contributions"] if c["agent_role"] == AgentRole.CRITIC.value
        )
        self.assertEqual(critic_contrib["vote"], "REQUEST_CHANGES")
        self.assertIsNotNone(critic_contrib["critique"])


if __name__ == "__main__":
    unittest.main()
