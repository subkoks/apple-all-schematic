import Foundation

/// Approximate, public channel size from Telegram's unauthenticated preview page.
enum ChannelStats {
    private static let pattern = try! NSRegularExpression(
        pattern: #"tgme_page_extra[^>]*>\s*([0-9 ,\u00a0]+)\s*(?:subscribers|members)"#,
        options: [.caseInsensitive]
    )
    static let batchSize = 4
    static let timeout: TimeInterval = 6

    static func parse(_ html: String) -> Int? {
        let source = html as NSString
        guard let match = pattern.firstMatch(in: html, range: NSRange(location: 0, length: source.length)),
              let range = Range(match.range(at: 1), in: html) else { return nil }
        let digits = html[range].filter(\.isNumber)
        return Int(digits)
    }

    static func fetch(_ name: String) async -> Int? {
        guard name.range(of: #"^[A-Za-z][A-Za-z0-9_]{4,31}$"#, options: .regularExpression) != nil,
              let url = URL(string: "https://t.me/\(name)") else { return nil }
        let session = URLSession(configuration: .ephemeral)
        defer { session.invalidateAndCancel() }
        var request = URLRequest(url: url)
        request.timeoutInterval = timeout
        guard let (data, response) = try? await session.data(for: request),
              (response as? HTTPURLResponse)?.statusCode == 200,
              let html = String(data: data, encoding: .utf8) else { return nil }
        return parse(html)
    }
}

extension AppModel {
    func refreshFollowerCounts() {
        guard ProcessInfo.processInfo.environment["BOARDVAULT_FIXTURE_ROOT"] == nil else { return }
        let names = channels.map(\.name)
        Task {
            for start in stride(from: 0, to: names.count, by: ChannelStats.batchSize) {
                let batch = Array(names[start..<min(start + ChannelStats.batchSize, names.count)])
                await withTaskGroup(of: (String, Int?).self) { group in
                    for name in batch {
                        group.addTask { (name, await ChannelStats.fetch(name)) }
                    }
                    for await (name, count) in group {
                        if let count { followerCounts[name] = count }
                    }
                }
            }
        }
    }
}
