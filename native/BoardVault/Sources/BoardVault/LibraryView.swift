import SwiftUI
import AppKit
import Quartz
import BoardVaultCore

@MainActor
final class PreviewController: NSObject, @preconcurrency QLPreviewPanelDataSource {
    static let shared = PreviewController()
    private var url: URL?
    func show(_ url: URL) {
        self.url = url
        guard let panel = QLPreviewPanel.shared() else { return }
        panel.dataSource = self
        panel.reloadData()
        panel.makeKeyAndOrderFront(nil)
    }
    func numberOfPreviewItems(in panel: QLPreviewPanel!) -> Int { url == nil ? 0 : 1 }
    func previewPanel(_ panel: QLPreviewPanel!, previewItemAt index: Int) -> QLPreviewItem! { url as NSURL? }
}

struct LibraryView: View {
    @ObservedObject var model: AppModel
    @State private var nodes: [LibraryNode] = []
    @State private var search = ""
    @State private var loading = false
    @State private var selection: String?
    @State private var revision = 0
    private var selectedURL: URL? { selection.map { URL(fileURLWithPath: $0) } }
    var body: some View {
        VStack(alignment: .leading, spacing: Layout.spacing) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Your reference shelf.").font(.title2).fontWeight(.semibold)
                    Text("Browse by product or brand. Preview without leaving BoardVault.").foregroundStyle(.secondary)
                }
                Spacer()
                Button("Refresh") { revision += 1 }.disabled(loading)
            }
            TextField("Search filenames", text: $search)
            if loading { ProgressView("Reading library…") }
            // Keep the list mounted so a search refresh preserves its keyboard focus.
            ZStack {
                List(selection: $selection) {
                    OutlineGroup(nodes, children: \.children) { node in
                        Label(node.name, systemImage: node.isDirectory ? "folder" : "doc")
                            .tag(node.id)
                            .contextMenu {
                                Button("Quick Look") { PreviewController.shared.show(node.url) }.disabled(node.isDirectory)
                                Button("Open") { NSWorkspace.shared.open(node.url) }
                                Button("Reveal in Finder") { NSWorkspace.shared.activateFileViewerSelecting([node.url]) }
                            }
                            .onTapGesture(count: 2) { NSWorkspace.shared.open(node.url) }
                    }
                }.listStyle(.inset)
                    .background(OutlineNavigationGuard())
                if nodes.isEmpty && !loading {
                    VStack(spacing: Layout.spacing) {
                        Image(systemName: "books.vertical").font(.largeTitle).foregroundStyle(.secondary)
                        Text(search.isEmpty ? "Your library is empty" : "No matching files").font(.headline)
                        Button("Go to Organize") { model.section = "Organize" }
                    }.frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            HStack {
                Button("Quick Look") { if let selectedURL { PreviewController.shared.show(selectedURL) } }
                    .keyboardShortcut(.space, modifiers: []).disabled(selectedURL == nil)
                Button("Open") { if let selectedURL { NSWorkspace.shared.open(selectedURL) } }.disabled(selectedURL == nil)
                Button("Reveal in Finder") { if let selectedURL { NSWorkspace.shared.activateFileViewerSelecting([selectedURL]) } }.disabled(selectedURL == nil)
                Spacer()
            }
        }.padding(Layout.inset)
        .task(id: "\(model.organizedFolder)|\(search)|\(revision)") { await refresh() }
    }
    private func refresh() async {
        loading = true
        defer { loading = false }
        let root = URL(fileURLWithPath: model.organizedFolder), query = search
        let work = Task.detached { try LibraryIndex.scan(root: root, search: query) }
        do {
            let result = try await withTaskCancellationHandler { try await work.value } onCancel: { work.cancel() }
            try Task.checkCancellation()
            nodes = result
            selection = nil
        } catch is CancellationError {} catch { model.error = "Could not read the library folder." }
    }
}

// Preserve a Down key received while AppKit is still expanding the selected row.
private struct OutlineNavigationGuard: NSViewRepresentable {
    func makeNSView(context: Context) -> NavigationGuardView { NavigationGuardView() }
    func updateNSView(_ view: NavigationGuardView, context: Context) {}
    static func dismantleNSView(_ view: NavigationGuardView, coordinator: ()) { view.stop() }
}

private final class NavigationGuardView: NSView {
    private final class Expansion {
        let id = UUID()
        weak var outline: NSOutlineView?
        let item: AnyObject
        var events: [NSEvent] = []
        var heldKeys: Set<UInt16> = []
        var timeout: DispatchWorkItem?

        init(outline: NSOutlineView, item: AnyObject) {
            self.outline = outline
            self.item = item
        }
    }

    private var monitor: Any?
    private var observers: [NSObjectProtocol] = []
    private var expansion: Expansion?
    private var focusObservation: NSKeyValueObservation?

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        stop()
        guard window != nil else { return }
        monitor = NSEvent.addLocalMonitorForEvents(matching: [.keyDown, .keyUp, .leftMouseDown, .rightMouseDown]) { [weak self] event in
            var result: NSEvent? = event
            MainActor.assumeIsolated {
                if let self { result = self.handle(event) }
            }
            return result
        }
        focusObservation = window?.observe(\.firstResponder, options: [.new]) { [weak self] _, _ in
            MainActor.assumeIsolated {
                guard let self, let pending = self.expansion else { return }
                if !self.isCurrent(pending) { self.cancel() }
            }
        }
        let center = NotificationCenter.default
        observers.append(center.addObserver(
            forName: NSWindow.didResignKeyNotification, object: window, queue: .main
        ) { [weak self] _ in MainActor.assumeIsolated { self?.cancel() } })
        observers.append(center.addObserver(
            forName: NSOutlineView.selectionDidChangeNotification, object: nil, queue: .main
        ) { [weak self] notification in
            MainActor.assumeIsolated {
                guard let self, let pending = self.expansion,
                      notification.object as? NSOutlineView === pending.outline else { return }
                if !self.isCurrent(pending) { self.cancel() }
            }
        })
        observers.append(center.addObserver(
            forName: NSOutlineView.itemDidExpandNotification, object: nil, queue: .main
        ) { [weak self] notification in
            MainActor.assumeIsolated {
                guard let self, let pending = self.expansion,
                      let outline = notification.object as? NSOutlineView,
                      outline === pending.outline,
                      outline.isItemExpanded(pending.item) else { return }
                let id = pending.id
                DispatchQueue.main.async { [weak self] in self?.finish(id: id) }
            }
        })
    }

    func stop() {
        if let monitor { NSEvent.removeMonitor(monitor) }
        monitor = nil
        focusObservation = nil
        for observer in observers { NotificationCenter.default.removeObserver(observer) }
        observers = []
        cancel()
    }

    private func cancel() {
        expansion?.timeout?.cancel()
        expansion = nil
    }

    private func libraryOutline() -> NSOutlineView? {
        func find(in view: NSView) -> NSOutlineView? {
            if let outline = view as? NSOutlineView { return outline }
            return view.subviews.lazy.compactMap { find(in: $0) }.first
        }
        var ancestor = superview
        while let view = ancestor {
            if let outline = find(in: view) { return outline }
            ancestor = view.superview
        }
        return nil
    }

    private func isCurrent(_ pending: Expansion) -> Bool {
        guard let outline = pending.outline, window?.firstResponder === outline,
              outline.selectedRow >= 0 else { return false }
        return (outline.item(atRow: outline.selectedRow) as AnyObject?) === pending.item
    }

    private func enqueue(_ event: NSEvent, in pending: Expansion) {
        pending.events.append(event)
        if event.type == .keyDown { pending.heldKeys.insert(event.keyCode) }
        if event.type == .keyUp { pending.heldKeys.remove(event.keyCode) }
        guard pending.timeout == nil else { return }
        let id = pending.id
        let timeout = DispatchWorkItem { [weak self] in
            // Missing expansion must never flush keys into a collapsed outline.
            guard self?.expansion?.id == id else { return }
            self?.cancel()
        }
        pending.timeout = timeout
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2, execute: timeout)
    }

    private func handle(_ event: NSEvent) -> NSEvent? {
        guard event.window === window,
              let target = window?.firstResponder as? NSOutlineView,
              target === libraryOutline() else {
            cancel()
            return event
        }
        if let pending = expansion, !isCurrent(pending) { cancel() }
        // Pair a buffered keyUp even if modifiers changed after its keyDown.
        if let pending = expansion, event.type == .keyUp,
           pending.heldKeys.contains(event.keyCode) {
            enqueue(event, in: pending)
            return nil
        }
        guard event.type == .keyDown || event.type == .keyUp,
              event.modifierFlags.intersection([.command, .control, .option, .shift]).isEmpty else {
            cancel()
            return event
        }
        guard (123...126).contains(event.keyCode) else {
            if event.type == .keyDown { cancel() }
            return event
        }
        if let pending = expansion, !pending.events.isEmpty {
            if event.type == .keyDown {
                enqueue(event, in: pending)
                return nil
            }
            return event
        }
        if event.type == .keyDown && event.keyCode == 124,
           target.selectedRow >= 0, let item = target.item(atRow: target.selectedRow),
           target.isExpandable(item), !target.isItemExpanded(item) {
            if expansion == nil { expansion = Expansion(outline: target, item: item as AnyObject) }
            return event
        }
        if let pending = expansion, event.type == .keyDown, event.keyCode == 125,
           !target.isItemExpanded(pending.item) {
            enqueue(event, in: pending)
            return nil
        }
        if event.type == .keyDown { cancel() }
        return event
    }

    private func finish(id: UUID) {
        guard let pending = expansion, pending.id == id else { return }
        guard isCurrent(pending), let outline = pending.outline,
              outline.isItemExpanded(pending.item) else {
            cancel()
            return
        }
        let events = pending.events
        cancel()
        for event in events {
            guard window?.firstResponder === outline else { break }
            // Re-enter the guard so a queued Right/Down can begin a new expansion.
            NSApp.sendEvent(event)
        }
    }
}
