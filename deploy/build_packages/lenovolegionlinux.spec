%define srcname LenovoLegionLinux
%global libname legion_linux

Summary: Control Lenovo Legion laptop
Name: python-%{srcname}
Version: 0.0.22
Release: 0
Source0: https://github.com/johnfanv2/LenovoLegionLinux/archive/refs/tags/v%{version}.tar.gz
License: GPL-2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildRequires:  python3-devel
BuildRequires:  python3dist(build)
BuildRequires:  python3dist(installer)
%if 0%{?suse_version}
BuildRequires:  python313-setuptools
BuildRequires:  python313-wheel
%else
BuildRequires:  python3dist(setuptools)
BuildRequires:  python3dist(wheel)
%endif
BuildRequires:  gcc-c++
BuildRequires:  cmake
%if 0%{?suse_version}
BuildRequires:  ninja
BuildRequires:  nlohmann_json-devel
%else
BuildRequires:  ninja-build
BuildRequires:  nlohmann-json-devel
%endif
BuildRequires:  yaml-cpp-devel
BuildRequires:  systemd-rpm-macros
Vendor: johnfan <johnfan@example.org>
Packager: Gonçalo Negrier Duarte <gonegrier.duarte@gamil.com>
Url: https://github.com/johnfanv2/LenovoLegionLinux

Requires:     python3dist(PyQt6)
Requires:     python3dist(PyYAML)
Requires:     python3dist(argcomplete)
Requires:     python3dist(darkdetect)
Requires:     python3dist(Pillow)
Requires:     yaml-cpp
Requires:     systemd

%description
See documenation of LenovoLegionLinux

%prep
%autosetup -p1 -n %{srcname}-%{version}
cd python/legion_linux
sed -i "s/version = _VERSION/version = %{version}/g" setup.cfg

%build
cmake -S native/legion_service -B native-build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=%{_prefix}
cmake --build native-build

python3 -m build --wheel --no-isolation python/legion_linux

%install
DESTDIR=%{buildroot} cmake --install native-build
python3 -m installer --destdir=%{buildroot} --prefix=%{_prefix} \
  python/legion_linux/dist/*.whl
install -D -m 0644 python/legion_linux/legion_linux/legion-linux.service \
  %{buildroot}%{_unitdir}/legion-linux.service
install -D -m 0644 deploy/legion-linux.sysusers \
  %{buildroot}%{_sysusersdir}/legion-linux.conf

%files -n python-%{srcname}
%doc README.md
%license LICENSE
%{python3_sitelib}/%{libname}
%{python3_sitelib}/%{libname}-%{version}.dist-info
%{_bindir}/legion_cli
%{_bindir}/legion_gui
%{_bindir}/legion_service
%{_datadir}/applications/legion_gui.desktop
%{_datadir}/pixmaps/legion_logo.png
%{_datadir}/pixmaps/legion_logo_dark.png
%{_datadir}/pixmaps/legion_logo_light.png
%{_unitdir}/legion-linux.service
%{_sysusersdir}/legion-linux.conf

%pre
echo 'g legion-linux -' | systemd-sysusers -

%post
%systemd_post legion-linux.service

%preun
%systemd_preun legion-linux.service

%postun
%systemd_postun_with_restart legion-linux.service

%changelog
* Sat Aug 15 2026 github-actions <actions@github.com> - 0.0.22
- 0.0.22 release of LenovoLegionLinux.
* Fri Aug 07 2026 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.21
- 0.0.21 release; add python3-pillow dependency.

* Mon Apr 8 2024 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.15
- Various fix to the gui and migrate to legiond daemon
