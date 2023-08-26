# norootforbuild

Name:         LenovoLegionLinux
License:      GPL
Group:        System/Kernel
Summary:      LenovoLegionLinux Kernel Module Package
Version:      1.0
Release:      0
BuildRoot:    %{_tmppath}/%{name}-%{version}-build

%description
Driver for controlling Lenovo Legion laptops including fan control and power mode. 

%package KMP
Summary: LenovoLegionLinux Kernel Module
Group: System/Kernel

%description KMP
This is one of the subpackages require for LenovoLegionLinux [kernel module/driver]

%prep
set -- *
mkdir source
mv "$@" source/
mkdir obj

%build
for flavor in %flavors_to_build; do
    rm -rf obj/$flavor
    cp -r source obj/$flavor
    make -C /usr/src/linux/%_target_cpu/$flavor M=$PWD/obj/$flavor
done

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
export INSTALL_MOD_DIR=updates
for flavor in %flavors_to_build; do
    make -C /usr/src/linux/%_target_cpu/$flavor install M=$PWD/obj/$flavor
done

%clean
rm -rf %{buildroot}

%changelog
Intial Release