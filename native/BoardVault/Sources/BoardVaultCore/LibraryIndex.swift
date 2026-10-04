import Foundation

public struct LibraryNode: Identifiable, Sendable {
    public var id: String { url.path }
    public let url: URL
    public let name: String
    public var children: [LibraryNode]?
    public var isDirectory: Bool { children != nil }
}

public enum LibraryIndex {
    public static func scan(root: URL, search: String = "") throws -> [LibraryNode] {
        let manager = FileManager.default
        guard manager.fileExists(atPath: root.path) else { return [] }
        let keys: Set<URLResourceKey> = [.isDirectoryKey, .isSymbolicLinkKey, .isRegularFileKey]
        func walk(_ directory: URL) throws -> [LibraryNode] {
            try Task.checkCancellation()
            return try manager.contentsOfDirectory(at: directory, includingPropertiesForKeys: Array(keys), options: [.skipsHiddenFiles])
                .sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
                .compactMap { url in
                    let attributes = try url.resourceValues(forKeys: keys)
                    guard attributes.isSymbolicLink != true else { return nil }
                    let name = url.lastPathComponent
                    if attributes.isDirectory == true {
                        let children = try walk(url)
                        guard search.isEmpty || !children.isEmpty || name.localizedCaseInsensitiveContains(search) else { return nil }
                        return LibraryNode(url: url, name: name, children: children)
                    }
                    guard attributes.isRegularFile == true, search.isEmpty || name.localizedCaseInsensitiveContains(search) else { return nil }
                    return LibraryNode(url: url, name: name, children: nil)
                }
        }
        return try walk(root)
    }
}
