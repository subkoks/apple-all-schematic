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
            if nodes.isEmpty && !loading {
                VStack(spacing: Layout.spacing) {
                    Image(systemName: "books.vertical").font(.largeTitle).foregroundStyle(.secondary)
                    Text(search.isEmpty ? "Your library is empty" : "No matching files").font(.headline)
                    Button("Go to Organize") { model.section = "Organize" }
                }.frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
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
