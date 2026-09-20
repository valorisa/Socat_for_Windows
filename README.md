# Compiling socat 1.8.1.3 on Windows 11 using Cygwin

## Description

Socat (SOcket CAT) is a multipurpose relay tool for bidirectional data transfer between two independent data channels.  Each channel may be a file, pipe, device (serial line etc. or a pseudo terminal), socket (UNIX, IP4, IP6, raw, UDP, TCP), TLS socket, proxy CONNECT connection, file descriptor (stdin etc.), the GNU line editor (readline), a program, or a combination of two of those. These modes include generation of 'listening' sockets, named pipes, and pseudo terminals. This project aims to simplify the process of building and installing Socat 1.8.1.3 on Windows systems using Cygwin.

## Step 1: Install Cygwin

1. **Download the Cygwin Installer**:
   - Go to the official Cygwin website: [https://www.cygwin.com/](https://www.cygwin.com/)
   - Download the appropriate installer (`setup-x86_64.exe` for a 64-bit architecture).

2. **Run the Cygwin Installer**:
   - Execute `setup-x86_64.exe`.
   - Choose an installation directory (e.g., `C:\cygwin64`).
   - Select a package cache directory (e.g., `C:\cygwin64\packages`).

3. **Select Necessary Packages**:
   - When you reach the screen where you can select packages to install, search for and install the following packages:
     - **gcc-core**: For C compilation.
     - **make**: To manage build scripts.
     - **automake**: To generate configuration files.
     - **autoconf**: To configure sources.
     - **libtool**: For shared library management.
     - **openssl-devel**: For SSL/TLS support.

   You can use the search bar to find these packages more easily.

4. **Complete the Installation**:
   - Continue with the installation by following the instructions.

## Step 2: Download socat Source Code (Version 1.8.1.3)

1. Open a Cygwin terminal:
   - You can find a shortcut in the Start menu or run `C:\cygwin64\Cygwin.bat`.

2. Download the socat source code (version 1.8.1.3):

   ```bash
   wget http://www.dest-unreach.org/socat/download/socat-1.8.1.3.tar.gz
   ```

3. Extract the source code:

   ```bash
   tar -xzf socat-1.8.1.3.tar.gz
   cd socat-1.8.1.3
   ```

## Step 3: Compile socat

1. Prepare the sources for compilation:

   ```bash
   ./configure
   ```

   If you encounter errors related to OpenSSL, ensure that `openssl-devel` is installed via Cygwin.

2. Compile socat:

   ```bash
   make
   ```

3. Verify the compilation:
   - Once the compilation is complete, you should have an executable `socat.exe` in the current directory (`your_current_directory`).

4. (Optional) Install socat within the Cygwin environment:

   ```bash
   make install
   ```

   This installs `socat.exe` (and its man page) into the standard Cygwin
   prefix, typically `/usr/local/bin` (i.e. `C:\cygwin64\usr\local\bin`),
   making `socat` immediately available from any Cygwin terminal without
   manually copying the binary around. Two things worth knowing before
   relying on it:

   - **It only covers the Cygwin side.** `/usr/local/bin` is added to the
     `PATH` *inside* Cygwin, not to the native Windows `PATH`. Running
     `socat` from `cmd.exe` or PowerShell still requires Step 4 (copy the
     binary to a Windows-accessible folder and add it to the system
     `PATH`) — or, alternatively, adding `C:\cygwin64\usr\local\bin`
     itself to the Windows `PATH`.
   - **`cygwin1.dll` is required either way.** This build is linked
     against Cygwin's POSIX layer, so `socat.exe` needs `cygwin1.dll`
     (found in `C:\cygwin64\bin`) reachable — either next to `socat.exe`
     or on the `PATH` — to run outside a Cygwin terminal. `make install`
     does not copy this DLL for you.
   - You can also target a Windows-visible path directly, e.g.
     `make install prefix=/cygdrive/c/socat`, to skip the manual copy in
     Step 4 altogether.

   If `/usr/local` isn't writable by your user, run this from an elevated
   Cygwin terminal, or install to a custom prefix as shown above.

## Step 4: Use socat.exe

1. Copy `socat.exe` to an accessible directory from your Windows command line:

   ```bash
   cp your_current_directory/socat.exe /cygdrive/c/path/to/your/desired/location/
   ```

   For example, if you want to copy `socat.exe` to `C:\Program Files\socat`, use:

   ```bash
   cp your_current_directory/socat.exe /cygdrive/c/Program\ Files/socat/
   ```

2. Add this directory to the system PATH to be able to use `socat` from anywhere:
   - Open Windows Settings.
   - Go to System > About > Advanced system settings.
   - Click on "Environment Variables".
   - In the "System variables" section, find and select the `Path` variable, then click "Edit".
   - Click "New" and add the path to the folder containing `socat.exe` (e.g., `C:\Program Files\socat`).
   - Click "OK" to close all windows.

## Addendum 

Otherwise for the others, there is one ready-made file '*socat-1.8.1.3.7z*'. You can download it by going to : **socat-1.8.1.3.7z** and proceeding by keyboard shortcut (Ctrl + Shift + s).

## Conclusion

You now have compiled `socat` version 1.8.1.3 under Windows 11 using Cygwin and obtained an executable `socat.exe`. You can use it directly from the Windows command line after adding its location to the PATH. This method provides maximum flexibility to adapt `socat` to your specific needs.

This will help other users understand and follow the process clearly.
