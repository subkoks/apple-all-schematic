import SwiftUI

struct DownloadView: View {
    @ObservedObject var model: AppModel
    @State private var addingChannel = false
    @State private var showLog = false
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
            HSplitView {
                VStack(alignment: .leading, spacing: Layout.compact) {
                    HStack {
                        Text("CHANNELS").font(.caption).foregroundStyle(.secondary)
                        Spacer()
                        Button { addingChannel = true } label: { Image(systemName: "plus") }
                            .help("Add channel").accessibilityLabel("Add channel")
                    }
                    List {
                        ForEach(Array(Set(model.channels.map(\.category))).sorted(), id: \.self) { category in
                            Section(category.capitalized) {
                                ForEach($model.channels) { $channel in
                                    if channel.category == category {
                                        Toggle(channel.name, isOn: $channel.selected)
                                            .toggleStyle(.checkbox)
                                            .help(channel.note ?? "Public Telegram channel")
                                            .contextMenu { Button("Remove channel", role: .destructive) { model.removeChannel(channel.name) } }
                                    }
                                }
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
                    TextField("Search, e.g. MacBook Pro M5", text: $model.keywords)
                    Text("All words must match. M5 won’t match M50.")
                        .font(.caption).foregroundStyle(.secondary)
                    HStack {
                        Text("Message limit")
                        TextField("0 = all", value: $model.limit, format: .number).frame(maxWidth: Layout.logHeight)
                    }
                    Text("0 scans all messages in each channel.").font(.caption).foregroundStyle(.secondary)
                    Toggle("Resume previous downloads", isOn: $model.resume)
                }
                .padding(.trailing, Layout.spacing)
                .frame(minWidth: Layout.sheetWidth, maxWidth: Layout.sheetWidth)
                .disabled(model.running)
                ScrollView {
                    VStack(alignment: .leading, spacing: Layout.compact) {
                        HStack {
                            Text("\(model.totalFiles) files").font(.headline)
                            Spacer()
                            Text(model.rateText).monospacedDigit()
                        }
                        Text(model.etaText).font(.caption).foregroundStyle(.secondary)
                        if model.transfers.isEmpty {
                            VStack(spacing: Layout.spacing) {
                                Image(systemName: "arrow.down.document").font(.largeTitle).foregroundStyle(.secondary)
                                Text("Ready when you are").font(.headline)
                                Text("Choose your channels and start a download.").foregroundStyle(.secondary)
                            }.frame(maxWidth: .infinity).padding(.vertical, Layout.inset)
                        }
                        ForEach(model.transfers) { transfer in
                            TransferRow(transfer: transfer)
                        }
                    }.padding(.leading, Layout.spacing)
                }
            }
            DisclosureGroup("Activity log", isExpanded: $showLog) {
                ScrollView {
                    Text(model.logs.joined(separator: "\n")).font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }.frame(height: Layout.logHeight)
            }
        }.padding(Layout.inset)
        .sheet(isPresented: $addingChannel) { AddChannelSheet(model: model) }
    }
}

private struct TransferRow: View {
    let transfer: Transfer

    var body: some View {
        VStack(alignment: .leading, spacing: Layout.transferRowSpacing) {
            HStack(spacing: Layout.compact) {
                HStack(spacing: Layout.transferIconSpacing) {
                    Image(systemName: transfer.finished ? "checkmark.circle.fill" : "circle.dotted")
                        .foregroundStyle(transfer.finished ? Color.green : Color.secondary)
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
                Text("\(transfer.downloaded) new · \(transfer.skipped) skipped · \(transfer.errors) errors")
                    .foregroundStyle(transfer.errors > 0 ? Color.red : Color.secondary)
                    .monospacedDigit()
                    .fixedSize()
            }
            .font(.caption)
            ProgressView(value: transfer.fraction)
                .controlSize(.mini)
                .accessibilityLabel("Download progress for \(transfer.channel)")
        }
        .padding(.vertical, Layout.transferRowSpacing)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("\(transfer.channel): \(transfer.filename), \(transfer.downloaded) downloaded, \(transfer.skipped) skipped, \(transfer.errors) errors")
        Divider()
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
