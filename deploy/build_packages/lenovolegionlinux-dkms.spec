# norootforbuild
%define srcname LenovoLegionLinux
%global dkms_name %{srcname}
%global debug_package %{nil}

Name:         dkms-%{srcname}
License:      GPL-2.0
Group:        System/Kernel
Summary:      LenovoLegionLinux Kernel Module Package
Version:      0.0.32
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
* Wed Sep 23 2026 github-actions <actions@github.com> - 0.0.32-0
- 0.0.32 release of LenovoLegionLinux DKMS module.
* Mon Sep 21 2026 github-actions <actions@github.com> - 0.0.31-0
- 0.0.31 release of LenovoLegionLinux DKMS module.
* Thu Sep 17 2026 github-actions <actions@github.com> - 0.0.30-0
- 0.0.30 release of LenovoLegionLinux DKMS module.
* Wed Sep 16 2026 github-actions <actions@github.com> - 0.0.29-0
- 0.0.29 release of LenovoLegionLinux DKMS module.
* Mon Sep 14 2026 github-actions <actions@github.com> - 0.0.28-0
- 0.0.28 release of LenovoLegionLinux DKMS module.
* Mon Sep 14 2026 github-actions <actions@github.com> - 0.0.27-0
- 0.0.27 release of LenovoLegionLinux DKMS module.
* Fri Sep 11 2026 github-actions <actions@github.com> - 0.0.26-0
- 0.0.26 release of LenovoLegionLinux DKMS module.
* Mon Sep 07 2026 github-actions <actions@github.com> - 0.0.25-0
- 0.0.25 release of LenovoLegionLinux DKMS module.
* Thu Sep 03 2026 github-actions <actions@github.com> - 0.0.24-0
- 0.0.24 release of LenovoLegionLinux DKMS module.
* Tue Sep 01 2026 github-actions <actions@github.com> - 0.0.23-0
- 0.0.23 release of LenovoLegionLinux DKMS module.
* Sat Aug 15 2026 github-actions <actions@github.com> - 0.0.22-0
- 0.0.22 release of LenovoLegionLinux DKMS module.
* Fri Aug 07 2026 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.21-0
- 0.0.21 release of LenovoLegionLinux DKMS module.

* Thu Aug 22 2024 Gonçalo Negrier Duarte <gonegrier.duarte@gmail.com> - 0.0.18-0
- 0.0.18 release of LenovoLegionLinux DKMS module.
