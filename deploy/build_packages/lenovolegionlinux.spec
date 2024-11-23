%define srcname LenovoLegionLinux
%global libname legion_linux

Summary: Control Lenovo Legion laptop
Name: python-%{srcname}
Version: 0.0.19
Release: 0
Source0: https://github.com/johnfanv2/LenovoLegionLinux/archive/refs/tags/v%{version}.tar.gz
License: GPL-2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: x86_64
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pip
BuildRequires:  make
BuildRequires:  clang
BuildRequires:  gcc
BuildRequires:  inih-devel
BuildRequires:  systemd-rpm-macros
Vendor: johnfan <johnfan@example.org>
Packager: Gonçalo Negrier Duarte <gonegrier.duarte@gamil.com>
Url: https://github.com/johnfanv2/LenovoLegionLinux

Requires:     PyQt6
Requires:     python-yaml
Requires:     python-argcomplete
Requires:     python-darkdetect

%description
See documenation of LenovoLegionLinux

%prep
%autosetup -p1 -n %{srcname}-%{version}
cd python/legion_linux
sed -i "s/version = _VERSION/version = %{version}/g" setup.cfg

%build
cd python/legion_linux
%pyproject_wheel
cd legion_linux/extra/service/legiond
make

%install
%pyproject_install
%pyproject_save_files legion_linux

mkdir -p %{buildroot}%{_unitdir}
install -D -m 0644 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond.service %{buildroot}%{_unitdir}/legiond.service
install -D -m 0644 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond-onresume.service %{buildroot}%{_unitdir}/legiond-onresume.service
install -D -m 0644 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond.service %{buildroot}%{_unitdir}/legiond-cpuset.service
install -D -m 0644 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond.service %{buildroot}%{_unitdir}/legiond-cpuset.timer

mkdir -p %{buildroot}%{_bindir}
install -D -m 0755 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond/legiond-ctl %{buildroot}%{_bindir}/legiond-ctl
install -D -m 0755 %{_builddir}/%{srcname}-%{version}/python/legion_linux/legion_linux/extra/service/legiond/legiond %{buildroot}%{_bindir}/legiond

# Remove debug files
rm -rf %{buildroot}/usr/lib/debug

%files -n python-%{srcname}
%doc README.md
%license LICENSE
%{python3_sitelib}/%{libname}
%{python3_sitelib}/%{libname}-%{version}.dist-info
%{_bindir}/legion_cli
%{_bindir}/legion_gui
%{_datadir}/applications/legion_gui.desktop
%{_datadir}/legion_linux/legiond.ini
%{_datadir}/legion_linux/balanced-ac.yaml
%{_datadir}/legion_linux/balanced-battery.yaml
%{_datadir}/legion_linux/balanced-performance-ac.yaml
%{_datadir}/legion_linux/balanced-performance-battery.yaml
%{_datadir}/legion_linux/performance-ac.yaml
%{_datadir}/legion_linux/performance-battery.yaml
%{_datadir}/legion_linux/quiet-ac.yaml
%{_datadir}/legion_linux/quiet-battery.yaml
%{_datadir}/pixmaps/legion_logo.png
%{_datadir}/pixmaps/legion_logo_dark.png
%{_datadir}/pixmaps/legion_logo_light.png
%{_datadir}/polkit-1/actions/legion_cli.policy
%{_datadir}/polkit-1/actions/legion_gui.policy
%{_bindir}/legiond
%{_bindir}/legiond-ctl
%{_unitdir}/legiond-cpuset.service
%{_unitdir}/legiond-cpuset.timer
%{_unitdir}/legiond-onresume.service
%{_unitdir}/legiond.service

%exclude /usr/lib/debug

%post
echo "Frist install?! Pls copy /usr/share/legion_linux folder to /etc/legion_linux.\n"
echo "Command: sudo cp /usr/share/legion_linux /etc/legion_linux"

%preun
echo "After uninstall you can remover /etc/legion_linux to get rid of the configuration file!"

%changelog
* Mon Apr 8 2024 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.15
- Various fix to the gui and migrate to legiond daemon
