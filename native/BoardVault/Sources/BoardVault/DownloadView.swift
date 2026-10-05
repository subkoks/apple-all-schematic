import SwiftUI

struct DownloadView: View {
    @ObservedObject var model: AppModel
    @State private var addingChannel = false
    var body: some View {
        VStack(alignment: .leading, spacing: Layout.spacing) {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading) {
                    Text("Your next reference, ready.").font(.title2).fontWeight(.semibold)
                    Text("Download schematics and boardviews from your channels.").foregroundStyle(.secondary)
                }
                Spacer()
                Button("Start", systemImage: "play.fill") { model.start() }
                    .buttonStyle(.borderedProminent).disabled(!model.canStart)
                Button("Stop", systemImage: "stop.fill") { model.stop() }.disabled(!model.running)
            }
            HStack(spacing: Layout.compact) {
                Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
                TextField("Search filenames and captions, e.g. MacBook Pro M5", text: $model.keywords)
                    .textFieldStyle(.plain)
                    .accessibilityLabel("Search files")
                if !model.keywords.isEmpty {
                    Button { model.keywords = "" } label: { Image(systemName: "xmark.circle.fill") }
                        .buttonStyle(.plain).foregroundStyle(.secondary).help("Clear search")
                }
                Menu {
                    Picker("Match words", selection: $model.searchMode) {
                        Text("Any word · more results").tag("any")
                        Text("All words · narrower").tag("all")
                        Text("Exact phrase").tag("phrase")
                    }
                    Picker("Search in", selection: $model.searchScope) {
                        Text("Filename and caption").tag("both")
                        Text("Filename only").tag("filename")
                        Text("Caption only").tag("caption")
                    }
                    Divider()
                    ForEach(fileTypeOptions, id: \.0) { key, label in
                        Toggle(label, isOn: Binding(
                            get: { model.fileTypes.contains(key) },
                            set: { enabled in
                                if enabled { model.fileTypes.insert(key) }
                                else { model.fileTypes.remove(key) }
                            }
                        ))
                    }
                } label: {
                    Label("Search options", systemImage: "line.3.horizontal.decrease")
                }
                .help("Choose matching, search fields and file formats")
            }
            .padding(Layout.compact)
            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: Layout.compact))
            .disabled(model.running)
            HStack {
                Text(searchSummary).font(.caption).foregroundStyle(.secondary)
                Spacer()
                if model.fileTypes.isEmpty {
                    Text("Choose at least one file type").font(.caption).foregroundStyle(.red)
                }
            }
            HSplitView {
                VStack(alignment: .leading, spacing: Layout.compact) {
                    HStack {
                        Text("CHANNELS").font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button { addingChannel = true } label: { Image(systemName: "plus") }
                            .help("Add channel").accessibilityLabel("Add channel")
                        Button { model.refreshFollowerCounts() } label: { Image(systemName: "arrow.clockwise") }
                            .disabled(model.refreshingCounts)
                            .help("Refresh public subscriber counts")
                            .accessibilityLabel("Refresh subscriber counts")
                    }
                    List {
                        ForEach($model.channels) { $channel in
                            HStack(spacing: Layout.compact) {
                                Toggle(channel.name, isOn: $channel.selected)
                                    .toggleStyle(.checkbox).lineLimit(1)
                                    .help("@\(channel.name)\n\(channel.note ?? "Public Telegram channel")")
                                Spacer(minLength: 0)
                                if let count = model.followerCounts[channel.name] {
                                    Text(count.formatted(.number.notation(.compactName)))
                                        .font(.caption2).foregroundStyle(.secondary)
                                        .help("Approximately \(count.formatted()) public subscribers")
                                }
                                Menu {
                                    Button("Move up", systemImage: "arrow.up") { model.moveChannel(channel.name, by: -1) }
                                        .disabled(model.channels.first?.name == channel.name)
                                    Button("Move down", systemImage: "arrow.down") { model.moveChannel(channel.name, by: 1) }
                                        .disabled(model.channels.last?.name == channel.name)
                                    Divider()
                                    Button("Remove channel", role: .destructive) { model.removeChannel(channel.name) }
                                } label: {
                                    Image(systemName: "ellipsis").foregroundStyle(.secondary)
                                }
                                .menuStyle(.borderlessButton)
                                .frame(width: Layout.inset)
                                .help("Reorder or remove \(channel.name)")
                            }
                        }
                    }.listStyle(.inset)
                    HStack {
                        Button("Select all") { for i in model.channels.indices { model.channels[i].selected = true } }
                        Button("Clear") { for i in model.channels.indices { model.channels[i].selected = false } }
                    }
                    Picker("Files", selection: $model.appleOnly) {
                        Text("Apple only").tag(true)
                        Text("All files").tag(false)
                    }.pickerStyle(.segmented)
                    HStack {
                        Text("Message limit")
                        TextField("0 = all", value: $model.limit, format: .number).frame(maxWidth: Layout.limitFieldWidth)
                    }
                    Text("0 scans all messages in each channel.").font(.caption).foregroundStyle(.secondary)
                    Toggle("Resume previous downloads", isOn: $model.resume)
                }
                .padding(.trailing, Layout.spacing)
                .frame(minWidth: Layout.channelPaneWidth, maxWidth: Layout.channelPaneWidth)
                .disabled(model.running)
                ScrollView {
                    VStack(alignment: .leading, spacing: Layout.compact) {
                        HStack {
                            Text("\(model.totalFiles) files").font(.headline)
                            Spacer()
                            Text(model.rateText).monospacedDigit()
                        }
                        Text(model.etaText).font(.caption).foregroundStyle(.secondary)
                        if !model.transfers.isEmpty {
                            HStack(spacing: Layout.compact) {
                                Text("Channel").frame(width: Layout.transferNameWidth, alignment: .leading)
                                Text("Current file / status").frame(maxWidth: .infinity, alignment: .leading)
                                Text("Progress").frame(width: Layout.transferProgressWidth)
                                ForEach(["New", "Skipped", "Errors"], id: \.self) { label in
                                    Text(label).frame(width: Layout.transferCountWidth, alignment: .trailing)
                                }
                            }
                            .font(.caption2).foregroundStyle(.secondary)
                        }
                        if model.transfers.isEmpty {
                            VStack(spacing: Layout.spacing) {
                                Image(systemName: "arrow.down.document").font(.largeTitle).foregroundStyle(.secondary)
                                Text("Ready when you are").font(.headline)
                                Text("Choose your channels and start a download.").foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity).padding(.vertical, Layout.inset)
                        }
                        LazyVStack(spacing: 0) {
                            ForEach(model.transfers) { transfer in TransferRow(transfer: transfer) }
                        }
                    }.padding(.leading, Layout.spacing)
                }
            }
        }.padding(Layout.inset)
        .sheet(isPresented: $addingChannel) { AddChannelSheet(model: model) }
        .task { model.refreshFollowerCounts() }
    }

    private let fileTypeOptions = [("pdf", "PDF"), ("boardview", "Boardview"),
                                   ("archive", "Archives"), ("firmware", "Firmware")]
    private var searchSummary: String {
        let mode = ["any": "Any word", "all": "All words", "phrase": "Exact phrase"][model.searchMode] ?? "Any word"
        let scope = ["both": "filename + caption", "filename": "filename", "caption": "caption"][model.searchScope] ?? "filename + caption"
        return "\(mode) in \(scope) · whole terms · \(model.fileTypes.count) file types"
    }
}

private struct TransferRow: View {
    let transfer: Transfer

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: Layout.compact) {
                HStack(spacing: Layout.transferIconSpacing) {
                    Image(systemName: transfer.errors > 0 ? "exclamationmark.circle.fill"
                          : transfer.finished ? "checkmark.circle.fill" : "circle.dotted")
                        .foregroundStyle(transfer.errors > 0 ? Color.red
                                         : transfer.finished ? Color.green : Color.secondary)
                        .accessibilityHidden(true)
                    Text(transfer.channel).fontWeight(.medium).lineLimit(1)
                }
                .frame(width: Layout.transferNameWidth, alignment: .leading)
                .help(transfer.channel)
                Text(transfer.filename)
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .help(transfer.filename)
                ProgressView(value: transfer.fraction)
                    .controlSize(.mini)
                    .frame(width: Layout.transferProgressWidth)
                    .accessibilityLabel("Download progress for \(transfer.channel)")
                count(transfer.downloaded, "new")
                count(transfer.skipped, "skipped")
                count(transfer.errors, "errors", color: transfer.errors > 0 ? .red : .secondary)
            }
            .font(.caption)
            .padding(.vertical, Layout.transferRowSpacing)
            Divider()
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(transfer.channel): \(transfer.filename), \(transfer.downloaded) downloaded, \(transfer.skipped) skipped, \(transfer.errors) errors")
    }

    private func count(_ value: Int, _ label: String, color: Color = .secondary) -> some View {
        Text(value.formatted()).monospacedDigit()
            .foregroundStyle(color)
            .frame(width: Layout.transferCountWidth, alignment: .trailing)
            .help("\(value.formatted()) \(label)")
    }
}

struct AddChannelSheet: View {
    @ObservedObject var model: AppModel
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var category = "laptop"
    var body: some View {
        VStack(alignment: .leading, spacing: Layout.spacing) {
            Text("Add a channel").font(.title2)
            TextField("Channel username", text: $name)
            Picker("Category", selection: $category) {
                ForEach(["laptop", "mobile", "apple"], id: \.self) { Text($0.capitalized).tag($0) }
            }
            HStack {
                Button("Cancel") { dismiss() }.keyboardShortcut(.cancelAction)
                Spacer()
                Button("Add") { if model.addChannel(name, category: category) { dismiss() } }.keyboardShortcut(.defaultAction)
            }
        }.padding(Layout.inset).frame(width: Layout.sheetWidth)
    }
}

struct LoginSheet: View {
    @ObservedObject var model: AppModel
    @State private var response = ""
    private var title: String {
        switch model.loginField { case "phone": return "Phone number"; case "code": return "Telegram login code"; default: return "Two-step verification password" }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: Layout.spacing) {
            Text("Connect to Telegram").font(.title2)
            Text(title)
            SecureField(title, text: $response).onSubmit(submit)
            Text("Your response is sent directly to the Telegram engine and is never logged.").font(.caption).foregroundStyle(.secondary)
            HStack {
                Button("Cancel") { response = ""; model.stop() }.keyboardShortcut(.cancelAction)
                Spacer()
                Button("Continue", action: submit).keyboardShortcut(.defaultAction).disabled(response.isEmpty)
            }
        }.padding(Layout.inset).frame(width: Layout.sheetWidth)
        .onChange(of: model.loginField) { _ in response = "" }
    }
    private func submit() { guard !response.isEmpty else { return }; model.respond(response); response = "" }
}
