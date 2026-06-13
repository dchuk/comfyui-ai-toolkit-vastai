import pytest

from vastctl import profiles
from vastctl.errors import ProfileError


def test_resolve_merges_defaults():
    prof = profiles.resolve("flux")
    assert prof.image == "dchuk/comfyui-ai-toolkit:latest"
    assert prof.env["AUTO_UPDATE"] == "true"  # from [defaults.env]
    assert "gpu_ram>=24" in prof.search
    assert prof.disk == 60  # profile overrides default disk


def test_unknown_profile_raises():
    with pytest.raises(ProfileError) as exc:
        profiles.resolve("nope")
    assert "unknown profile" in str(exc.value)
    assert "flux" in str(exc.value)  # lists available


def test_overrides_apply():
    o = profiles.Overrides(
        disk=120,
        max_dph=0.25,
        gpu_ram=48,
        gpu_name="RTX_4090",
        env={"HF_TOKEN": "x"},
        pin_comfyui="v0.3.40",
        pin_ai_toolkit="abc123",
    )
    prof = profiles.resolve("flux", overrides=o)
    assert prof.disk == 120
    assert prof.max_dph == 0.25
    assert "gpu_ram>=48" in prof.search
    assert "gpu_name==RTX_4090" in prof.search
    assert prof.env["COMFYUI_VERSION"] == "v0.3.40"
    assert prof.env["AI_TOOLKIT_VERSION"] == "abc123"
    assert prof.env["HF_TOKEN"] == "x"


def test_env_override_wins_over_pin():
    o = profiles.Overrides(pin_comfyui="v1", env={"COMFYUI_VERSION": "v2"})
    prof = profiles.resolve("flux", overrides=o)
    assert prof.env["COMFYUI_VERSION"] == "v2"


def test_available_lists_profiles():
    assert set(profiles.available()) >= {"sdxl", "flux", "train"}


def test_missing_file_raises(tmp_path):
    with pytest.raises(ProfileError):
        profiles.resolve("flux", path=tmp_path / "nope.toml")
