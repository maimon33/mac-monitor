import SwiftUI

struct MonitorWindowView: View {
    let snapshot: Snapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Mac Monitor")
                        .font(.title2.bold())
                    Text(snapshot.date, style: .time)
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
                summaryPill("CPU", "\(Int(snapshot.cpu.percent.rounded()))%")
                summaryPill("RAM", "\(Int(snapshot.memory.percent.rounded()))%")
            }

            HStack(alignment: .top, spacing: 12) {
                VStack(alignment: .leading, spacing: 12) {
                    panel("SYSTEM") {
                        metricRow("CPU", percent: snapshot.cpu.percent, detail: "load \(fmt(snapshot.cpu.load1))/\(fmt(snapshot.cpu.load5))/\(fmt(snapshot.cpu.load15))")
                        metricRow("RAM", percent: snapshot.memory.percent, detail: "\(bytes(snapshot.memory.usedBytes)) / \(bytes(snapshot.memory.totalBytes))")
                    }

                    panel("IO") {
                        if snapshot.networks.isEmpty {
                            plainRow("NET", "no active physical device")
                        } else {
                            ForEach(Array(snapshot.networks.prefix(3))) { item in
                                plainRow("NET \(item.name)", bytesPerSecond(item.totalRate))
                            }
                        }

                        ForEach(snapshot.disks.prefix(3)) { disk in
                            plainRow("DSK \(disk.mount)", "\(bytes(disk.usedBytes)) \(Int(disk.percent.rounded()))%")
                        }
                    }
                }
                .frame(width: 280, alignment: .topLeading)

                panel("TOP CONSUMERS") {
                    Grid(alignment: .leading, horizontalSpacing: 16, verticalSpacing: 7) {
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
                    .font(.system(size: 12, design: .monospaced))
                }
                .frame(maxWidth: .infinity, alignment: .topLeading)
            }
        }
        .padding(16)
        .background(.background)
    }

    private func summaryPill(_ label: String, _ value: String) -> some View {
        HStack(spacing: 4) {
            Text(label)
                .foregroundStyle(.secondary)
            Text(value)
                .monospacedDigit()
        }
        .font(.caption.bold())
        .padding(.horizontal, 9)
        .padding(.vertical, 5)
        .background(.quaternary.opacity(0.8), in: Capsule())
    }

    private func panel<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.caption.bold())
                .foregroundStyle(.secondary)
            content()
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.quaternary.opacity(0.45), in: RoundedRectangle(cornerRadius: 8))
    }

    private func metricRow(_ label: String, percent: Double, detail: String) -> some View {
        HStack(spacing: 8) {
            Text(label)
                .font(.caption.monospaced().bold())
                .frame(width: 34, alignment: .leading)
            ProgressView(value: min(max(percent, 0), 100), total: 100)
                .frame(width: 95)
            Text("\(Int(percent.rounded()))%")
                .font(.caption.monospacedDigit())
                .frame(width: 34, alignment: .trailing)
            Text(detail)
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
                .lineLimit(1)
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
                .lineLimit(1)
        }
    }

    private func columnHeader(_ title: String) -> some View {
        Text(title)
            .foregroundStyle(.secondary)
            .frame(width: 92, alignment: .leading)
    }

    @ViewBuilder
    private func topCPU(_ index: Int) -> some View {
        if snapshot.topCPU.indices.contains(index) {
            let item = snapshot.topCPU[index]
            Text("\(item.command) \(fmt(item.cpuCores))c")
                .lineLimit(1)
                .frame(width: 92, alignment: .leading)
        } else {
            emptyTopCell
        }
    }

    @ViewBuilder
    private func topRAM(_ index: Int) -> some View {
        if snapshot.topMemory.indices.contains(index) {
            let item = snapshot.topMemory[index]
            Text("\(item.command) \(bytes(item.memoryBytes))")
                .lineLimit(1)
                .frame(width: 92, alignment: .leading)
        } else {
            emptyTopCell
        }
    }

    @ViewBuilder
    private func topDisk(_ index: Int) -> some View {
        if snapshot.disks.indices.contains(index) {
            let item = snapshot.disks[index]
            Text("\(item.mount) \(bytes(item.usedBytes))")
                .lineLimit(1)
                .frame(width: 92, alignment: .leading)
        } else {
            emptyTopCell
        }
    }

    @ViewBuilder
    private func topNet(_ index: Int) -> some View {
        if snapshot.networks.indices.contains(index) {
            let item = snapshot.networks[index]
            Text("\(item.name) \(bytesPerSecond(item.totalRate))")
                .lineLimit(1)
                .frame(width: 92, alignment: .leading)
        } else {
            emptyTopCell
        }
    }

    private var emptyTopCell: some View {
        Text("")
            .frame(width: 92, alignment: .leading)
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
