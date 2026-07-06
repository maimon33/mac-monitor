import Foundation
import SwiftUI

@MainActor
final class MetricSampler: ObservableObject {
    @Published private(set) var snapshot = Snapshot()

    private var samplingTask: Task<Void, Never>?
    private var isSampling = false
    private var lastNetworkCounters: [String: (rx: Int64, tx: Int64)] = [:]
    private var lastNetworkDate: Date?

    var menuTitle: String {
        let cpu = snapshot.cpu.percent.rounded()
        let ram = snapshot.memory.percent.rounded()
        return "CPU \(Int(cpu))%  RAM \(Int(ram))%"
    }

    func start() {
        guard samplingTask == nil else { return }
        samplingTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.sample()
                try? await Task.sleep(nanoseconds: 1_000_000_000)
            }
        }
    }

    func sample() async {
        guard !isSampling else { return }
        isSampling = true
        let now = Date()
        let previousCounters = lastNetworkCounters
        let previousDate = lastNetworkDate

        let result = await Task.detached(priority: .utility) {
            collectSnapshot(previousNetworkCounters: previousCounters, previousNetworkDate: previousDate, now: now)
        }.value

        lastNetworkCounters = result.networkCounters
        lastNetworkDate = now
        snapshot = result.snapshot
        isSampling = false
    }

    deinit {
        samplingTask?.cancel()
    }
}

private struct SampleResult {
    let snapshot: Snapshot
    let networkCounters: [String: (rx: Int64, tx: Int64)]
}

private func collectSnapshot(
    previousNetworkCounters: [String: (rx: Int64, tx: Int64)],
    previousNetworkDate: Date?,
    now: Date
) -> SampleResult {
    let counters = collectNetworkCounters()
    let elapsed = previousNetworkDate.map { now.timeIntervalSince($0) } ?? 0
    let networks = buildNetworkStats(current: counters, previous: previousNetworkCounters, elapsed: elapsed)
    let processes = collectProcesses(limit: 12)
    let snapshot = Snapshot(
        date: now,
        cpu: collectCPU(processes: processes),
        memory: collectMemory(),
        disks: collectDisks(limit: 5),
        networks: networks,
        topCPU: Array(processes.sorted { $0.cpuPercent > $1.cpuPercent }.prefix(5)),
        topMemory: Array(processes.sorted { $0.memoryBytes > $1.memoryBytes }.prefix(5))
    )
    return SampleResult(snapshot: snapshot, networkCounters: counters)
}

private func runCommand(_ executable: String, _ args: [String]) -> String {
    let process = Process()
    let pipe = Pipe()
    process.executableURL = URL(fileURLWithPath: executable)
    process.arguments = args
    process.standardOutput = pipe
    process.standardError = Pipe()

    do {
        try process.run()
        process.waitUntilExit()
        let data = pipe.fileHandleForReading.readDataToEndOfFile()
        return String(data: data, encoding: .utf8) ?? ""
    } catch {
        return ""
    }
}

private func collectCPU(processes: [ProcessStats]) -> CPUStats {
    let totalProcessCPU = processes.reduce(0) { $0 + $1.cpuPercent }
    let cores = max(ProcessInfo.processInfo.processorCount, 1)
    let loads = ProcessInfo.processInfo.systemUptime >= 0 ? loadAverages() : (0, 0, 0)
    return CPUStats(
        percent: min(100, totalProcessCPU / Double(cores)),
        load1: loads.0,
        load5: loads.1,
        load15: loads.2,
        cores: cores
    )
}

private func loadAverages() -> (Double, Double, Double) {
    var loads = [Double](repeating: 0, count: 3)
    let count = getloadavg(&loads, 3)
    guard count == 3 else { return (0, 0, 0) }
    return (loads[0], loads[1], loads[2])
}

private func collectMemory() -> MemoryStats {
    let totalOutput = runCommand("/usr/sbin/sysctl", ["-n", "hw.memsize"]).trimmingCharacters(in: .whitespacesAndNewlines)
    let total = Int64(totalOutput) ?? 0
    let output = runCommand("/usr/bin/vm_stat", [])

    var pageSize: Int64 = 4096
    if let match = output.range(of: #"page size of ([0-9]+) bytes"#, options: .regularExpression) {
        let text = String(output[match])
        let digits = text.filter(\.isNumber)
        pageSize = Int64(digits) ?? pageSize
    }

    var pages: [String: Int64] = [:]
    output.split(separator: "\n").forEach { line in
        let parts = line.split(separator: ":", maxSplits: 1)
        guard parts.count == 2 else { return }
        let key = parts[0].trimmingCharacters(in: .whitespaces)
        let digits = parts[1].filter(\.isNumber)
        pages[key] = Int64(digits) ?? 0
    }

    let freePages = (pages["Pages free"] ?? 0) + (pages["Pages speculative"] ?? 0)
    let free = freePages * pageSize
    return MemoryStats(totalBytes: total, usedBytes: max(0, total - free))
}

private func collectDisks(limit: Int) -> [DiskStats] {
    let output = runCommand("/bin/df", ["-k"])
    return output
        .split(separator: "\n")
        .dropFirst()
        .compactMap { line -> DiskStats? in
            let parts = line.split(separator: " ")
            guard parts.count >= 9 else { return nil }
            let filesystem = String(parts[0])
            let mount = String(parts.last ?? "")
            guard !shouldSkipMount(filesystem: filesystem, mount: mount) else { return nil }
            guard let totalKB = Int64(parts[1]), let usedKB = Int64(parts[2]), let freeKB = Int64(parts[3]) else { return nil }
            return DiskStats(mount: displayMount(mount), usedBytes: usedKB * 1024, freeBytes: freeKB * 1024, totalBytes: totalKB * 1024)
        }
        .sorted { $0.percent > $1.percent }
        .prefix(limit)
        .map { $0 }
}

private func shouldSkipMount(filesystem: String, mount: String) -> Bool {
    if filesystem == "devfs" || filesystem == "map" { return true }
    if mount.hasPrefix("/System/Volumes/Data/") { return true }
    if mount.hasPrefix("/System/Volumes/") && mount != "/System/Volumes/Data" { return true }
    return false
}

private func displayMount(_ mount: String) -> String {
    mount == "/System/Volumes/Data" ? "Data" : mount
}

private func collectNetworkCounters() -> [String: (rx: Int64, tx: Int64)] {
    let physical = Set(activePhysicalInterfaces())
    let output = runCommand("/usr/sbin/netstat", ["-ibn"])
    var counters: [String: (rx: Int64, tx: Int64)] = [:]

    for line in output.split(separator: "\n") {
        let parts = line.split(separator: " ")
        guard parts.count >= 10, parts[0] != "Name" else { continue }
        let rawName = String(parts[0])
        let name = rawName.split(separator: ".").first.map(String.init) ?? rawName
        guard physical.contains(name) else { continue }
        guard let rx = Int64(parts[6]), let tx = Int64(parts[9]) else { continue }
        let old = counters[name] ?? (0, 0)
        counters[name] = (max(old.rx, rx), max(old.tx, tx))
    }

    return counters
}

private func activePhysicalInterfaces() -> [String] {
    let output = runCommand("/sbin/ifconfig", [])
    let blocks = output.components(separatedBy: "\n").reduce(into: [String]()) { partial, line in
        if line.first?.isWhitespace == false {
            partial.append(line)
        } else if let last = partial.indices.last {
            partial[last] += "\n" + line
        }
    }

    return blocks.compactMap { block in
        guard let firstLine = block.split(separator: "\n").first else { return nil }
        guard let name = firstLine.split(separator: ":").first.map(String.init) else { return nil }
        guard name.range(of: #"^en[0-9]+$"#, options: .regularExpression) != nil else { return nil }
        return block.contains("status: active") ? name : nil
    }
}

private func buildNetworkStats(
    current: [String: (rx: Int64, tx: Int64)],
    previous: [String: (rx: Int64, tx: Int64)],
    elapsed: TimeInterval
) -> [NetworkStats] {
    current.map { name, value in
        let old = previous[name]
        let rxRate = old.map { max(0, Double(value.rx - $0.rx) / max(elapsed, 0.001)) } ?? 0
        let txRate = old.map { max(0, Double(value.tx - $0.tx) / max(elapsed, 0.001)) } ?? 0
        return NetworkStats(name: name, rxBytes: value.rx, txBytes: value.tx, rxRate: rxRate, txRate: txRate)
    }
    .sorted { $0.totalRate > $1.totalRate }
}

private func collectProcesses(limit: Int) -> [ProcessStats] {
    let output = runCommand("/bin/ps", ["-axo", "pid=,%cpu=,%mem=,rss=,comm="])
    return output.split(separator: "\n").compactMap { line in
        let parts = line.split(separator: " ", maxSplits: 4, omittingEmptySubsequences: true)
        guard parts.count == 5 else { return nil }
        guard let pid = Int32(parts[0]),
              let cpu = Double(parts[1]),
              let mem = Double(parts[2]),
              let rssKB = Int64(parts[3]) else { return nil }
        let command = URL(fileURLWithPath: String(parts[4])).lastPathComponent
        return ProcessStats(pid: pid, command: command, cpuPercent: cpu, memoryPercent: mem, memoryBytes: rssKB * 1024)
    }
    .sorted { $0.cpuPercent > $1.cpuPercent }
    .prefix(limit)
    .map { $0 }
}
