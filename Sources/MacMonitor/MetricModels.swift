import Foundation

struct Snapshot {
    var date = Date()
    var cpu = CPUStats()
    var memory = MemoryStats()
    var disks: [DiskStats] = []
    var networks: [NetworkStats] = []
    var topCPU: [ProcessStats] = []
    var topMemory: [ProcessStats] = []
}

struct CPUStats {
    var percent: Double = 0
    var load1: Double = 0
    var load5: Double = 0
    var load15: Double = 0
    var cores: Int = ProcessInfo.processInfo.processorCount
}

struct MemoryStats {
    var totalBytes: Int64 = 0
    var usedBytes: Int64 = 0

    var percent: Double {
        guard totalBytes > 0 else { return 0 }
        return Double(usedBytes) / Double(totalBytes) * 100
    }
}

struct DiskStats: Identifiable {
    var id: String { mount }
    var mount: String
    var usedBytes: Int64
    var freeBytes: Int64
    var totalBytes: Int64

    var percent: Double {
        guard totalBytes > 0 else { return 0 }
        return Double(usedBytes) / Double(totalBytes) * 100
    }
}

struct NetworkStats: Identifiable {
    var id: String { name }
    var name: String
    var rxBytes: Int64
    var txBytes: Int64
    var rxRate: Double
    var txRate: Double

    var totalBytes: Int64 { rxBytes + txBytes }
    var totalRate: Double { rxRate + txRate }
}

struct ProcessStats: Identifiable {
    var id: Int32 { pid }
    var pid: Int32
    var command: String
    var cpuPercent: Double
    var memoryPercent: Double
    var memoryBytes: Int64

    var cpuCores: Double { cpuPercent / 100 }
}
