%global srcname darkdetect
%define version _VERSION

Summary: Detect OS Dark Mode from Python
Name: python-darkdetect
Version: %{version}
Release: 1
Source0: %{name}-%{version}.tar.gz
License: BSD-3-Clause
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
BuildRequires:  python3-devel
BuildRequires:  python3-wheel
Vendor: Alberto Sottile <asottile@gmail.com>
Packager: Gonçalo Negrier Duarte <gonegrier.duarte@gamil.com>
Url: https://github.com/albertosottile/darkdetect

%description
# Darkdetect (UNOFFICIAL RPM)

This package allows to detect if the user is using Dark Mode on:

- [macOS 10.14+](https://support.apple.com/en-us/HT208976)
- [Windows 10 1607+](https://blogs.windows.com/windowsexperience/2016/08/08/windows-10-tip-personalize-your-pc-by-enabling-the-dark-theme/)
- Linux with [a dark GTK theme](https://www.gnome-look.org/browse/cat/135/ord/rating/?tag=dark).

The main application of this package is to detect the Dark mode from your GUI Python application (Tkinter/wx/pyqt/qt for python (pyside)/...) and apply the needed adjustments to your interface. Darkdetect is particularly useful if your GUI library **does not** provide a public API for this detection (I am looking at you, Qt). In addition, this package does not depend on other modules or packages that are not already included in standard Python distributions.


## Usage

```
import darkdetect

>>> darkdetect.theme()
'Dark'

>>> darkdetect.isDark()
True

>>> darkdetect.isLight()
False
```
It's that easy.

You can create a dark mode switch listener daemon thread with `darkdetect.listener` and pass a callback function. The function will be called with string "Dark" or "Light" when the OS switches the dark mode setting.

``` python
import threading
import darkdetect

# def listener(callback: typing.Callable[[str], None]) -> None: ...

t = threading.Thread(target=darkdetect.listener, args=(print,))
t.daemon = True
t.start()
```

## Install

The preferred channel is PyPI:
```
pip install darkdetect
```

Alternatively, you are free to vendor directly a copy of Darkdetect in your app. Further information on vendoring can be found [here](https://medium.com/underdog-io-engineering/vendoring-python-dependencies-with-pip-b9eb6078b9c0).

## Optional Installs

To enable the macOS listener, additional components are required, these can be installed via:
```bash
pip install darkdetect[macos-listener]
```

## Notes

- This software is licensed under the terms of the 3-clause BSD License.
- This package can be installed on any operative system, but it will always return `None` unless executed on a OS that supports Dark Mode, including older versions of macOS and Windows.
- On macOS, detection of the dark menu bar and dock option (available from macOS 10.10) is not supported.
- [Details](https://stackoverflow.com/questions/25207077/how-to-detect-if-os-x-is-in-dark-mode) on the detection method used on macOS.
- [Details](https://askubuntu.com/questions/1261366/detecting-dark-mode#comment2132694_1261366) on the experimental detection method used on Linux.


%prep
%autosetup -n %{name}-%{version} -n %{name}-%{version}

%build
unset RPM_BUILD_ROOT
%{python3} setup.py bdist_wheel

%install
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
mkdir %{buildroot}
mkdir %{buildroot}/usr
cd "%{_builddir}/%{name}-%{version}"
%{python3} -m installer --destdir="%{buildroot}" dist/*.whl

%files -n python-%{srcname}
%{python3_sitelib}/darkdetect/*
%{python3_sitelib}/darkdetect-%{version}.dist-info/*
