import AppKit
import Foundation

extension AppModel {
    /// Explicit fixture-only acceptance mode. Never reads Keychain or Telegram sessions.
    func runSmokeCheck() async {
        guard ProcessInfo.processInfo.arguments.contains("--ui-smoke"),
              ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"] != nil else { return }
        let report = dataRoot.appendingPathComponent("ui-smoke.json")
        var checks: [String: Bool] = [:]
        do {
            try FileManager.default.createDirectory(at: dataRoot, withIntermediateDirectories: true)
            // Show the full catalogue in fixture captures so row density can be reviewed.
            struct Catalogue: Decodable { let channels: [String: [String]] }
            if let url = Bundle.main.resourceURL?.appendingPathComponent("config.json"),
               let data = try? Data(contentsOf: url),
               let catalogue = try? JSONDecoder().decode(Catalogue.self, from: data) {
                channels = catalogue.channels.keys.sorted().flatMap { category in
                    (catalogue.channels[category] ?? []).map { Channel(name: $0, category: category) }
                }
                transfers = channels.map { Transfer(channel: $0.name) }
                checks["compact_rows"] = !transfers.isEmpty && transfers.count == catalogue.channels.values.reduce(0) { $0 + $1.count }
            } else {
                checks["compact_rows"] = false
            }
            section = "Download"
            if let window = NSApp.windows.first(where: { $0.isVisible }) {
                window.setContentSize(NSSize(width: Layout.minWidth, height: Layout.minHeight))
                checks["capture-Download-minimum"] = await captureSafely(name: "Download-minimum")
                window.setContentSize(NSSize(width: Layout.windowWidth, height: Layout.windowHeight))
            }
            for appearance in ["light", "dark"] {
                theme = appearance
                for page in ["Download", "Settings"] {
                    section = page
                    checks["capture-\(page)-\(appearance)"] = await captureSafely(name: "\(page)-\(appearance)")
                }
            }
            transfers = []
            channels = [Channel(name: "fixturechannel", category: "apple")]
            section = "Organize"
            start("scan")
            await task?.value
            checks["scan"] = error == nil && !moves.isEmpty
            checks["capture-Organize"] = await captureSafely(name: "Organize-preview")
            start("organize")
            await task?.value
            checks["organize"] = error == nil && status == "Completed"
            section = "Library"
            checks["capture-Library"] = await captureSafely(name: "Library")
            section = "Organize"
            start("undo")
            await task?.value
            checks["undo"] = error == nil && status == "Completed"
            checks["window"] = NSApp.windows.contains { $0.isVisible }
            try JSONSerialization.data(withJSONObject: checks, options: [.sortedKeys]).write(to: report)
        } catch {
            checks["smoke_error"] = false
            try? JSONSerialization.data(withJSONObject: checks, options: [.sortedKeys]).write(to: report)
        }
        NSApp.terminate(nil)
    }

    private func captureSafely(name: String) async -> Bool {
        do { try await capture(name: name); return true } catch { return false }
    }

    private func capture(name: String) async throws {
        let renderDelay: UInt64 = 750_000_000
        try await Task.sleep(nanoseconds: renderDelay)
        guard let window = NSApp.windows.first(where: { $0.isVisible && $0.contentView != nil }) else {
            throw CocoaError(.fileWriteUnknown)
        }
        let destination = dataRoot.appendingPathComponent(name + ".png")
        let capture = Process()
        capture.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        capture.arguments = ["-x", "-o", "-l", String(window.windowNumber), destination.path]
        try capture.run()
        let capturePoll: UInt64 = 50_000_000
        let captureDeadline = Date().addingTimeInterval(5)
        while capture.isRunning && Date() < captureDeadline { try await Task.sleep(nanoseconds: capturePoll) }
        if capture.isRunning { capture.terminate(); throw CocoaError(.fileWriteUnknown) }
        guard capture.terminationStatus == 0 else { throw CocoaError(.fileWriteUnknown) }
    }
}
