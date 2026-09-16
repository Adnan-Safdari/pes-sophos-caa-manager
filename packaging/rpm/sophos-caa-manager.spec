Name:           sophos-caa-manager
Version:        0.1.0
Release:        1%{?dist}
Summary:        Unofficial Linux manager for Sophos Client Authentication Agent

License:        MIT
URL:            https://github.com/Adnan-Safdari/pes-sophos-caa-manager
Source0:        %{url}/releases/download/v%{version}/%{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python3-devel >= 3.11
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pytest
BuildRequires:  python3-rpm-macros
BuildRequires:  pyproject-rpm-macros

Requires:       python3 >= 3.11
Requires:       python3-gobject
Requires:       gtk3
Requires:       NetworkManager
Requires:       systemd
Requires:       libayatana-appindicator-gtk3

%description
Network-aware lifecycle management and a GTK/AppIndicator desktop interface
for a separately obtained Sophos Client Authentication Agent.

This package contains only the open source manager. It does not contain the
proprietary Sophos Client Authentication Agent.

%prep
%autosetup -p1

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files sophos_caa

%check
%{python3} -m pytest -q

%files -f %{pyproject_files}
%license LICENSE
%doc README.md
%{_bindir}/sophos-caa
%{_bindir}/sophos-caa-manager
%{_bindir}/sophos-caa-indicator
%{_bindir}/sophos-caa-install
%{_bindir}/sophos-caa-run
%{_datadir}/applications/org.sophos.CAA.desktop
%{_datadir}/icons/hicolor/scalable/apps/org.sophos.CAA.svg
%{_datadir}/icons/hicolor/symbolic/apps/org.sophos.CAA-symbolic.svg
%{_datadir}/icons/hicolor/symbolic/apps/org.sophos.CAA-connecting-symbolic.svg
%{_datadir}/icons/hicolor/symbolic/apps/org.sophos.CAA-error-symbolic.svg
%{_datadir}/icons/hicolor/symbolic/apps/org.sophos.CAA-inactive-symbolic.svg
%{_prefix}/lib/systemd/user/sophos-caa.service
%{_prefix}/lib/systemd/user/sophos-caa-manager.service
%{_prefix}/lib/systemd/user/sophos-caa-indicator.service

%changelog
* Wed Sep 16 2026 Sophos CAA Manager contributors <noreply@example.invalid> - 0.1.0-1
- Initial distribution package.
