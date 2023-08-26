%global python3_pkgversion 3.11

Name:           lenovolegionlinux
Version:        1.0.0
Release:        1%{?dist}
Summary:        lenovolegionlinux Python library

License:        Custom License
URL:            https://github.com/albertosottile/lenovolegionlinux
Source0:        lenovolegionlinux-1.0.0.tar.gz

BuildArch:      noarch
BuildRequires:  python%{python3_pkgversion}-devel                     

# Build dependencies needed to be specified manually
BuildRequires:  python%{python3_pkgversion}-setuptools


%global _description %{expand:
Driver and tools for controlling Lenovo Legion laptops in Linux including fan control and power mode.}

%description %_description

%package -n python%{python3_pkgversion}-lenovolegionlinux                         
Summary:        %{summary}

%description -n python%{python3_pkgversion}-lenovolegionlinux %_description


%prep
%autosetup -p1 -n lenovolegionlinux-%{version}


%build
# The macro only supported projects with setup.py
%py3_build                                                            


%install
# The macro only supported projects with setup.py
%py3_install
install -D -m 0644 %{_sourcedir}/extra/service/legion-linux.service %{_unitdir}/legion-linux.service
install -D -m 0644 %{_sourcedir}/extra/service/legion-linux.path %{_unitdir}/legion-linux.path


%check                                                                
%{pytest}


# Note that there is no %%files section for the unversioned python module
%files -n python%{python3_pkgversion}-lenovolegionlinux
%doc README.md
%license LICENSE