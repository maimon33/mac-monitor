import SwiftUI

@main
struct MacMonitorApp: App {
    @StateObject private var sampler = MetricSampler()

    var body: some Scene {
        WindowGroup("Mac Monitor") {
            MonitorWindowView(snapshot: sampler.snapshot)
                .frame(minWidth: 720, idealWidth: 760, minHeight: 420, idealHeight: 460)
                .task {
                    sampler.start()
                }
                .floatingWindow()
        }
        .windowResizability(.contentSize)

        MenuBarExtra {
            MonitorPopoverView(snapshot: sampler.snapshot)
                .frame(width: 430)
                .padding(12)
                .task {
                    sampler.start()
                }
        } label: {
            Text(sampler.menuTitle)
                .monospacedDigit()
        }
        .menuBarExtraStyle(.window)

        Settings {
            VStack(alignment: .leading, spacing: 8) {
                Text("Mac Monitor")
                    .font(.headline)
                Text("The floating window is the primary interface. The menu-bar extra stays available as a compact secondary view.")
                    .foregroundStyle(.secondary)
            }
            .padding()
            .frame(width: 420, alignment: .leading)
        }
    }
}
