import SwiftUI
import BoardVaultCore

struct OrganizeView: View {
    @ObservedObject var model: AppModel
    @State private var confirmation: String?
    private var categories: [(String, Int)] {
        Dictionary(grouping: model.moves, by: \.category).map { ($0.key, $0.value.count) }.sorted { $0.0 < $1.0 }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: Layout.spacing) {
            Text("A place for every schematic.").font(.title2).fontWeight(.semibold)
            Text("Preview the changes, organize your files, or undo the last batch.").foregroundStyle(.secondary)
            HStack {
                Button("Scan (dry-run)") { model.start("scan") }.disabled(model.running)
                Button("Organize \(model.moves.count) files") { confirmation = "organize" }
                    .buttonStyle(.borderedProminent).disabled(model.running || model.planID == nil || model.moves.isEmpty)
                Button("Undo last batch") { confirmation = "undo" }.disabled(model.running)
                Spacer()
            }
            if model.moves.isEmpty {
                VStack(spacing: Layout.spacing) {
                    Image(systemName: "tray.2").font(.largeTitle).foregroundStyle(.secondary)
                    Text("Scan your downloads to preview their destinations.")
                }.frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView(.horizontal) {
                    HStack { ForEach(categories, id: \.0) { category, count in Text("\(category): \(count)").font(.caption) } }
                }
                Table(model.moves) {
                    TableColumn("File") { Text(URL(fileURLWithPath: $0.src).lastPathComponent) }
                    TableColumn("Category", value: \.category)
                    TableColumn("Destination", value: \.dest)
                    TableColumn("Match", value: \.confidence)
                }
            }
        }.padding(Layout.inset)
        .confirmationDialog(confirmation == "undo" ? "Undo the last organization?" : "Move the previewed files?",
            isPresented: Binding(get: { confirmation != nil }, set: { if !$0 { confirmation = nil } }), titleVisibility: .visible) {
                Button(confirmation == "undo" ? "Undo" : "Organize") {
                    if let operation = confirmation { model.start(operation) }
                    confirmation = nil
                }
                Button("Cancel", role: .cancel) { confirmation = nil }
            } message: { Text("Existing files are preserved. Changed previews must be scanned again.") }
    }
}
