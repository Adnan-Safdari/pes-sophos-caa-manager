# Distribution packaging

These recipes package the Python manager, its five console scripts, desktop
file, icons, and three systemd user units. They build from a clean Python source
distribution rather than archiving the development directory. They do **not**
package the proprietary Sophos Client Authentication Agent (CAA).

All package formats require Python 3.11 or newer, PyGObject with Gio/GTK 3
typelibs, NetworkManager, systemd, and an Ayatana AppIndicator implementation.
Dependency names follow Debian/Ubuntu, Fedora, and Arch conventions
respectively.

None of the recipes enables or starts a service during installation. Users or
desktop integration may enable the installable user units later when desired;
`sophos-caa.service` intentionally has no `[Install]` section.

Before publishing distribution packages, replace the non-routable example
maintainer address in the Debian and RPM metadata and generate the Arch tarball
checksum. The release sources point to this project's canonical GitHub
repository; maintainer contact details are intentionally not guessed.

## Debian/Ubuntu

Debian tools require the packaging directory to be named `debian` at the
source root. Build from a clean source distribution in a disposable directory:

```sh
version=0.1.0
work=$(mktemp -d)
python3 -m build --sdist --outdir "$work"
tar -xzf "$work/sophos_caa_manager-$version.tar.gz" -C "$work"
mv "$work/sophos_caa_manager-$version" "$work/sophos-caa-manager-$version"
cp -a packaging/debian "$work/sophos-caa-manager-$version/debian"
tar -C "$work" \
  --exclude="sophos-caa-manager-$version/debian" \
  -czf "$work/sophos-caa-manager_${version}.orig.tar.gz" \
  "sophos-caa-manager-$version"
(cd "$work/sophos-caa-manager-$version" && dpkg-buildpackage -us -uc)
```

Install the build dependencies listed in `packaging/debian/control` first, or
use `sbuild`/`pbuilder` for a clean build.

## Fedora/RPM

The spec targets current Fedora RPM Python macros:

```sh
version=0.1.0
topdir=$(mktemp -d)
mkdir -p "$topdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
python3 -m build --sdist --outdir "$topdir"
tar -xzf "$topdir/sophos_caa_manager-$version.tar.gz" -C "$topdir"
mv "$topdir/sophos_caa_manager-$version" "$topdir/sophos-caa-manager-$version"
tar -C "$topdir" -czf "$topdir/SOURCES/sophos-caa-manager-$version.tar.gz" \
  "sophos-caa-manager-$version"
cp packaging/rpm/sophos-caa-manager.spec "$topdir/SPECS/"
rpmbuild --define "_topdir $topdir" -ba \
  "$topdir/SPECS/sophos-caa-manager.spec"
```

For another RPM family, adjust AppIndicator and Python build dependency names
to that distribution's repositories.

## Arch Linux

`PKGBUILD` deliberately contains a release-tarball checksum placeholder. Build
from a staging directory and replace it with the actual SHA-256 using
`updpkgsums`; never publish a package with a skipped or placeholder checksum.

```sh
version=0.1.0
work=$(mktemp -d)
python3 -m build --sdist --outdir "$work"
tar -xzf "$work/sophos_caa_manager-$version.tar.gz" -C "$work"
mv "$work/sophos_caa_manager-$version" "$work/sophos-caa-manager-$version"
tar -C "$work" -czf "$work/sophos-caa-manager-$version.tar.gz" \
  "sophos-caa-manager-$version"
cp packaging/arch/PKGBUILD "$work/"
(cd "$work" && updpkgsums && makepkg --cleanbuild)
```

## Platform validation

Before publishing, build and install-test in clean containers or VMs for every
supported distribution release. Verify package contents, dependency
resolution, desktop/icon discovery, and that all three user units remain
disabled and inactive immediately after install and upgrade. Also test removal
and upgrade paths. The proprietary CAA must be supplied and licensed
separately; it should never be added to the source tarball or binary package.
