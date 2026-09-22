# socat 1.8.1.3 Cygport for Windows

This section provides a Cygport package for building and installing Socat 1.8.1.3 on Windows using Cygwin.

## Description

Socat (SOcket CAT) is a multipurpose relay tool for bidirectional data transfer between two independent data channels. This project aims to simplify the process of building and installing Socat 1.8.1.3 on Windows systems using Cygwin and Cygport.

## Prerequisites

- Cygwin installed on your Windows system
- The following Cygwin packages:
  - gcc-core
  - gcc-g++
  - make
  - cygport
  - binutils
  - patch
  - diffutils
  - autoconf
  - automake
  - git
  - subversion
  - wget
  - curl

## Installation

1. Install required Cygwin packages (with admin rights):

   ```console
   setup-x86_64.exe -q -P cygport,gcc-core,gcc-g++,make,patch,diffutils,binutils,autoconf,automake,git,subversion,wget,curl
   ```

2. Clone this repository:

   ```console
   git clone https://github.com/valorisa/socat_1.8.1.0-for-Windows.git
   cd socat_1.8.1.0-for-Windows
   ```

3. Build the package:

   ```console
   cygport socat.cygport all
   ```

4. Create a custom Cygwin package directory:

   ```console
   mkdir -p /cygdrive/c/cygwin-custom/x86_64/release
   cp *.tar.xz /cygdrive/c/cygwin-custom/x86_64/release/
   ```

5. Generate the setup.ini file:

   ```console
   cd /cygdrive/c/cygwin-custom
   mksetupini
   ```

6. Run Cygwin setup and install the package from the local directory.

## Usage

After installation, you can use Socat by running:

```bash
socat [options]
```

For more information on Socat usage, refer to the official documentation.

## socat.cygport file

```bash
NAME="socat"
VERSION="1.8.1.0"
CATEGORY="net"
SRC_URI="<http://www.dest-unreach.org/socat/download/${NAME}-${VERSION}.tar.gz>"
HOMEPAGE="<http://www.dest-unreach.org/socat/>"
LICENSE="GPLv2"
REQUIRES="cygwin"

SRC_DIR="${NAME}-${VERSION}"

# Default configure options

src_configure() {
    ./configure
}

# Installation du package

src_compile() {
    make
}

# Installation dans l'arborescence Cygwin

src_install() {
    make install
}

# Vérification du package après installation

check() {
    socat -V
}
```

## Troubleshooting

If you encounter issues during the build or installation process, please check the Troubleshooting section in the project wiki.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GPL-2.0 License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Socat developers for creating this versatile tool
- Cygwin team for providing a Unix-like environment for Windows

Citations:
[1] <https://github.com/valorisa/socat-1.7.4.3-for-Windows/blob/main/README.md>
[2] <https://sourceware.org/pipermail/cygwin/2015-July.txt>
[3] <https://github.com/StudioEtrange/socat-windows/blob/master/README>
[4] <https://cygwin.com/packages/src_package_list.html>
[5] <https://publiccloudimagechangeinfo.suse.com/google/sles-15-sp5-chost-byos-v20241216-x86-64/package_changelogs.html>
[6] <https://publiccloudimagechangeinfo.suse.com/google/sles-15-sp6-sap-v20250129-x86-64/package_changelogs.html>
[7] <https://sourceware.org/pipermail/cygwin/2023-March.txt>
[8] <https://repo.or.cz/?a=project_index>
