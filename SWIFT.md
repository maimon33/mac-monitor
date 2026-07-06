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

## Package

Create a local `.app` bundle and zip:

```bash
./scripts/package-macos.sh
```

Output:

```text
dist/MacMonitor.app
dist/MacMonitor.app.zip
```

Install locally by unzipping and moving `MacMonitor.app` to `/Applications`, or run it directly:

```bash
open dist/MacMonitor.app
```

The app bundle is ad-hoc signed locally with `codesign --sign -`. It is not notarized yet, so macOS may still show Gatekeeper warnings when downloaded from GitHub.

## Avoid Gatekeeper Confirmation

To avoid the "cannot verify developer" / confirmation flow for downloaded builds, the app must be signed with an Apple Developer ID certificate and notarized by Apple. Ad-hoc signing is only useful for local packaging.

Add these GitHub Actions secrets to enable signing and notarization:

```text
MACOS_CERTIFICATE_P12       base64-encoded Developer ID Application .p12
MACOS_CERTIFICATE_PASSWORD  password for the .p12
MACOS_KEYCHAIN_PASSWORD     temporary CI keychain password
MACOS_SIGNING_IDENTITY      Developer ID Application: Your Name (TEAMID)
APPLE_ID                    Apple ID email
APPLE_APP_PASSWORD          app-specific password
APPLE_TEAM_ID               Apple Developer team ID
```

With those secrets present, the release workflow signs with hardened runtime, submits the zip to Apple notary service, staples the ticket, and re-zips the stapled app.

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
