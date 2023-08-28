%define srcname lenovolegionlinux
%define name python3-lenovolegionlinux
%define version 1.0.0
%define unmangled_version 1.0.0
%define release 1

Summary: Control Lenovo Legion laptop
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: UNKNOWN
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: johnfan <johnfan@example.org>
Packager: Gonçalo Negrier Duarte <gonegrier.duarte@gamil.com>
Url: https://github.com/johnfanv2/LenovoLegionLinux

%description
See documenation of LenovoLegionLinux

%prep
%autosetup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
unset RPM_BUILD_ROOT
python3.11 setup.py bdist_wheel

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
mkdir %{buildroot}
mkdir %{buildroot}/usr
cd "%{_builddir}/%{name}-%{version}"
python3.11 -m installer --destdir="%{buildroot}" dist/*.whl

install -D -m 0644 %{_builddir}/%{name}-%{version}/legion_linux/extra/service/legion-linux.service %{_unitdir}/legion-linux.service
install -D -m 0644 %{_builddir}/%{name}-%{version}/legion_linux//extra/service/legion-linux.path %{_unitdir}/legion-linux.path

%files -n python3-%{srcname}
/usr/lib/python3.11/site-packages/legion_linux/__init__.py
/usr/lib/python3.11/site-packages/legion_linux/legion.py
/usr/lib/python3.11/site-packages/legion_linux/legion_cli.py
/usr/lib/python3.11/site-packages/legion_linux/legion_gui.py
/usr/lib/python3.11/site-packages/legion_linux/legion_logo.png
/usr/lib/python3.11/site-packages/legion_linux/legion_logo_dark.png
/usr/lib/python3.11/site-packages/legion_linux/legion_logo_light.png
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/__init__.cpython-311.pyc 
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion.cpython-311.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion_cli.cpython-311.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion_gui.cpython-311.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/__init__.cpython-311.opt-1.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion.cpython-311.opt-1.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion_cli.cpython-311.opt-1.pyc
/usr/lib/python3.11/site-packages/legion_linux/__pycache__/legion_gui.cpython-311.opt-1.pyc
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/METADATA
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/RECORD
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/WHEEL
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/entry_points.txt
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/top_level.txt
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