import SwiftUI
import AppKit
import BoardVaultCore
import UserNotifications

struct SettingsView: View {
    @ObservedObject var model: AppModel
    @State private var logout = false
    var body: some View {
        Form {
            Section("Account") {
                TextField("Telegram API ID", text: $model.apiID)
                SecureField("Telegram API hash", text: $model.apiHash)
                HStack {
                    Button("Save to Keychain") { model.saveCredentials() }.disabled(model.apiID.isEmpty || model.apiHash.isEmpty)
                    Button("Import legacy .env…") { model.importCredentials() }
                }
                Text("Saved credentials are read only when you log in, download, or log out. Close the Qt app and CLI before using the shared session.")
                    .font(.caption).foregroundStyle(.secondary)
                HStack {
                    Button("Log in") { model.start("login") }
                    Button("Log out") { logout = true }
                    Link("Get API credentials", destination: URL(string: "https://my.telegram.org")!)
                }
            }
            Section("Locations") {
                folder("Downloads", path: model.downloadFolder) { model.pickFolder(organized: false) }
                folder("Organized library", path: model.organizedFolder) { model.pickFolder(organized: true) }
            }
            Section("Appearance") {
                Picker("Theme", selection: $model.theme) {
                    Text("System").tag("system")
                    Text("Dark").tag("dark")
                    Text("Light").tag("light")
                }.pickerStyle(.segmented)
            }
            Section("Behavior") {
                Toggle("Apple files by default", isOn: $model.appleOnly)
                Toggle("Resume downloads", isOn: $model.resume)
                Toggle("Open download folder on completion", isOn: $model.revealOnComplete)
                Toggle("Notify when downloads finish", isOn: $model.notifications)
                    .onChange(of: model.notifications) { enabled in if enabled { model.requestNotifications() } }
            }
            Section("About & Help") {
                Text("BoardVault · Native preview").font(.headline)
                Text("SwiftUI interface · Python / Telethon engine · MIT License")
                Link("User guide", destination: URL(string: "https://github.com/subkoks/apple-all-schematic/blob/main/docs/USER_GUIDE.md")!)
                Link("Report an issue", destination: URL(string: "https://github.com/subkoks/apple-all-schematic/issues")!)
            }
        }
        .formStyle(.grouped)
        .disabled(model.running)
        .confirmationDialog("Log out of the shared Telegram session?", isPresented: $logout, titleVisibility: .visible) {
            Button("Log out", role: .destructive) { model.start("logout") }
            Button("Cancel", role: .cancel) {}
        } message: { Text("You will need to sign in again. Your API credentials remain in Keychain.") }
        .onDisappear { model.savePreferences() }
    }
    private func folder(_ title: String, path: String, choose: @escaping () -> Void) -> some View {
        VStack(alignment: .leading, spacing: Layout.compact) {
            Text(title).font(.headline)
            Text(path).font(.caption).textSelection(.enabled)
            HStack {
                Button("Choose…", action: choose)
                Button("Open") { NSWorkspace.shared.open(URL(fileURLWithPath: path)) }
            }
        }
    }
}

extension AppModel {
    func saveCredentials() {
        do {
            try KeychainCredentials().save(Credentials(apiID: apiID, apiHash: apiHash))
            apiID = ""; apiHash = ""
            status = "API credentials saved to Keychain"
        } catch { self.error = "Could not save credentials. Check the API ID/hash and Keychain access." }
    }
    func importCredentials() {
        let panel = NSOpenPanel()
        panel.title = "Choose your legacy Telegram .env file"
        panel.showsHiddenFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let size = try url.resourceValues(forKeys: [.fileSizeKey]).fileSize ?? 0
            guard size <= 65_536 else { throw CredentialError.invalid }
            let credentials = try Credentials.legacy(contents: String(contentsOf: url, encoding: .utf8))
            try KeychainCredentials().save(credentials)
            status = "Legacy credentials imported into Keychain"
        } catch { self.error = "Could not import credentials from the selected file." }
    }
    func pickFolder(organized: Bool) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = true
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        if organized { organizedFolder = url.path } else { downloadFolder = url.path }
        planID = nil; moves = []
        savePreferences()
    }
    func savePreferences() {
        let preferences: [String: Any] = ["downloadFolder": downloadFolder, "organizedFolder": organizedFolder,
            "theme": theme, "appleOnly": appleOnly, "resume": resume, "limit": limit,
            "reveal": revealOnComplete, "notifications": notifications]
        UserDefaults.standard.set(preferences, forKey: "native.preferences")
        saveChannels()
    }
    func loadPreferences() {
        guard ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"] == nil,
              let prefs = UserDefaults.standard.dictionary(forKey: "native.preferences") else { return }
        downloadFolder = prefs["downloadFolder"] as? String ?? downloadFolder
        organizedFolder = prefs["organizedFolder"] as? String ?? organizedFolder
        theme = prefs["theme"] as? String ?? "system"
        appleOnly = prefs["appleOnly"] as? Bool ?? true
        resume = prefs["resume"] as? Bool ?? true
        limit = prefs["limit"] as? Int ?? 0
        revealOnComplete = prefs["reveal"] as? Bool ?? false
        notifications = prefs["notifications"] as? Bool ?? false
    }
    func requestNotifications() {
        guard Bundle.main.bundleIdentifier != nil else { return }
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }
    func notifyCompletion() {
        guard notifications, Bundle.main.bundleIdentifier != nil else { return }
        let content = UNMutableNotificationContent()
        content.title = "BoardVault downloads complete"
        content.body = "\(totalFiles) files downloaded."
        let request = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request) { _ in }
    }
}
