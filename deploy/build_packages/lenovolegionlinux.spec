%define srcname LenovoLegionLinux
%global libname legion_linux

Summary: Control Lenovo Legion laptop
Name: python-%{srcname}
Version: 0.0.9
Release: 1
Source0: https://github.com/johnfanv2/LenovoLegionLinux/archive/refs/tags/v%{version}-prerelease.tar.gz
License: GPL-2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
BuildRequires:  python3-wheel
BuildRequires:  python3-pip
Vendor: johnfan <johnfan@example.org>
Packager: Gonçalo Negrier Duarte <gonegrier.duarte@gamil.com>
Url: https://github.com/johnfanv2/LenovoLegionLinux

Requires:     PyQt5
Requires:     python-yaml
Requires:     python-argcomplete
Requires:     python-darkdetect

%description
See documenation of LenovoLegionLinux

%prep
%autosetup -p1 -n %{srcname}-%{version}-prerelease
cd python/legion_linux
sed -i "s/version = _VERSION/version = %{version}/g" setup.cfg

%build
cd python/legion_linux
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files legion_linux

install -D -m 0644 %{_builddir}/%{srcname}-%{version}-prerelease/python/legion_linux/legion_linux/extra/service/legion-linux.service %{_unitdir}/legion-linux.service
install -D -m 0644 %{_builddir}/%{srcname}-%{version}-prerelease/python/legion_linux/legion_linux/extra/service/legion-linux.path %{_unitdir}/legion-linux.path

%files -n python-%{srcname}
%doc README.md
%{python3_sitelib}/%{libname}
%{python3_sitelib}/%{libname}-%{version}.dist-info
%{_bindir}/fancurve-set
%{_bindir}/legion_cli
%{_bindir}/legion_gui
%{_datadir}/applications/legion_gui.desktop
%{_datadir}/applications/legion_gui_user.desktop
%{_datadir}/legion_linux/.env
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

%post
echo "Frist install?! Pls copy /usr/share/legion_linux folder to /etc/legion_linux.\n"
echo "Command: sudo cp /usr/share/legion_linux /etc/legion_linux"

%preun
echo "After uninstall you can remover /etc/legion_linux to get rid of the configuration file!"
