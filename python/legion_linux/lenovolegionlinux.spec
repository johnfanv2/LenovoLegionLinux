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
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python3 -m build --wheel --no-isolation

%install
python3 -m installer --destdir="$RPM_BUILD_ROOT" dist/*.whl

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)