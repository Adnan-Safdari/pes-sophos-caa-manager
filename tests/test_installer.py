from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from sophos_caa import installer
from sophos_caa.installer import (
    _desktop_entry,
    _install_icons,
    _systemd_quote,
    _unit_contents,
)

ICON_PATHS = [
    Path("scalable/apps/org.sophos.CAA.svg"),
    Path("symbolic/apps/org.sophos.CAA-symbolic.svg"),
    Path("symbolic/apps/org.sophos.CAA-connecting-symbolic.svg"),
    Path("symbolic/apps/org.sophos.CAA-error-symbolic.svg"),
    Path("symbolic/apps/org.sophos.CAA-inactive-symbolic.svg"),
]


def test_generated_units_cover_caa_manager_and_indicator() -> None:
    caa_unit, manager_unit, indicator_unit = _unit_contents()

    assert f'ExecStart="{installer.sys.executable}" -m sophos_caa.caa.runner --verbose' in caa_unit
    assert "Restart=on-failure" in caa_unit
    assert "[Install]" not in caa_unit
    assert f'ExecStart="{installer.sys.executable}" -m sophos_caa.main' in manager_unit
    assert "WantedBy=default.target" in manager_unit
    assert f'ExecStart="{installer.sys.executable}" -m sophos_caa.ui.tray' in indicator_unit
    assert "Wants=sophos-caa-manager.service" in indicator_unit
    assert "WantedBy=default.target" in indicator_unit


def test_systemd_quote_rejects_control_characters() -> None:
    with pytest.raises(ValueError):
        _systemd_quote("/opt/caa\nExecStart=bad")


def test_desktop_entry_uses_installed_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(installer.sys, "executable", "/opt/app/bin/python")

    entry = _desktop_entry()

    assert "Exec=/opt/app/bin/sophos-caa show-indicator" in entry
    assert "Exec=/opt/app/bin/sophos-caa reauth" in entry
    assert "Exec=/opt/app/bin/sophos-caa hide-indicator" in entry
    assert "Icon=org.sophos.CAA" in entry


def test_install_icons_copies_all_packaged_icons_to_user_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prefix = tmp_path / "prefix"
    home = tmp_path / "home"
    source_root = prefix / "share/icons/hicolor"
    for index, relative in enumerate(ICON_PATHS):
        source = source_root / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(f"<svg>{index}</svg>", encoding="utf-8")
    monkeypatch.setattr(installer.sys, "prefix", str(prefix))
    monkeypatch.setattr(installer.Path, "home", staticmethod(lambda: home))

    _install_icons()

    target_root = home / ".local/share/icons/hicolor"
    for index, relative in enumerate(ICON_PATHS):
        assert (target_root / relative).read_text(encoding="utf-8") == f"<svg>{index}</svg>"


def test_installer_writes_three_units_and_desktop_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    caa = tmp_path / "opt/caa"
    caa.parent.mkdir(parents=True)
    caa.write_text("", encoding="utf-8")
    monkeypatch.setattr(installer.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(installer.shutil, "which", MagicMock(return_value="/usr/bin/tool"))
    monkeypatch.setattr(installer, "discover_caa", MagicMock(return_value=caa))
    monkeypatch.setattr(installer, "_warn_caa_config_permissions", MagicMock())
    config = MagicMock()
    monkeypatch.setattr(installer.Config, "load", MagicMock(return_value=config))
    monkeypatch.setattr(installer, "_diagnostics", MagicMock())
    monkeypatch.setattr(installer, "_indicator_available", MagicMock(return_value=True))
    install_icons = MagicMock()
    monkeypatch.setattr(installer, "_install_icons", install_icons)
    monkeypatch.setattr(installer, "_has_running_caa", MagicMock(return_value=False))
    monkeypatch.setattr(installer, "caa_version", MagicMock(return_value="CAA test"))

    def fake_run(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            arguments,
            0 if arguments[-2:] == ("is-active", "sophos-caa-manager.service") else 0,
            "",
            "",
        )

    run = MagicMock(side_effect=fake_run)
    monkeypatch.setattr(installer, "_run", run)

    assert installer.main([]) == 0

    unit_root = home / ".config/systemd/user"
    assert "sophos_caa.caa.runner --verbose" in (unit_root / "sophos-caa.service").read_text(
        encoding="utf-8"
    )
    assert "sophos_caa.main" in (unit_root / "sophos-caa-manager.service").read_text(
        encoding="utf-8"
    )
    assert "sophos_caa.ui.tray" in (unit_root / "sophos-caa-indicator.service").read_text(
        encoding="utf-8"
    )
    desktop = home / ".local/share/applications/org.sophos.CAA.desktop"
    assert "show-indicator" in desktop.read_text(encoding="utf-8")
    assert config.caa_command == str(caa)
    config.save.assert_called_once_with()
    install_icons.assert_called_once_with()
    assert (
        call(
            "systemctl",
            "--user",
            "enable",
            "sophos-caa-manager.service",
        )
        in run.call_args_list
    )
    assert (
        call(
            "systemctl",
            "--user",
            "enable",
            "sophos-caa-indicator.service",
        )
        in run.call_args_list
    )
    assert (
        run.call_args_list.count(
            call(
                "systemctl",
                "--user",
                "start",
                "sophos-caa-indicator.service",
            )
        )
        == 1
    )


def test_installer_disables_unavailable_indicator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    caa = tmp_path / "caa"
    caa.write_text("", encoding="utf-8")
    monkeypatch.setattr(installer.Path, "home", staticmethod(lambda: home))
    monkeypatch.setattr(installer.shutil, "which", MagicMock(return_value="/usr/bin/tool"))
    monkeypatch.setattr(installer, "discover_caa", MagicMock(return_value=caa))
    monkeypatch.setattr(installer, "_warn_caa_config_permissions", MagicMock())
    monkeypatch.setattr(installer.Config, "load", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(installer, "_diagnostics", MagicMock())
    monkeypatch.setattr(installer, "_indicator_available", MagicMock(return_value=False))
    install_icons = MagicMock()
    monkeypatch.setattr(installer, "_install_icons", install_icons)
    monkeypatch.setattr(installer, "_has_running_caa", MagicMock(return_value=False))
    monkeypatch.setattr(installer, "caa_version", MagicMock(return_value="CAA test"))
    run = MagicMock(return_value=subprocess.CompletedProcess(["systemctl"], 0, "", ""))
    monkeypatch.setattr(installer, "_run", run)

    assert installer.main([]) == 0

    install_icons.assert_not_called()
    assert (
        call(
            "systemctl",
            "--user",
            "disable",
            "--now",
            "sophos-caa-indicator.service",
            check=False,
        )
        in run.call_args_list
    )
    assert (
        call("systemctl", "--user", "enable", "sophos-caa-indicator.service")
        not in run.call_args_list
    )
    assert (
        call("systemctl", "--user", "start", "sophos-caa-indicator.service")
        not in run.call_args_list
    )


def test_uninstall_does_not_require_networkmanager(monkeypatch: pytest.MonkeyPatch) -> None:
    which = MagicMock(
        side_effect=lambda command: "/usr/bin/systemctl" if command == "systemctl" else None
    )
    uninstall = MagicMock(return_value=0)
    monkeypatch.setattr(installer.shutil, "which", which)
    monkeypatch.setattr(installer, "_uninstall", uninstall)

    assert installer.main(["--uninstall"]) == 0
    which.assert_called_once_with("systemctl")
    uninstall.assert_called_once_with()


def test_uninstall_removes_units_desktop_autostart_and_icons(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    monkeypatch.setattr(installer.Path, "home", staticmethod(lambda: home))
    relative_paths = [
        Path(".config/systemd/user/sophos-caa.service"),
        Path(".config/systemd/user/sophos-caa-manager.service"),
        Path(".config/systemd/user/sophos-caa-indicator.service"),
        Path(".local/share/applications/org.sophos.CAA.desktop"),
        Path(".config/autostart/org.sophos.CAA.Indicator.desktop"),
        *(Path(".local/share/icons/hicolor") / path for path in ICON_PATHS),
    ]
    for relative in relative_paths:
        path = home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("installed", encoding="utf-8")
    run = MagicMock(return_value=subprocess.CompletedProcess(["systemctl"], 0, "", ""))
    monkeypatch.setattr(installer, "_run", run)

    assert installer._uninstall() == 0

    assert all(not (home / relative).exists() for relative in relative_paths)
    assert run.call_args_list == [
        call(
            "systemctl",
            "--user",
            "disable",
            "--now",
            "sophos-caa-indicator.service",
            check=False,
        ),
        call(
            "systemctl",
            "--user",
            "disable",
            "--now",
            "sophos-caa-manager.service",
            check=False,
        ),
        call(
            "systemctl",
            "--user",
            "stop",
            "sophos-caa.service",
            check=False,
        ),
        call("systemctl", "--user", "daemon-reload", check=False),
    ]
