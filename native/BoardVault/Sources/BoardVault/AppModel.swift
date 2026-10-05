import SwiftUI
import AppKit
import BoardVaultCore

struct Channel: Codable, Identifiable {
    var id: String { name }
    var name: String
    var category: String
    var selected = true
    var note: String? = nil
}

struct Transfer: Identifiable {
    var id: String { channel }
    let channel: String
    var filename = "Waiting"
    var received: Int64 = 0
    var total: Int64 = 0
    var downloaded = 0
    var skipped = 0
    var errors = 0
    var finished = false
    var fraction: Double { total > 0 ? min(1, Double(received) / Double(total)) : 0 }
}

enum Layout {
    static let spacing: CGFloat = 16
    static let compact: CGFloat = 8
    static let inset: CGFloat = 24
    static let sidebar: CGFloat = 220
    static let sidebarNavigationHeight: CGFloat = 190
    static let windowWidth: CGFloat = 980
    static let windowHeight: CGFloat = 680
    static let minWidth: CGFloat = 820
    static let minHeight: CGFloat = 560
    static let sheetWidth: CGFloat = 380
    static let logHeight: CGFloat = 140
    static let maxLogEntries = 300
    static let maxMessages = 1_000_000
    static let transferNameWidth: CGFloat = 190
    static let transferProgressWidth: CGFloat = 110
    static let transferCountWidth: CGFloat = 48
    static let sidebarLogHeight: CGFloat = 220
    static let transferRowSpacing: CGFloat = 3
    static let transferIconSpacing: CGFloat = 4
}

@MainActor
final class AppModel: ObservableObject {
    private static let sourceParentLevels = 5
    @Published var section: String? = "Download"
    @Published var channels: [Channel] = []
    @Published var appleOnly = true
    @Published var resume = true
    @Published var limit = 0
    @Published var keywords = ""
    @Published var searchMode = "any"
    @Published var searchScope = "both"
    @Published var fileTypes: Set<String> = ["pdf", "boardview", "archive", "firmware"]
    @Published var followerCounts: [String: Int] = [:]
    @Published var running = false
    @Published var transfers: [Transfer] = []
    @Published var logs: [String] = []
    @Published var status = "Ready"
    @Published var error: String?
    @Published var loginField: String?
    @Published var apiID = ""
    @Published var apiHash = ""
    @Published var downloadFolder: String
    @Published var organizedFolder: String
    @Published var theme = "system"
    @Published var speed = 0.0
    @Published var moves: [OrganizeMove] = []
    @Published var planID: String?
    @Published var revealOnComplete = false
    @Published var notifications = false
    let engine = EngineClient()
    let dataRoot: URL
    let repo: URL
    var task: Task<Void, Never>?
    private var activeOperation = ""
    private var started = Date()
    private var transferred: Int64 = 0

    init(loadSavedState: Bool = true) {
        var source = URL(fileURLWithPath: #filePath)
        for _ in 0..<Self.sourceParentLevels { source.deleteLastPathComponent() }
        repo = ProcessInfo.processInfo.environment["BOARDVAULT_REPO"].map { URL(fileURLWithPath: $0) } ?? source
        dataRoot = ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"].map { URL(fileURLWithPath: $0) }
            ?? FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/subkoks/BoardVault")
        downloadFolder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Downloads/BoardVault").path
        organizedFolder = dataRoot.appendingPathComponent("organized").path
        if ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"] != nil {
            downloadFolder = dataRoot.appendingPathComponent("downloads").path
        }
        if ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"] != nil {
            channels = [Channel(name: "fixturechannel", category: "apple")]
        } else if loadSavedState {
            loadChannels()
            loadPreferences()
        }
    }

    static func mergingAdditions(_ existing: [Channel], additions: [Channel], seen: Set<String>) -> [Channel] {
        var result = existing
        var names = Set(existing.map { $0.name.lowercased() })
        for var channel in additions {
            let key = channel.name.lowercased()
            guard !seen.contains(key), names.insert(key).inserted else { continue }
            channel.selected = false
            result.append(channel)
        }
        return result
    }

    func loadChannels() {
        let defaults = UserDefaults.standard
        let saved = defaults.data(forKey: "native.channels")
            .flatMap { try? JSONDecoder().decode([Channel].self, from: $0) }
        if let saved { channels = saved }
        let configURL = Bundle.main.resourceURL?.appendingPathComponent("config.json")
        let path = configURL.flatMap { FileManager.default.fileExists(atPath: $0.path) ? $0 : nil }
            ?? repo.appendingPathComponent("args/config.json")
        struct Config: Decodable {
            let channels: [String: [String]]
            let native_channel_additions: [String]?
            let channel_notes: [String: String]?
        }
        guard let data = try? Data(contentsOf: path), let config = try? JSONDecoder().decode(Config.self, from: data) else {
            if saved == nil { error = "Could not load channel configuration. Add channels to begin." }
            return
        }
        let introduced = Set((config.native_channel_additions ?? []).map { $0.lowercased() })
        let catalog = config.channels.keys.sorted().flatMap { category in
            (config.channels[category] ?? []).map {
                Channel(name: $0, category: category, selected: !introduced.contains($0.lowercased()), note: config.channel_notes?[$0])
            }
        }
        let seen = Set((defaults.stringArray(forKey: "native.seenChannelAdditions") ?? []).map { $0.lowercased() })
        channels = saved.map { Self.mergingAdditions($0, additions: catalog.filter { introduced.contains($0.name.lowercased()) }, seen: seen) } ?? catalog
        saveChannels()
        defaults.set(Array(seen.union(introduced)).sorted(), forKey: "native.seenChannelAdditions")
    }

    func saveChannels() {
        if let data = try? JSONEncoder().encode(channels) { UserDefaults.standard.set(data, forKey: "native.channels") }
    }

    func addChannel(_ raw: String, category: String) -> Bool {
        let name = raw.trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "@", with: "")
        guard name.range(of: "^[A-Za-z][A-Za-z0-9_]{4,31}$", options: .regularExpression) != nil else {
            error = "Use a channel name of 5–32 letters, digits or underscores, beginning with a letter."
            return false
        }
        guard !channels.contains(where: { $0.name.lowercased() == name.lowercased() }) else { return false }
        channels.append(Channel(name: name, category: category))
        saveChannels()
        return true
    }

    func removeChannel(_ name: String) {
        channels.removeAll { $0.name == name }
        saveChannels()
    }

    func moveChannel(_ name: String, by offset: Int) {
        guard !running, let index = channels.firstIndex(where: { $0.name == name }),
              channels.indices.contains(index + offset) else { return }
        channels.swapAt(index, index + offset)
        saveChannels()
    }

    var canStart: Bool { !running && !fileTypes.isEmpty && channels.contains(where: \.selected) }
    var totalFiles: Int { transfers.reduce(0) { $0 + $1.downloaded } }
    var rateText: String { ByteCountFormatter.string(fromByteCount: Int64(speed), countStyle: .file) + "/s" }
    var etaText: String {
        let remaining = transfers.filter { !$0.finished }.reduce(Int64(0)) { $0 + max(0, $1.total - $1.received) }
        guard speed > 0, remaining > 0 else { return "ETA —" }
        return "Current file: \(Int(Double(remaining) / speed))s remaining"
    }

    func location() throws -> (URL, [String]) {
        if let engine = Bundle.main.resourceURL?.appendingPathComponent("engine/boardvault-engine"),
           FileManager.default.isExecutableFile(atPath: engine.path) { return (engine, []) }
        let python = repo.appendingPathComponent(".venv/bin/python")
        guard FileManager.default.isExecutableFile(atPath: python.path) else { throw EngineFailure.unavailable }
        return (python, [repo.appendingPathComponent("src/tg_schematic_downloader.py").path])
    }

    func start(_ operation: String = "download") {
        guard !running else { return }
        guard operation != "download" || canStart else { return }
        if operation == "organize", planID == nil { return }
        if operation == "scan" { moves = []; planID = nil }
        error = nil
        savePreferences()
        running = true
        status = operation.capitalized + " in progress…"
        activeOperation = operation
        started = Date()
        transferred = 0
        speed = 0
        if operation == "download" { transfers = channels.filter(\.selected).map { Transfer(channel: $0.name) } }
        task = Task {
            defer { running = false; loginField = nil; apiID = ""; apiHash = ""; updateDock(active: false) }
            do {
                let (executable, prefix) = try location()
                var arguments = prefix + ["--json", "--operation", operation, "--data-dir", dataRoot.path,
                    "--download-dir", downloadFolder, "--organized-dir", organizedFolder]
                if operation == "organize", let planID { arguments += ["--plan-id", planID] }
                if operation == "download" {
                    arguments += ["--limit", String(max(0, min(limit, Layout.maxMessages)))]
                    if appleOnly { arguments.append("--apple") }
                    if resume { arguments.append("--resume") }
                    if !keywords.trimmingCharacters(in: .whitespaces).isEmpty {
                        arguments += ["--filter"] + keywords.split(separator: " ").map(String.init)
                    }
                    arguments += ["--search-mode", searchMode, "--search-scope", searchScope]
                    arguments += ["--file-types"] + fileTypes.sorted()
                    arguments += ["--channels"] + channels.filter(\.selected).map(\.name)
                }
                var environment: [String: String] = [:]
                if ["download", "login", "logout"].contains(operation) {
                    let credentials = apiID.isEmpty && apiHash.isEmpty
                        ? try KeychainCredentials().load() : try Credentials(apiID: apiID, apiHash: apiHash)
                    environment = credentials.environment
                }
                let stream = try await engine.start(executable: executable, arguments: arguments,
                    environment: environment)
                for await event in stream { handle(event, operation: operation) }
                if error != nil { status = "Operation failed" }
                if error == nil, status == "Completed", operation == "download" {
                    notifyCompletion()
                    if revealOnComplete { NSWorkspace.shared.open(URL(fileURLWithPath: downloadFolder)) }
                }
            } catch {
                self.error = "Unable to run the engine. Check the installation and Settings."
                status = "Operation failed"
            }
        }
    }

    func handle(_ event: EngineEvent, operation: String) {
        if event.type == "plan" { moves += event.moves ?? []; planID = event.planID }
        if event.type == "error" { error = event.message ?? "Engine operation failed." }
        if event.type == "login_required" { loginField = event.field }
        if let channel = event.channel, let index = transfers.firstIndex(where: { $0.channel == channel }) {
            switch event.type {
            case "file_start":
                transfers[index].filename = event.filename ?? "Downloading"
                transfers[index].received = 0
                transfers[index].total = 0
            case "progress":
                let received = max(0, event.done ?? 0)
                transferred += max(0, received - transfers[index].received)
                transfers[index].received = received
                transfers[index].total = max(0, event.total ?? 0)
                speed = Double(transferred) / max(Date().timeIntervalSince(started), 1)
            case "file_done": transfers[index].downloaded = event.count ?? transfers[index].downloaded + 1
            case "channel_done":
                transfers[index].downloaded = event.count ?? 0
                transfers[index].skipped = event.skipped ?? 0
                transfers[index].errors = event.errors ?? 0
                transfers[index].finished = true
            default: break
            }
        }
        if event.type != "progress" && event.type != "login_required" {
            logs.append([event.type, event.channel, event.filename].compactMap { $0 }.joined(separator: " · "))
            if logs.count > Layout.maxLogEntries { logs.removeFirst(logs.count - Layout.maxLogEntries) }
        }
        if event.type == "done" {
            if operation == "organize" || operation == "undo" { planID = nil; moves = [] }
            status = event.status == "ok" ? "Completed" : event.status == "cancelled" ? "Stopped" : "Operation failed"
        }
        updateDock(active: event.type != "done")
    }

    func stop() { loginField = nil; status = "Stopping…"; Task { await engine.cancel() } }
    func respond(_ value: String) {
        guard let field = loginField else { return }
        loginField = nil
        Task {
            do { try await engine.send(EngineCommand("login_response", field: field, value: value)) }
            catch { self.error = "Login response could not be delivered."; stop() }
        }
    }

    func updateDock(active: Bool) {
        guard active, running, activeOperation == "download", !transfers.isEmpty else {
            DockProgress.update(fraction: nil, label: nil)
            return
        }
        let completed = transfers.filter(\.finished).count
        let partial = transfers.filter { !$0.finished }.reduce(0.0) { $0 + $1.fraction }
        DockProgress.update(fraction: (Double(completed) + partial) / Double(transfers.count),
                            label: "\(completed)/\(transfers.count)")
    }
}
