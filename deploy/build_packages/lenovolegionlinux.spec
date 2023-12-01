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

%files -n python3-%{srcname}
%{python3_sitelib}/legion_linux/__init__.py
%{python3_sitelib}/legion_linux/legion.py
%{python3_sitelib}/legion_linux/legion_cli.py
%{python3_sitelib}/legion_linux/legion_gui.py
%{python3_sitelib}/legion_linux/legion_logo.png
%{python3_sitelib}/legion_linux/legion_logo_dark.png
%{python3_sitelib}/legion_linux/legion_logo_light.png
%{python3_sitelib}/legion_linux-%{version}.dist-info/METADATA
%{python3_sitelib}/legion_linux-%{version}.dist-info/RECORD
%{python3_sitelib}/legion_linux-%{version}.dist-info/WHEEL
%{python3_sitelib}/legion_linux-%{version}.dist-info/entry_points.txt
%{python3_sitelib}/legion_linux-%{version}.dist-info/top_level.txt
/usr/bin/fancurve-set
/usr/bin/legion_cli
/usr/bin/legion_gui
/usr/share/applications/legion_gui.desktop
/usr/share/applications/legion_gui_user.desktop
/usr/share/legion_linux/.env
/usr/share/legion_linux/balanced-ac.yaml
/usr/share/legion_linux/balanced-battery.yaml
/usr/share/legion_linux/balanced-performance-ac.yaml
/usr/share/legion_linux/balanced-performance-battery.yaml
/usr/share/legion_linux/performance-ac.yaml
/usr/share/legion_linux/performance-battery.yaml
/usr/share/legion_linux/quiet-ac.yaml
/usr/share/legion_linux/quiet-battery.yaml
/usr/share/pixmaps/legion_logo.png
/usr/share/pixmaps/legion_logo_dark.png
/usr/share/pixmaps/legion_logo_light.png
/usr/share/polkit-1/actions/legion_cli.policy
/usr/share/polkit-1/actions/legion_gui.policy
