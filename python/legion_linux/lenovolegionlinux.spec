%define name python-lenovolegionlinux
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
python3 -m pip install --target %{buildroot}%{python3_sitelib} %{srcname}-%{version}-py3-none-any.whl 

%files -n python3-%{srcname}
%{python3_sitelib}/legion_linux/__init__.py
%{python3_sitelib}/legion_linux/legion.py
%{python3_sitelib}/legion_linux/legion_cli.py
%{python3_sitelib}/legion_linux/legion_gui.py
%{python3_sitelib}/legion_linux/legion_logo.png
%{python3_sitelib}/legion_linux/legion_logo_dark.png
%{python3_sitelib}/legion_linux/legion_logo_light.png
%{python3_sitelib}/legion_linux/__pycache__/__init__.cpython-311.opt-1.pyc
%{python3_sitelib}/legion_linux/__pycache__/__init__.cpython-311.pyc 
%{python3_sitelib}/legion_linux/__pycache__/legion.cpython-311.opt-1.pyc
%{python3_sitelib}/legion_linux/__pycache__/legion.cpython-311.pyc
%{python3_sitelib}/legion_linux/__pycache__/legion_cli.cpython-311.opt-1.pyc
%{python3_sitelib}/legion_linux/__pycache__/legion_cli.cpython-311.pyc
%{python3_sitelib}/legion_linux/__pycache__/legion_gui.cpython-311.opt-1.pyc
%{python3_sitelib}/legion_linux/__pycache__/legion_gui.cpython-311.pyc
%{python3_sitelib}/legion_linux-%{version}.dist-info/INSTALLER
%{python3_sitelib}/legion_linux-%{version}.dist-info/LICENSE
%{python3_sitelib}/legion_linux-%{version}.dist-info/METADATA
%{python3_sitelib}/legion_linux-%{version}.dist-info/RECORD
%{python3_sitelib}/legion_linux-%{version}.dist-info/REQUESTED
%{python3_sitelib}/legion_linux-%{version}.dist-info/WHEEL
%{python3_sitelib}/legion_linux-%{version}.dist-info/direct_url.json
%{python3_sitelib}/legion_linux-%{version}.dist-info/top_level.txt