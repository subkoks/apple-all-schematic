import Foundation

/// Shared native search semantics: all whole tokens, with common joined model names.
public enum SearchQuery {
    private static func tokens(_ text: String) -> Set<String> {
        let normalized = text.lowercased()
            .replacingOccurrences(of: "mac[\\W_]*book", with: "macbook", options: .regularExpression)
            .replacingOccurrences(of: "macbook(pro|air)\\b", with: "macbook $1", options: .regularExpression)
            .replacingOccurrences(of: "\\b(m\\d+)(pro|max|ultra)\\b", with: "$1 $2", options: .regularExpression)
        return Set(normalized.components(separatedBy: CharacterSet.alphanumerics.inverted).filter { !$0.isEmpty })
    }

    public static func matches(_ text: String, query: String) -> Bool {
        guard !query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return true }
        let wanted = tokens(query)
        return !wanted.isEmpty && wanted.isSubset(of: tokens(text))
    }
}
