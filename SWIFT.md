# Swift Build

This repo now has a first native macOS Swift implementation under `Sources/MacMonitor`.

It is a Swift Package executable named `MacMonitor`:

```bash
swift build
swift run MacMonitor
```

The app is a menu-bar extra with a compact popover:

- System: CPU and RAM
- IO: active physical network interfaces and disks
- Top: five ranked CPU, RAM, disk, and network consumers

## Local Toolchain Note

On this machine, `swift build` currently fails before compiling project sources because the selected CommandLineTools SwiftPM installation cannot link `PackageDescription`.

Observed selected developer directory:

```text
/Library/Developer/CommandLineTools
```

Observed failure:

```text
Undefined symbols for architecture arm64:
  PackageDescription.Package.__allocating_init(...)
```

That points to a local Xcode/CommandLineTools mismatch. The usual fixes are:

```bash
xcode-select --install
```

or, if full Xcode is installed:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

Then retry:

```bash
swift build
swift run MacMonitor
```

If `xcode-select --install` says the tools are already installed but the error persists, reinstall the CommandLineTools package cleanly:

```bash
sudo rm -rf /Library/Developer/CommandLineTools
xcode-select --install
```

Then open a new terminal and verify:

```bash
xcode-select -p
swift --version
swift run MacMonitor
```

On this machine, `/Applications/Xcode.app` is not present, so switching to full Xcode is not currently available unless Xcode is installed first.
