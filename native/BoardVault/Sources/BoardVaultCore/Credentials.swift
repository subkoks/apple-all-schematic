import Foundation
import Security

public enum CredentialError: Error { case invalid, unavailable(OSStatus), missing }

public struct Credentials: Codable, Equatable, Sendable {
    public let apiID: String
    public let apiHash: String
    public init(apiID: String, apiHash: String) throws {
        let id = apiID.trimmingCharacters(in: .whitespacesAndNewlines)
        let hash = apiHash.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let number = Int32(id), number > 0,
              hash.range(of: "^[A-Fa-f0-9]{32}$", options: .regularExpression) != nil else { throw CredentialError.invalid }
        self.apiID = id
        self.apiHash = hash
    }
    public var environment: [String: String] { ["TG_API_ID": apiID, "TG_API_HASH": apiHash] }

    public static func legacy(contents: String) throws -> Credentials {
        var values: [String: String] = [:]
        for raw in contents.split(whereSeparator: \.isNewline) {
            var line = raw.trimmingCharacters(in: .whitespaces)
            if line.hasPrefix("export ") { line = String(line.dropFirst("export ".count)) }
            guard !line.hasPrefix("#"), let separator = line.firstIndex(of: "=") else { continue }
            let key = line[..<separator].trimmingCharacters(in: .whitespaces)
            guard ["TG_API_ID", "TG_API_HASH"].contains(key) else { continue }
            var value = line[line.index(after: separator)...].trimmingCharacters(in: .whitespaces)
            if let first = value.first, first == "\"" || first == "'" {
                guard let end = value.dropFirst().firstIndex(of: first) else { throw CredentialError.invalid }
                value = String(value[value.index(after: value.startIndex)..<end])
            } else {
                value = String(value.split(separator: "#", maxSplits: 1).first ?? "").trimmingCharacters(in: .whitespaces)
            }
            values[key] = value
        }
        return try Credentials(apiID: values["TG_API_ID"] ?? "", apiHash: values["TG_API_HASH"] ?? "")
    }
}

public struct KeychainCredentials {
    private let service = "com.subkoks.boardvault.native"
    private let account = "telegram-api"
    public init() {}
    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service, kSecAttrAccount as String: account]
    }
    public func load() throws -> Credentials {
        var lookup = query
        lookup[kSecReturnData as String] = true
        lookup[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        let status = SecItemCopyMatching(lookup as CFDictionary, &result)
        if status == errSecItemNotFound { throw CredentialError.missing }
        guard status == errSecSuccess, let data = result as? Data else { throw CredentialError.unavailable(status) }
        let value = try JSONDecoder().decode(Credentials.self, from: data)
        return try Credentials(apiID: value.apiID, apiHash: value.apiHash)
    }
    public func save(_ credentials: Credentials) throws {
        let data = try JSONEncoder().encode(credentials)
        let attributes = [kSecValueData as String: data]
        var status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var insert = query
            insert[kSecValueData as String] = data
            insert[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            status = SecItemAdd(insert as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw CredentialError.unavailable(status) }
    }
}
