# mac-monitor

A small, dependency-free macOS CLI for the stats you usually want at a glance:

- Network traffic by interface, with RX/TX rates and totals
- CPU usage, load average, and top CPU processes
- RAM usage from `vm_stat`
- Disk capacity by mounted filesystem

It is intentionally much smaller than tools like `btop`, `glances`, `bottom`, or `bandwhich`, but it borrows their best ideas: one readable terminal view, scriptable output, and knobs you can control.

## Install locally

```bash
python3 -m pip install -e .
```

Then run:

```bash
mac-monitor
```

or:

```bash
mm
```

During local development you can also run the bundled shim:

```bash
./bin/mac-monitor
```

## Examples

Show one snapshot:

```bash
mac-monitor --once
```

Watch every second:

```bash
mac-monitor --interval 1
```

The default watch mode uses a full-screen terminal console when stdout is a TTY. Disable it when piping or when you want scrolling output:

```bash
mac-monitor --no-screen
mac-monitor --no-clear
```

Only show selected interfaces:

```bash
mac-monitor --interface en0 --interface utun0
```

By default, network rows only include active physical macOS devices (`en*`, usually Wi-Fi/Ethernet). Include VPN, bridge, tunnel, and other logical interfaces when needed:

```bash
mac-monitor --all-interfaces
```

JSON for scripts:

```bash
mac-monitor --once --json
```

Show more processes and disks:

```bash
mac-monitor --top 8 --disk-limit 8
```

Switch console views:

```bash
mac-monitor --view all
mac-monitor --view overview
mac-monitor --view top --top-count 10
mac-monitor --no-top
```

Print the default config:

```bash
mac-monitor --print-config
```

Use your own config:

```bash
mac-monitor --config ./monitor.json
```

Default config path:

```text
~/.config/mac-monitor/config.json
```

## Config

All settings are optional:

```json
{
  "interval": 1.0,
  "interfaces": [],
  "top_count": 5,
  "top_processes": 5,
  "disk_limit": 5,
  "view": "all",
  "show_loopback": false,
  "show_logical_interfaces": false,
  "warn_cpu_percent": 85.0,
  "warn_memory_percent": 85.0,
  "warn_disk_percent": 90.0
}
```

CLI flags override config values.

## Notes

This tool uses macOS system commands and standard library APIs (`netstat`, `vm_stat`, `ps`, `df`, `sysctl`). It does not sniff packets and does not need root permissions.

## Later UI paths

The monitor is already split into data collection (`mac_monitor.monitor`) and rendering (`mac_monitor.render`), so other shells can reuse the same snapshot model.

- Separate terminal window: easy. Launch `mac-monitor` inside Terminal.app, iTerm, or Alacritty.
- Native menu bar icon: medium. Use a small Swift/SwiftUI wrapper or a Python app bundle with a status item, then call the monitor sampler.
- Desktop widget: medium to hard. macOS widgets are best done in Swift/WidgetKit and prefer timeline snapshots over always-on polling.
- Native floating window: medium. A SwiftUI or PyObjC app can show the same metrics with better controls and permissions.

## Swift prototype

A native Swift menu-bar prototype now lives in `Sources/MacMonitor`. See `SWIFT.md`.

Build a downloadable local app bundle:

```bash
./scripts/package-macos.sh
open dist/MacMonitor.app
```

GitHub Actions also uploads `MacMonitor.app.zip` as a workflow artifact after successful `main` builds. Pushing a tag like `v0.1.0` publishes the zip as a GitHub Release asset.
