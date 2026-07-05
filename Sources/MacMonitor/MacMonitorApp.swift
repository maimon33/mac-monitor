import SwiftUI

@main
struct MacMonitorApp: App {
    @StateObject private var sampler = MetricSampler()

    var body: some Scene {
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
            EmptyView()
        }
    }
}
