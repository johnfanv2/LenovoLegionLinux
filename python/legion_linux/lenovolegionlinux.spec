%define srcname lenovolegionlinux
%define name python3-lenovolegionlinux
%define version _VERSION
%define unmangled_version _VERSION
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
python3 setup.py bdist_wheel

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
mkdir %{buildroot}
mkdir %{buildroot}/usr
cd "%{_builddir}/%{name}-%{version}/dist"
python3 -m pip install --target %{buildroot}/usr/lib/python3.11/site-packages/ legion_linux-py3-none-any.whl
install -D -m 0644 %{build}/legion_linux/extra/service/legion-linux.service %{_unitdir}/legion-linux.service
install -D -m 0644 %{build}/legion_linux//extra/service/legion-linux.path %{_unitdir}/legion-linux.path

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
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/INSTALLER
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/LICENSE
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/METADATA
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/RECORD
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/REQUESTED
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/WHEEL
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/direct_url.json
/usr/lib/python3.11/site-packages/legion_linux-%{version}.dist-info/top_level.txt