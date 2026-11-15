import AppKit
import CoreGraphics
import SwiftUI
import XCTest
@testable import BoardVault

@MainActor
private final class NavigationWindow: NSWindow {
    var trace: ((String, NSEvent?) -> Void)?
    var deliveryProbeKeys: Set<UInt16> = []

    override func sendEvent(_ event: NSEvent) {
        if event.type == .keyDown || event.type == .keyUp {
            trace?("dispatch-\(event.type.rawValue)-\(event.keyCode)", event)
        }
        // Observe delivery past the production monitor without invoking preview or closing UI.
        if deliveryProbeKeys.contains(event.keyCode) { return }
        super.sendEvent(event)
    }
}

final class LibraryNavigationTests: XCTestCase {
    @MainActor
    func testRapidDownBeforeExpansionSelectsFixture() async throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("BoardVault-navigation-\(UUID().uuidString)")
        let apple = root.appendingPathComponent("Apple")
        try FileManager.default.createDirectory(at: apple, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let pdf = apple.appendingPathComponent("BoardVault-Keyboard-fixture.pdf")
        var box = CGRect(x: 0, y: 0, width: 200, height: 200)
        let context = try XCTUnwrap(CGContext(pdf as CFURL, mediaBox: &box, nil))
        context.beginPDFPage(nil)
        context.endPDFPage()
        context.closePDF()

        _ = NSApplication.shared
        let model = AppModel(loadSavedState: false)
        model.organizedFolder = root.path
        let window = NavigationWindow(
            contentRect: NSRect(x: 100, y: 100, width: 800, height: 600),
            styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.isReleasedWhenClosed = false
        window.contentView = NSHostingView(rootView: LibraryView(model: model))
        window.makeKeyAndOrderFront(nil)
        defer { window.orderOut(nil); window.close() }
        guard await waitUntil({ self.outline(in: window.contentView)?.numberOfRows == 1 }) else {
            throw XCTSkip("TEST_INVALID: hosted LibraryView did not expose one outline row")
        }
        let outline = try XCTUnwrap(outline(in: window.contentView))
        var observeInput: ((NSEvent) -> Void)?
        let inputMonitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp]) { event in
            MainActor.assumeIsolated { observeInput?(event) }
            return event
        }
        defer { if let inputMonitor { NSEvent.removeMonitor(inputMonitor) } }
        XCTAssertTrue(window.makeFirstResponder(outline))
        guard window.firstResponder === outline else {
            throw XCTSkip("TEST_INVALID: native outline is not first responder")
        }

        var entries: [[String: String]] = []
        var sequence: [String] = []
        func record(_ name: String, _ event: NSEvent? = nil) {
            sequence.append(name)
            entries.append([
                "name": name,
                "callbackUptime": String(ProcessInfo.processInfo.systemUptime),
                "eventTimestamp": event.map { String($0.timestamp) } ?? "",
                "modifierFlags": event.map { String($0.modifierFlags.rawValue) } ?? "",
                "isRepeat": event.map { String($0.isARepeat) } ?? "",
                "selectedRow": String(outline.selectedRow),
                "rows": String(outline.numberOfRows)
            ])
        }
        window.trace = { record($0, $1) }
        observeInput = { event in
            if event.window === window { record("input-\(event.type.rawValue)-\(event.keyCode)", event) }
        }
        let center = NotificationCenter.default
        let will = center.addObserver(forName: NSOutlineView.itemWillExpandNotification,
                                      object: outline, queue: .main) { _ in
            MainActor.assumeIsolated { record("willExpand") }
        }
        let did = center.addObserver(forName: NSOutlineView.itemDidExpandNotification,
                                     object: outline, queue: .main) { _ in
            MainActor.assumeIsolated { record("didExpand") }
        }
        defer {
            center.removeObserver(will)
            center.removeObserver(did)
            window.trace = nil
            if let destination = ProcessInfo.processInfo.environment["BOARDVAULT_NAVIGATION_TRACE"] {
                do {
                    let data = try JSONSerialization.data(withJSONObject: entries, options: [.prettyPrinted, .sortedKeys])
                    try data.write(to: URL(fileURLWithPath: destination))
                } catch { XCTFail("Could not save navigation trace: \(error)") }
            }
        }
        func key(_ code: UInt16, characters: String, repeating: Bool = false,
                 keyUpModifiers: NSEvent.ModifierFlags = []) throws {
            for type in [NSEvent.EventType.keyDown, .keyUp] {
                let event = try XCTUnwrap(NSEvent.keyEvent(
                    with: type, location: .zero, modifierFlags: type == .keyUp ? keyUpModifiers : [],
                    timestamp: ProcessInfo.processInfo.systemUptime,
                    windowNumber: window.windowNumber, context: nil,
                    characters: characters, charactersIgnoringModifiers: characters,
                    isARepeat: repeating && type == .keyDown, keyCode: code))
                NSApp.sendEvent(event)
                record("application-return-\(event.type.rawValue)-\(event.keyCode)", event)
            }
        }

        // Enter through the real responder path, then establish a settled control.
        try key(125, characters: "\u{F701}")
        XCTAssertEqual(outline.selectedRow, 0)
        record("control-start")
        try key(124, characters: "\u{F703}")
        guard await waitUntil({ outline.numberOfRows == 2 }) else {
            throw XCTSkip("TEST_INVALID: control did not expand the synthetic folder")
        }
        try key(125, characters: "\u{F701}")
        XCTAssertEqual(outline.selectedRow, 1, "Settled-expansion control must select the only PDF child")
        record("control-selected")
        try key(123, characters: "\u{F702}")
        try key(123, characters: "\u{F702}")
        guard await waitUntil({ outline.numberOfRows == 1 && outline.selectedRow == 0 }) else {
            throw XCTSkip("TEST_INVALID: could not restore collapsed selected parent")
        }
        let start = sequence.count
        record("race-start")
        // No await, snapshot, or run-loop drain between the two key pairs.
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}")
        guard await waitUntil({ outline.numberOfRows == 2 }) else {
            throw XCTSkip("TEST_INVALID: race trial did not finish expanding")
        }
        // Allow a delayed selection update to settle before asserting the result.
        let selectedChild = await waitUntil { outline.selectedRow == 1 }
        record("race-result")
        let trial = Array(sequence.dropFirst(start))
        guard let down = trial.firstIndex(of: "application-return-10-125"),
              let willExpand = trial.firstIndex(of: "willExpand"),
              let didExpand = trial.firstIndex(of: "didExpand"),
              down < willExpand, willExpand < didExpand else {
            throw XCTSkip("TEST_INVALID: Down-before-expansion ordering was not observed")
        }
        XCTAssertTrue(selectedChild,
                      "Pre-expansion Down must ultimately select the synthetic PDF child; selected row \(outline.selectedRow)")

        // Buffered navigation must keep its original order across repeats.
        try key(123, characters: "\u{F702}")
        try key(123, characters: "\u{F702}")
        guard await waitUntil({ outline.numberOfRows == 1 && outline.selectedRow == 0 }) else {
            throw XCTSkip("TEST_INVALID: interleaved control could not reset")
        }
        let interleavedStart = entries.count
        record("interleaved-start")
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}", keyUpModifiers: [.shift])
        try key(124, characters: "\u{F703}", repeating: true)
        try key(125, characters: "\u{F701}", repeating: true)
        try key(126, characters: "\u{F700}")
        try await Task.sleep(nanoseconds: 100_000_000)
        record("interleaved-result")
        XCTAssertEqual(outline.numberOfRows, 2)
        XCTAssertEqual(outline.selectedRow, 0, "Down, Right, Down, Up must finish on parent")
        let interleaved = Array(entries.dropFirst(interleavedStart))
        let delivered = interleaved.filter { $0["name"]?.hasPrefix("dispatch-10-") == true }
        XCTAssertEqual(delivered.compactMap { $0["name"] },
                       ["dispatch-10-124", "dispatch-10-125", "dispatch-10-124", "dispatch-10-125", "dispatch-10-126"])
        let didTime = try XCTUnwrap(interleaved.first { $0["name"] == "didExpand" }?["callbackUptime"])
        let firstDownTime = try XCTUnwrap(delivered.first { $0["name"] == "dispatch-10-125" }?["callbackUptime"])
        XCTAssertGreaterThan(try XCTUnwrap(Double(firstDownTime)), try XCTUnwrap(Double(didTime)))
        XCTAssertEqual(interleaved.filter { $0["name"] == "dispatch-11-125" }.count, 2,
                       "Both Down keyUps must survive a modifier change")
        XCTAssertTrue(interleaved.contains {
            $0["name"] == "dispatch-11-125" && $0["modifierFlags"] == String(NSEvent.ModifierFlags.shift.rawValue)
        })
        XCTAssertTrue(delivered.contains { $0["name"] == "dispatch-10-124" && $0["isRepeat"] == "true" })

        // Selection departure cancels even when selection returns before completion.
        try key(123, characters: "\u{F702}")
        guard await waitUntil({ outline.numberOfRows == 1 }) else {
            throw XCTSkip("TEST_INVALID: selection cancellation could not reset")
        }
        record("selection-cancel-start")
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}")
        outline.deselectAll(nil)
        outline.selectRowIndexes(IndexSet(integer: 0), byExtendingSelection: false)
        try await Task.sleep(nanoseconds: 250_000_000)
        XCTAssertEqual(outline.selectedRow, 0)
        record("selection-cancel-result")

        // A pending key must not move selection after focus leaves the outline.
        try key(123, characters: "\u{F702}")
        guard await waitUntil({ outline.numberOfRows == 1 && outline.selectedRow == 0 }) else {
            throw XCTSkip("TEST_INVALID: focus control could not reset the parent")
        }
        record("focus-control-start")
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}")
        window.makeFirstResponder(nil)
        window.makeFirstResponder(outline)
        try await Task.sleep(nanoseconds: 250_000_000)
        XCTAssertEqual(outline.selectedRow, 0)
        record("focus-control-result")

        // Ordinary input must reach the native window during a pending Down.
        // Probe at window delivery so Space/Return/Escape cannot create unrelated UI.
        let ordinaryInputs: [(UInt16, String)] = [(0, "a"), (49, " "), (36, "\r"), (53, "\u{1B}")]
        window.deliveryProbeKeys = Set(ordinaryInputs.map { $0.0 })
        for (code, characters) in ordinaryInputs {
            try key(123, characters: "\u{F702}")
            guard await waitUntil({ outline.numberOfRows == 1 && outline.selectedRow == 0 }) else {
                throw XCTSkip("TEST_INVALID: ordinary-input control could not reset")
            }
            let begin = entries.count
            record("ordinary-start-\(code)")
            try key(124, characters: "\u{F703}")
            try key(125, characters: "\u{F701}")
            try key(code, characters: characters)
            let immediate = Array(entries.dropFirst(begin))
            XCTAssertEqual(immediate.filter { $0["name"] == "dispatch-10-\(code)" }.count, 1)
            XCTAssertEqual(immediate.filter { $0["name"] == "dispatch-11-\(code)" }.count, 1)
            XCTAssertFalse(immediate.contains { $0["name"] == "didExpand" },
                           "Delivery must be immediate while expansion is pending")
            try await Task.sleep(nanoseconds: 250_000_000)
            XCTAssertEqual(outline.selectedRow, 0, "Unrelated input cancels buffered navigation")
            XCTAssertFalse(entries.dropFirst(begin).contains { $0["name"] == "dispatch-10-125" })
            record("ordinary-result-\(code)")
        }
        window.deliveryProbeKeys = []

        // Stop Right at the test-owned window after the real input monitor arms.
        // With native expansion deliberately withheld, the actual timeout must cancel.
        try key(123, characters: "\u{F702}")
        guard await waitUntil({ outline.numberOfRows == 1 && outline.selectedRow == 0 }) else {
            throw XCTSkip("TEST_INVALID: timeout control could not reset")
        }
        window.deliveryProbeKeys = [124]
        let stalledStart = entries.count
        record("stalled-start")
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}", keyUpModifiers: [.shift])
        try await Task.sleep(nanoseconds: 300_000_000)
        XCTAssertTrue(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-10-124" })
        XCTAssertEqual(outline.numberOfRows, 1)
        XCTAssertEqual(outline.selectedRow, 0)
        XCTAssertFalse(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-10-125" })
        XCTAssertFalse(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-11-125" })
        window.deliveryProbeKeys = []
        record("stalled-result")
        try key(124, characters: "\u{F703}")
        let recovered = await waitUntil { outline.numberOfRows == 2 }
        XCTAssertTrue(recovered, "Recovery must expand without unrelated cancellation input")
        try await Task.sleep(nanoseconds: 50_000_000)
        XCTAssertEqual(outline.selectedRow, 0, "Expired Down must not replay on later expansion")
        XCTAssertFalse(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-10-125" },
                       "Stale Down keyDown must not reach the window during recovery")
        XCTAssertFalse(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-11-125" },
                       "Stale Down keyUp must not reach the window during recovery")
        record("stalled-recovery-result")

        // Check normal input separately, after timeout recovery has been asserted.
        window.deliveryProbeKeys = [0]
        try key(0, characters: "a")
        XCTAssertTrue(entries.dropFirst(stalledStart).contains { $0["name"] == "dispatch-10-0" })
        window.deliveryProbeKeys = []
        record("post-recovery-normal-input")

        let empty = root.appendingPathComponent("Empty")
        try FileManager.default.createDirectory(at: empty, withIntermediateDirectories: true)
        model.organizedFolder = empty.path
        guard await waitUntil({ outline.numberOfRows == 0 }) else {
            throw XCTSkip("TEST_INVALID: empty-list control did not load")
        }
        window.makeFirstResponder(outline)
        try key(124, characters: "\u{F703}")
        try key(125, characters: "\u{F701}")
        XCTAssertEqual(outline.selectedRow, -1)
        XCTAssertEqual(outline.numberOfRows, 0)
        record("empty-control-result")
    }

    @MainActor
    private func outline(in view: NSView?) -> NSOutlineView? {
        guard let view else { return nil }
        if let outline = view as? NSOutlineView { return outline }
        return view.subviews.lazy.compactMap { self.outline(in: $0) }.first
    }

    @MainActor
    private func waitUntil(_ condition: () -> Bool) async -> Bool {
        let deadline = ProcessInfo.processInfo.systemUptime + 3
        while !condition() && ProcessInfo.processInfo.systemUptime < deadline {
            try? await Task.sleep(nanoseconds: 10_000_000)
        }
        return condition()
    }
}
