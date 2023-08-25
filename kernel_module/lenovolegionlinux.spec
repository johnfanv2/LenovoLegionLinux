#
# lenovolegionlinux.spec
# Sample KMP spec file
#

# Following line included for SUSE "build" command; does not affect "rpmbuild"
# norootforbuild

Name:         LenovoLegionLinux
License:      GPL
Group:        System/Kernel
Summary:      LenovoLegionLinux Kernel Module Package
Version:      1.0
Release:      0
Source0:      %name-%version.tar.bz2
BuildRoot:    %{_tmppath}/%{name}-%{version}-build

%kernel_module_package

%description
Driver for controlling Lenovo Legion laptops including fan control and power mode. 

%prep
%setup
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
for flavor in %flavors_to_build; do
    rm -rf obj/$flavor
    cp -r source obj/$flavor
    make -C %{kernel_source $flavor} modules M=$PWD/obj/$flavor
done

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
# Following line works for SUSE 11+ and RHEL 6.1+ only, must set INSTALL_MOD_DIR manually for other targets
export INSTALL_MOD_DIR=%kernel_module_package_moddir %{name}
for flavor in %flavors_to_build; do
    make -C %{kernel_source $flavor} install M=$PWD/obj/$flavor
done

%clean
rm -rf %{buildroot}

%changelog
Intial Release