%define srcname lenovolegionlinux
%define version _VERSION

Summary: Control Lenovo Legion laptop
Name: python-%{srcname}
Version: %{version}
Release: 1
Source0: %{name}-%{version}.tar.gz
License: GPL-2.0
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
BuildRequires:  python3-devel
BuildRequires:  python3-wheel
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
%autosetup -n %{name}-%{version} -n %{name}-%{version}

%build
unset RPM_BUILD_ROOT
%{python3} setup.py bdist_wheel

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
mkdir %{buildroot}
mkdir %{buildroot}/usr
cd "%{_builddir}/%{name}-%{version}"
%{python3} -m installer --destdir="%{buildroot}" dist/*.whl

install -D -m 0644 %{_builddir}/%{name}-%{version}/legion_linux/extra/service/legion-linux.service %{_unitdir}/legion-linux.service
install -D -m 0644 %{_builddir}/%{name}-%{version}/legion_linux//extra/service/legion-linux.path %{_unitdir}/legion-linux.path

%files -n python-%{srcname}
%{python3_sitelib}/legion_linux/*
%{python3_sitelib}/legion_linux-%{version}.dist-info/*
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
