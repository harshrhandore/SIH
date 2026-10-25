import pytest
from app.core.lifecycle import validate_reset_target, cloud_bootstrap


@pytest.mark.parametrize(
    "url,target,confirmation",
    [
        ("postgresql://owner@remote.example.test/shiksham", "shiksham", "RESET-SYNTHETIC-DEMO"),
        ("postgresql://owner@localhost/other", "shiksham", "RESET-SYNTHETIC-DEMO"),
        ("postgresql://owner@localhost/shiksham", "other", "RESET-SYNTHETIC-DEMO"),
        ("postgresql://owner@localhost/shiksham", "shiksham", "wrong"),
        ("postgresql://owner@localhost/shiksham?host=remote.example&dbname=other", "shiksham", "RESET-SYNTHETIC-DEMO"),
        ("postgresql://owner@localhost/shiksham?hostaddr=198.51.100.1", "shiksham", "RESET-SYNTHETIC-DEMO"),
    ],
)
def test_reset_refuses_unapproved_targets(url, target, confirmation):
    with pytest.raises(RuntimeError):
        validate_reset_target(url, target, confirmation)


def test_exact_local_reset_guard():
    assert (
        validate_reset_target(
            "postgresql://owner@127.0.0.1:55432/shiksham", "shiksham", "RESET-SYNTHETIC-DEMO"
        ).hostname
        == "127.0.0.1"
    )


@pytest.mark.parametrize("name", ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS"])
def test_reset_refuses_environment_overrides(monkeypatch, name):
    monkeypatch.setenv(name, "untrusted")
    with pytest.raises(RuntimeError):
        validate_reset_target("postgresql://owner@localhost/shiksham", "shiksham", "RESET-SYNTHETIC-DEMO")


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://owner@project.neon.tech/db?sslmode=require&host=other.example",
        "postgresql://owner@project.neon.tech/db?sslmode=require&dbname=other",
        "postgresql://owner@project.neon.tech/db?sslmode=require&host=",
        "postgresql://owner@project.neon.tech/db?sslmode=require&sslmode=",
        "postgresql://owner@project.neon.tech/db?sslmode=disable",
        "postgresql://owner@remote.example/db?sslmode=require",
    ],
)
def test_cloud_target_rejected_before_connecting(monkeypatch, url):
    def forbidden(*args, **kwargs):
        raise AssertionError("Unapproved target must never be connected")

    monkeypatch.setattr("app.core.lifecycle.connect", forbidden)
    with pytest.raises(RuntimeError):
        cloud_bootstrap(url, 5000, "EMPTY-SYNTHETIC-CLOUD")
