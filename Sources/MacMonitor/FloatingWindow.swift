import AppKit
import SwiftUI

extension View {
    func floatingWindow() -> some View {
        background(FloatingWindowAccessor())
    }
}

private struct FloatingWindowAccessor: NSViewRepresentable {
    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            configure(window: view.window)
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        DispatchQueue.main.async {
            configure(window: nsView.window)
        }
    }

    private func configure(window: NSWindow?) {
        guard let window else { return }
        window.level = .floating
        window.collectionBehavior.insert(.canJoinAllSpaces)
        window.titleVisibility = .visible
    }
}
