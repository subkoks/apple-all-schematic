import SwiftUI
import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    weak var model: AppModel?
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        model?.savePreferences()
        guard let model, model.running else { return .terminateNow }
        model.stop()
        Task { @MainActor in
            await model.task?.value
            sender.reply(toApplicationShouldTerminate: true)
        }
        return .terminateLater
    }
}

@main
struct BoardVaultApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @StateObject private var model = AppModel()
    var body: some Scene {
        Window("BoardVault", id: "main") {
            MainView(model: model)
                .onAppear { delegate.model = model }
                .task { await model.runSmokeCheck() }
                .preferredColorScheme(model.theme == "dark" ? .dark : model.theme == "light" ? .light : nil)
        }
        .defaultSize(width: Layout.windowWidth, height: Layout.windowHeight)
        .commands {
            CommandGroup(after: .newItem) {
                Button("Start Download") { model.start() }.keyboardShortcut("r").disabled(!model.canStart)
                Button("Stop") { model.stop() }.keyboardShortcut(".").disabled(!model.running)
            }
            CommandGroup(replacing: .appSettings) {
                Button("Settings…") { model.section = "Settings" }.keyboardShortcut(",")
            }
            CommandGroup(replacing: .help) {
                Link("BoardVault Help", destination: URL(string: "https://github.com/subkoks/apple-all-schematic#readme")!)
            }
        }
    }
}

struct MainView: View {
    @ObservedObject var model: AppModel
    private let sections = [("Download", "arrow.down.circle"), ("Organize", "tray.2"),
                            ("Library", "books.vertical"), ("Settings", "gearshape")]
    var body: some View {
        NavigationSplitView {
            List(selection: $model.section) {
                ForEach(sections, id: \.0) { name, icon in Label(name, systemImage: icon).tag(name) }
            }
            .navigationSplitViewColumnWidth(min: Layout.sidebar, ideal: Layout.sidebar)
            .safeAreaInset(edge: .bottom) {
                VStack(alignment: .leading) {
                    Text("BoardVault").font(.headline)
                    Text("Schematics, in order.").font(.caption).foregroundStyle(.secondary)
                }.padding()
            }
        } detail: {
            VStack(spacing: 0) {
                if let error = model.error {
                    HStack {
                        Label(error, systemImage: "exclamationmark.triangle").foregroundStyle(.red)
                        Spacer()
                        Button("Dismiss") { model.error = nil }
                    }.padding().background(.regularMaterial)
                }
                switch model.section {
                case "Settings": SettingsView(model: model)
                case "Organize": OrganizeView(model: model)
                case "Library": LibraryView(model: model)
                default: DownloadView(model: model)
                }
                HStack {
                    if model.running { ProgressView().controlSize(.small) }
                    Text(model.status).foregroundStyle(.secondary)
                    Spacer()
                }.padding(Layout.compact).background(.bar)
            }
            .navigationTitle(model.section ?? "Download")
        }
        .frame(minWidth: Layout.minWidth, minHeight: Layout.minHeight)
        .sheet(isPresented: Binding(get: { model.loginField != nil }, set: { if !$0 { model.stop() } })) {
            LoginSheet(model: model)
        }
    }
}

