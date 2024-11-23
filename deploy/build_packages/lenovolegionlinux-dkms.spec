# norootforbuild
%define srcname LenovoLegionLinux
%global dkms_name %{srcname}
%global debug_package %{nil}

Name:         dkms-%{srcname}
License:      GPL-2.0
Group:        System/Kernel
Summary:      LenovoLegionLinux Kernel Module Package
Version:      0.0.19
Release:      0
Source0:      https://github.com/johnfanv2/LenovoLegionLinux/archive/refs/tags/v%{version}.tar.gz

Requires:     dkms

%description
Driver for controlling Lenovo Legion laptops including fan control and power mode.

%prep
%autosetup -p1 -n %{srcname}-%{version}

%install
mkdir -p %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/
cp -fr kernel_module/* %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/

%post
dkms add -m %{dkms_name} -v %{version} -q || :
# Rebuild and make available for the currently running kernel:
dkms build -m %{dkms_name} -v %{version} -q || :
dkms install -m %{dkms_name} -v %{version} -q --force || :

%preun
# Remove all versions from DKMS registry:
dkms remove -m %{dkms_name} -v %{version} -q --all || :

%files
%license LICENSE
%doc README.md
%{_usrsrc}/%{dkms_name}-%{version}

%changelog
* Thu Aug 22 2024 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.18-0
- 0.0.18 release of LenovoLegionLinux DKMS module.
