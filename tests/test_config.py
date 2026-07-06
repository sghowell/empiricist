"""Tests for RunConfig defaults and the environment fingerprint."""

import json

from empiricist.config import RunConfig, env_fingerprint


def test_defaults_match_spec_section_3():
    cfg = RunConfig()
    assert cfg.resource_model == "GHZ_3"
    assert cfg.json_retry_count == 2
    assert cfg.stall_window_generations == 8
    assert cfg.diversity_floor == 0.30
    assert cfg.diversity_window == 64
    assert cfg.verify_timeout_s == 30.0
    assert cfg.transient_cap == 4


def test_config_is_frozen_and_hashable():
    cfg = RunConfig()
    assert cfg.config_hash() == RunConfig().config_hash()
    assert cfg.config_hash() != RunConfig(json_retry_count=3).config_hash()
    assert len(cfg.config_hash()) == 64


def test_env_fingerprint_contains_python_and_platform():
    fp = json.loads(env_fingerprint())
    assert "python" in fp and "platform" in fp and "packages" in fp
    assert "blake3" in fp["packages"]
