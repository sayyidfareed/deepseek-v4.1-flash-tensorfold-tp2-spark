"""Offline contract checks; these do not establish GPU correctness or speed."""
import json
import shlex
import hashlib
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

import recipe


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.site = json.loads((recipe.ROOT / "site.example.json").read_text())
        self.site.update(head_ip="10.40.0.1", hca="mlx5_0:1,mlx5_1:1", interface="enp1s0")

    def test_both_ranks_use_same_pool_and_lane_geometry(self):
        for name in recipe.LOCK["profiles"]:
            with self.subTest(profile=name):
                result = recipe.commands(self.site, name)
                worker = result["worker"]["argv"]
                head = result["head"]
                for option, env in (("--streams", "TF_DS_STREAMS"),
                                    ("--round-rows", "TF_DS_ROUND_ROWS")):
                    self.assertEqual(worker[worker.index(option) + 1], head["env"][env])
                self.assertEqual(worker[worker.index("--pool") + 1],
                                 head["argv"][head["argv"].index("--context") + 1])
                self.assertEqual(result["start_order"], ["worker", "head"])
                self.assertFalse(result["qualified_here"])

    def test_replay_fix_and_private_authenticated_listener(self):
        result = recipe.commands(self.site, "baseline-c4")
        for rank in ("head", "worker"):
            self.assertEqual(result[rank]["env"]["TF_DS_REPLAY_FLOOR"], "1")
        argv = result["head"]["argv"]
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--api-key-file") + 1], self.site["key_file"])
        self.assertEqual(argv[argv.index("--temperature") + 1], "1.0")

    def test_gid_three_reaches_both_independent_transports(self):
        self.site["gid_index"] = 3
        for profile in recipe.LOCK["profiles"]:
            result = recipe.commands(self.site, profile)
            for rank in ("head", "worker"):
                self.assertEqual(result[rank]["env"]["TF_RDMA_GID_INDEX"], "3")
                self.assertEqual(result[rank]["env"]["NCCL_IB_GID_INDEX"], "3")

    def test_reviewed_patch_is_reproducible_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "upstream/native"
            source.mkdir(parents=True)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(source), *args])
            git("init", "-q")
            (source / "setting").write_text("old\n")
            git("add", "setting")
            git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                "-c", "commit.gpgsign=false", "commit", "-qm", "base")
            revision = git("rev-parse", "HEAD").decode().strip()
            (source / "setting").write_text("new\n")
            data = git("diff", "--binary", "HEAD")
            (source / "setting").write_text("old\n")
            (root / "fix.patch").write_bytes(data)
            lock = {"sources": {"native": {"revision": revision}},
                    "patches": {"native": {"path": "fix.patch",
                        "sha256": hashlib.sha256(data).hexdigest()}}}
            with patch.object(recipe, "ROOT", root), patch.object(recipe, "LOCK", lock):
                self.assertFalse(recipe.source_status("native")["ready"])
                recipe.apply_source_patch("native")
                self.assertTrue(recipe.source_status("native")["ready"])
                recipe.apply_source_patch("native")  # idempotent
                (source / "unrelated").write_text("preserve me")
                self.assertFalse(recipe.source_status("native")["ready"])
                with self.assertRaises(ValueError):
                    recipe.apply_source_patch("native")
                self.assertEqual((source / "unrelated").read_text(), "preserve me")
                (source / "unrelated").unlink()
                (source / "setting").write_text("another edit\n")
                with self.assertRaises(ValueError):
                    recipe.apply_source_patch("native")
                (root / "fix.patch").write_bytes(data + b"modified")
                with self.assertRaisesRegex(ValueError, "checksum"):
                    recipe.source_status("native")

    def test_accepted_gpu_sampling_reaches_both_ranks(self):
        result = recipe.commands(self.site, "accepted-c8")
        for rank in ("head", "worker"):
            self.assertEqual(result[rank]["env"]["TF_DS_GPU_CANDIDATES"], "1")
            self.assertNotIn("TF_DS_PREFILL_4K", result[rank]["env"])

    def test_c8_changes_only_stream_count(self):
        base = recipe.commands(self.site, "baseline-c4")
        candidate = recipe.commands(self.site, "candidate-c8")
        candidate["profile"] = base["profile"]
        candidate["head"]["env"]["TF_DS_STREAMS"] = "4"
        for rank, flag in (("head", "--parallel"), ("worker", "--streams")):
            argv = candidate[rank]["argv"]
            argv[argv.index(flag) + 1] = "4"
        self.assertEqual(base, candidate)

    def test_example_cannot_be_accidentally_used(self):
        with self.assertRaises(ValueError):
            recipe.validate_site(json.loads((recipe.ROOT / "site.example.json").read_text()))

    def test_bad_sites_fail_before_any_command(self):
        for key, value in (("head_ip", "127.0.0.1"), ("head_ip", "192.0.2.10"),
                           ("api_port", 29620), ("api_port", True), ("gid_index", -1),
                           ("hca", None), ("head_ip", 1234),
                           ("cache", "relative"), ("interface", "eth0; touch x"),
                           ("model", "/model\nunsafe")):
            site = dict(self.site, **{key: value})
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                recipe.commands(site, "baseline-c4")

    def test_shell_representation_preserves_literal_paths(self):
        site = dict(self.site, model="/models/a name $(touch SHOULD_NOT_RUN)")
        for rank in recipe.commands(site, "baseline-c4").values():
            if isinstance(rank, dict) and "argv" in rank:
                self.assertEqual(shlex.split(shlex.join(rank["argv"])), rank["argv"])

    def test_all_public_identities_are_immutable(self):
        for source in [*recipe.LOCK["sources"].values(), *recipe.LOCK["artifacts"].values()]:
            self.assertRegex(source["revision"], r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
