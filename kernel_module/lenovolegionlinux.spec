# norootforbuild
%global dkms_name lenovolegionlinux

Name:         dkms-lenovolegionlinux
License:      GPL
Group:        System/Kernel
Summary:      LenovoLegionLinux Kernel Module Package
Version:      _VERSION
Release:      0
Source0:      %{dkms_name}-kmod-%{version}-x86_64.tar.gz

Provides:     %{dkms_name}-kmod = %{?epoch:%{epoch}:}%{version}
Requires:     %{dkms_name}-kmod-common = %{?epoch:%{epoch}:}%{version}
Requires:     dkms

%description
Driver for controlling Lenovo Legion laptops including fan control and power mode.

%prep
%autosetup -p0 -n %{dkms_name}-kmod-%{version}-x86_64

%install
mkdir -p %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/
cp -fr * %{buildroot}%{_usrsrc}/%{dkms_name}-%{version}/

%post
dkms add -m %{dkms_name} -v %{version} -q || :
# Rebuild and make available for the currently running kernel:
dkms build -m %{dkms_name} -v %{version} -q || :
dkms install -m %{dkms_name} -v %{version} -q --force || :

%preun
# Remove all versions from DKMS registry:
dkms remove -m %{dkms_name} -v %{version} -q --all || :

%files
%{_usrsrc}/%{dkms_name}-%{version}