import SwiftUI

struct MonitorPopoverView: View {
    let snapshot: Snapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            header
            section("SYSTEM") {
                metricRow("CPU", percent: snapshot.cpu.percent, detail: "load \(fmt(snapshot.cpu.load1))/\(fmt(snapshot.cpu.load5))/\(fmt(snapshot.cpu.load15))")
                metricRow("RAM", percent: snapshot.memory.percent, detail: "\(bytes(snapshot.memory.usedBytes)) / \(bytes(snapshot.memory.totalBytes))")
            }
            section("IO") {
                ForEach(snapshot.network.prefix(2)) { item in
                    plainRow("NET \(item.name)", "\(bytesPerSecond(item.totalRate))")
                }
                if snapshot.network.isEmpty {
                    plainRow("NET", "no active physical device")
                }
                ForEach(snapshot.disks.prefix(2)) { disk in
                    plainRow("DSK \(disk.mount)", "\(bytes(disk.usedBytes)) \(Int(disk.percent.rounded()))%")
                }
            }
            section("TOP") {
                Grid(alignment: .leading, horizontalSpacing: 14, verticalSpacing: 5) {
                    GridRow {
                        columnHeader("CPU")
                        columnHeader("RAM")
                        columnHeader("DISK")
                        columnHeader("NET")
                    }
                    ForEach(0..<5, id: \.self) { index in
                        GridRow {
                            topCPU(index)
                            topRAM(index)
                            topDisk(index)
                            topNet(index)
                        }
                    }
                }
                .font(.system(size: 11, design: .monospaced))
            }
        }
    }

    private var header: some View {
        HStack {
            Text("Mac Monitor")
                .font(.headline)
            Spacer()
            Text(snapshot.date, style: .time)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }

    private func section<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            content()
        }
        .padding(8)
        .background(.quaternary.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
    }

    private func metricRow(_ label: String, percent: Double, detail: String) -> some View {
        HStack(spacing: 8) {
            Text(label)
                .font(.caption.monospaced().bold())
                .frame(width: 32, alignment: .leading)
            ProgressView(value: min(max(percent, 0), 100), total: 100)
                .frame(width: 110)
            Text("\(Int(percent.rounded()))%")
                .font(.caption.monospacedDigit())
                .frame(width: 34, alignment: .trailing)
            Text(detail)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }

    private func plainRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(.caption.monospaced().bold())
            Spacer()
            Text(value)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
        }
    }

    private func columnHeader(_ title: String) -> some View {
        Text(title)
            .foregroundStyle(.secondary)
            .frame(width: 86, alignment: .leading)
    }

    @ViewBuilder
    private func topCPU(_ index: Int) -> some View {
        if snapshot.topCPU.indices.contains(index) {
            let item = snapshot.topCPU[index]
            Text("\(item.command) \(fmt(item.cpuCores))c")
                .lineLimit(1)
                .frame(width: 86, alignment: .leading)
        } else {
            Text("")
                .frame(width: 86, alignment: .leading)
        }
    }

    @ViewBuilder
    private func topRAM(_ index: Int) -> some View {
        if snapshot.topMemory.indices.contains(index) {
            let item = snapshot.topMemory[index]
            Text("\(item.command) \(bytes(item.memoryBytes))")
                .lineLimit(1)
                .frame(width: 86, alignment: .leading)
        } else {
            Text("")
                .frame(width: 86, alignment: .leading)
        }
    }

    @ViewBuilder
    private func topDisk(_ index: Int) -> some View {
        if snapshot.disks.indices.contains(index) {
            let item = snapshot.disks[index]
            Text("\(item.mount) \(bytes(item.usedBytes))")
                .lineLimit(1)
                .frame(width: 86, alignment: .leading)
        } else {
            Text("")
                .frame(width: 86, alignment: .leading)
        }
    }

    @ViewBuilder
    private func topNet(_ index: Int) -> some View {
        if snapshot.network.indices.contains(index) {
            let item = snapshot.network[index]
            Text("\(item.name) \(bytesPerSecond(item.totalRate))")
                .lineLimit(1)
                .frame(width: 86, alignment: .leading)
        } else {
            Text("")
                .frame(width: 86, alignment: .leading)
        }
    }
}

private func fmt(_ value: Double) -> String {
    String(format: "%.1f", value)
}

private func bytes(_ value: Int64) -> String {
    ByteCountFormatter.string(fromByteCount: value, countStyle: .memory)
}

private func bytesPerSecond(_ value: Double) -> String {
    "\(ByteCountFormatter.string(fromByteCount: Int64(value), countStyle: .memory))/s"
}
