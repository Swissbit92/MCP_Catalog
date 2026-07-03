# tests/backend/coordinator/test_sampling_presets.py
"""
Unit tests for src/coordinator/models/sampling_presets.py.

Covers: SamplingConfig dataclass, to_ollama_params, __str__,
all named presets, get_preset, get_preset_or_default,
build_sampling_config, get_sampling_for_persona, list_presets.
"""
import sys
import logging
from pathlib import Path
from typing import Optional

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.coordinator.models.sampling_presets import (
    SamplingConfig,
    PRESETS,
    get_preset,
    get_preset_or_default,
    build_sampling_config,
    get_sampling_for_persona,
    list_presets,
)


# ── SamplingConfig dataclass ──────────────────────────────────────────────────

class TestSamplingConfigDefaults:
    def test_default_temperature(self):
        cfg = SamplingConfig()
        assert cfg.temperature == 0.7

    def test_default_optional_fields_none(self):
        cfg = SamplingConfig()
        assert cfg.top_k is None
        assert cfg.top_p is None
        assert cfg.repeat_penalty is None
        assert cfg.min_p is None

    def test_default_name_and_description(self):
        cfg = SamplingConfig()
        assert cfg.name == "custom"
        assert cfg.description == ""


class TestToOllamaParams:
    def test_always_includes_temperature(self):
        cfg = SamplingConfig(temperature=0.5)
        params = cfg.to_ollama_params()
        assert "temperature" in params
        assert params["temperature"] == 0.5

    def test_excludes_none_fields(self):
        cfg = SamplingConfig(temperature=0.5)
        params = cfg.to_ollama_params()
        assert "top_k" not in params
        assert "top_p" not in params
        assert "repeat_penalty" not in params
        assert "min_p" not in params

    def test_includes_all_non_none_fields(self):
        cfg = SamplingConfig(
            temperature=0.9,
            top_k=40,
            top_p=0.95,
            repeat_penalty=1.05,
            min_p=0.05,
        )
        params = cfg.to_ollama_params()
        assert params == {
            "temperature": 0.9,
            "top_k": 40,
            "top_p": 0.95,
            "repeat_penalty": 1.05,
            "min_p": 0.05,
        }

    def test_partial_params_only_top_k(self):
        cfg = SamplingConfig(temperature=0.7, top_k=20)
        params = cfg.to_ollama_params()
        assert set(params.keys()) == {"temperature", "top_k"}
        assert params["top_k"] == 20

    def test_partial_params_only_min_p(self):
        cfg = SamplingConfig(temperature=0.7, min_p=0.02)
        params = cfg.to_ollama_params()
        assert "min_p" in params
        assert params["min_p"] == 0.02
        assert "top_k" not in params


class TestSamplingConfigStr:
    def test_str_contains_name(self):
        cfg = SamplingConfig(name="mypreset", temperature=0.8)
        assert "mypreset" in str(cfg)

    def test_str_contains_temperature(self):
        cfg = SamplingConfig(name="test", temperature=0.42)
        assert "0.42" in str(cfg)

    def test_str_format(self):
        cfg = SamplingConfig(name="precise", temperature=0.4, top_k=30)
        s = str(cfg)
        assert s.startswith("precise(")
        assert "temperature=0.4" in s
        assert "top_k=30" in s


# ── PRESETS dict ──────────────────────────────────────────────────────────────

class TestPresets:
    EXPECTED_NAMES = {"creative", "balanced", "precise", "chaotic", "deterministic"}

    def test_all_preset_keys_present(self):
        assert set(PRESETS.keys()) == self.EXPECTED_NAMES

    def test_all_presets_are_sampling_config(self):
        for name, preset in PRESETS.items():
            assert isinstance(preset, SamplingConfig), f"{name} is not a SamplingConfig"

    def test_preset_names_match_keys(self):
        for key, preset in PRESETS.items():
            assert preset.name == key, f"Preset key '{key}' != preset.name '{preset.name}'"

    def test_creative_preset_values(self):
        p = PRESETS["creative"]
        assert p.temperature == 1.0
        assert p.top_k == 50
        assert p.top_p == 0.95
        assert p.repeat_penalty == 1.05
        assert p.min_p == 0.05

    def test_balanced_preset_values(self):
        p = PRESETS["balanced"]
        assert p.temperature == 0.8
        assert p.top_k == 40
        assert p.top_p == 0.95
        assert p.repeat_penalty == 1.05
        assert p.min_p == 0.05

    def test_precise_preset_values(self):
        p = PRESETS["precise"]
        assert p.temperature == 0.4
        assert p.top_k == 30
        assert p.top_p == 0.90
        assert p.repeat_penalty == 1.05
        assert p.min_p == 0.08

    def test_chaotic_preset_values(self):
        p = PRESETS["chaotic"]
        assert p.temperature == 1.1
        assert p.top_k == 60
        assert p.top_p == 0.97
        assert p.repeat_penalty == 1.03
        assert p.min_p == 0.03

    def test_deterministic_preset_values(self):
        p = PRESETS["deterministic"]
        assert p.temperature == 0.15
        assert p.top_k == 10
        assert p.top_p == 0.7
        assert p.repeat_penalty == 1.08
        assert p.min_p == 0.1

    def test_all_presets_have_descriptions(self):
        for name, preset in PRESETS.items():
            assert preset.description, f"{name} has empty description"

    def test_all_presets_have_non_none_top_k(self):
        for name, preset in PRESETS.items():
            assert preset.top_k is not None, f"{name} missing top_k"

    def test_temperatures_ordered_by_creativity(self):
        assert PRESETS["deterministic"].temperature < PRESETS["precise"].temperature
        assert PRESETS["precise"].temperature < PRESETS["balanced"].temperature
        assert PRESETS["balanced"].temperature < PRESETS["creative"].temperature
        assert PRESETS["creative"].temperature < PRESETS["chaotic"].temperature


# ── get_preset ────────────────────────────────────────────────────────────────

class TestGetPreset:
    def test_returns_config_for_valid_name(self):
        result = get_preset("creative")
        assert isinstance(result, SamplingConfig)
        assert result.name == "creative"

    def test_case_insensitive_lower(self):
        assert get_preset("creative") is not None

    def test_case_insensitive_upper(self):
        result = get_preset("CREATIVE")
        assert result is not None
        assert result.name == "creative"

    def test_case_insensitive_mixed(self):
        result = get_preset("Balanced")
        assert result is not None

    def test_returns_none_for_unknown(self):
        assert get_preset("nonexistent") is None

    def test_returns_none_for_empty_string(self):
        assert get_preset("") is None

    def test_all_presets_accessible(self):
        for name in PRESETS:
            assert get_preset(name) is not None


# ── get_preset_or_default ─────────────────────────────────────────────────────

class TestGetPresetOrDefault:
    def test_returns_named_preset_when_exists(self):
        result = get_preset_or_default("creative")
        assert result.name == "creative"

    def test_returns_default_when_name_is_none(self):
        result = get_preset_or_default(None)
        assert result.name == "balanced"

    def test_returns_explicit_default_when_name_is_none(self):
        result = get_preset_or_default(None, "precise")
        assert result.name == "precise"

    def test_returns_default_when_name_not_found(self, caplog):
        with caplog.at_level(logging.WARNING, logger="src.coordinator.models.sampling_presets"):
            result = get_preset_or_default("unknown_preset")
        assert result.name == "balanced"

    def test_logs_warning_for_unknown_preset(self, caplog):
        with caplog.at_level(logging.WARNING, logger="src.coordinator.models.sampling_presets"):
            get_preset_or_default("bogus")
        assert "bogus" in caplog.text

    def test_custom_default_used_when_name_not_found(self):
        result = get_preset_or_default("does_not_exist", "precise")
        assert result.name == "precise"

    def test_empty_string_name_uses_default(self):
        # Empty string is falsy — treated same as None
        result = get_preset_or_default("")
        assert result.name == "balanced"


# ── build_sampling_config ─────────────────────────────────────────────────────

class TestBuildSamplingConfig:
    def test_no_args_returns_custom_config(self):
        cfg = build_sampling_config()
        assert cfg.name == "custom"
        assert cfg.temperature == 0.7  # SamplingConfig default

    def test_temperature_override(self):
        cfg = build_sampling_config(temperature=0.3)
        assert cfg.temperature == 0.3

    def test_top_k_override(self):
        cfg = build_sampling_config(top_k=15)
        assert cfg.top_k == 15

    def test_top_p_override(self):
        cfg = build_sampling_config(top_p=0.85)
        assert cfg.top_p == 0.85

    def test_repeat_penalty_override(self):
        cfg = build_sampling_config(repeat_penalty=1.1)
        assert cfg.repeat_penalty == 1.1

    def test_min_p_override(self):
        cfg = build_sampling_config(min_p=0.02)
        assert cfg.min_p == 0.02

    def test_all_individual_params(self):
        cfg = build_sampling_config(
            temperature=0.5, top_k=25, top_p=0.9, repeat_penalty=1.07, min_p=0.04
        )
        assert cfg.temperature == 0.5
        assert cfg.top_k == 25
        assert cfg.top_p == 0.9
        assert cfg.repeat_penalty == 1.07
        assert cfg.min_p == 0.04

    def test_preset_sets_base_values(self):
        cfg = build_sampling_config(preset="precise")
        assert cfg.temperature == PRESETS["precise"].temperature
        assert cfg.top_k == PRESETS["precise"].top_k

    def test_preset_name_in_config_name(self):
        cfg = build_sampling_config(preset="creative")
        assert "creative" in cfg.name

    def test_preset_plus_temperature_override(self):
        cfg = build_sampling_config(temperature=0.3, preset="creative")
        # Temperature overridden, other preset values inherited
        assert cfg.temperature == 0.3
        assert cfg.top_k == PRESETS["creative"].top_k

    def test_preset_plus_top_k_override(self):
        cfg = build_sampling_config(top_k=99, preset="balanced")
        assert cfg.top_k == 99
        assert cfg.temperature == PRESETS["balanced"].temperature

    def test_preset_plus_all_overrides(self):
        cfg = build_sampling_config(
            temperature=0.1,
            top_k=5,
            top_p=0.5,
            repeat_penalty=1.2,
            min_p=0.01,
            preset="chaotic",
        )
        assert cfg.temperature == 0.1
        assert cfg.top_k == 5
        assert cfg.top_p == 0.5
        assert cfg.repeat_penalty == 1.2
        assert cfg.min_p == 0.01

    def test_unknown_preset_falls_back_to_balanced(self):
        cfg = build_sampling_config(preset="nonexistent")
        assert cfg.temperature == PRESETS["balanced"].temperature

    def test_returns_sampling_config_instance(self):
        assert isinstance(build_sampling_config(), SamplingConfig)


# ── get_sampling_for_persona ──────────────────────────────────────────────────

class TestGetSamplingForPersona:
    def test_empty_card_returns_balanced(self):
        result = get_sampling_for_persona({})
        assert result.name == "balanced"

    def test_no_model_preferences_returns_balanced(self):
        result = get_sampling_for_persona({"key": "eeva", "name": "E.E.V.A."})
        assert result.name == "balanced"

    def test_temperature_from_prefs(self):
        card = {"model_preferences": {"temperature": 0.6}}
        result = get_sampling_for_persona(card)
        assert result.temperature == 0.6

    def test_top_k_from_prefs(self):
        card = {"model_preferences": {"top_k": 35}}
        result = get_sampling_for_persona(card)
        assert result.top_k == 35

    def test_top_p_from_prefs(self):
        card = {"model_preferences": {"top_p": 0.88}}
        result = get_sampling_for_persona(card)
        assert result.top_p == 0.88

    def test_repeat_penalty_mapped_from_repetition_penalty(self):
        # persona JSON uses "repetition_penalty", not "repeat_penalty"
        card = {"model_preferences": {"repetition_penalty": 1.06}}
        result = get_sampling_for_persona(card)
        assert result.repeat_penalty == 1.06

    def test_min_p_from_prefs(self):
        card = {"model_preferences": {"min_p": 0.07}}
        result = get_sampling_for_persona(card)
        assert result.min_p == 0.07

    def test_preset_from_prefs(self):
        card = {"model_preferences": {"preset": "creative"}}
        result = get_sampling_for_persona(card)
        assert result.temperature == PRESETS["creative"].temperature

    def test_preset_with_temperature_override(self):
        card = {"model_preferences": {"preset": "precise", "temperature": 0.2}}
        result = get_sampling_for_persona(card)
        assert result.temperature == 0.2
        # Other precise values inherited
        assert result.top_k == PRESETS["precise"].top_k

    def test_empty_model_preferences_dict_returns_balanced(self):
        result = get_sampling_for_persona({"model_preferences": {}})
        assert result.name == "balanced"

    def test_returns_sampling_config_instance(self):
        assert isinstance(get_sampling_for_persona({}), SamplingConfig)

    def test_all_individual_params_in_prefs(self):
        card = {
            "model_preferences": {
                "temperature": 0.75,
                "top_k": 45,
                "top_p": 0.92,
                "repetition_penalty": 1.04,
                "min_p": 0.06,
            }
        }
        result = get_sampling_for_persona(card)
        assert result.temperature == 0.75
        assert result.top_k == 45
        assert result.top_p == 0.92
        assert result.repeat_penalty == 1.04
        assert result.min_p == 0.06


# ── list_presets ──────────────────────────────────────────────────────────────

class TestListPresets:
    def test_returns_dict(self):
        assert isinstance(list_presets(), dict)

    def test_all_preset_names_present(self):
        result = list_presets()
        assert set(result.keys()) == set(PRESETS.keys())

    def test_values_are_descriptions(self):
        result = list_presets()
        for name, description in result.items():
            assert description == PRESETS[name].description

    def test_all_descriptions_are_strings(self):
        for name, desc in list_presets().items():
            assert isinstance(desc, str), f"{name} description is not a string"

    def test_all_descriptions_non_empty(self):
        for name, desc in list_presets().items():
            assert desc, f"{name} has empty description"


# ── to_ollama_params round-trip for each preset ───────────────────────────────

class TestPresetOllamaParams:
    @pytest.mark.parametrize("preset_name", list(PRESETS.keys()))
    def test_ollama_params_always_has_temperature(self, preset_name):
        params = PRESETS[preset_name].to_ollama_params()
        assert "temperature" in params

    @pytest.mark.parametrize("preset_name", list(PRESETS.keys()))
    def test_ollama_params_top_k_present(self, preset_name):
        params = PRESETS[preset_name].to_ollama_params()
        assert "top_k" in params

    @pytest.mark.parametrize("preset_name", list(PRESETS.keys()))
    def test_ollama_params_min_p_present(self, preset_name):
        params = PRESETS[preset_name].to_ollama_params()
        assert "min_p" in params

    @pytest.mark.parametrize("preset_name", list(PRESETS.keys()))
    def test_ollama_params_are_finite_numbers(self, preset_name):
        import math
        params = PRESETS[preset_name].to_ollama_params()
        for k, v in params.items():
            assert not math.isnan(v) if isinstance(v, float) else True
