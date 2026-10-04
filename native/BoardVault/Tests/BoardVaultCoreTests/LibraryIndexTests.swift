import XCTest
@testable import BoardVaultCore

final class LibraryIndexTests: XCTestCase {
    func testTreeSearchAndSymlinkExclusion() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        let apple = root.appendingPathComponent("Apple/iPhone")
        try FileManager.default.createDirectory(at: apple, withIntermediateDirectories: true)
        try Data("fixture".utf8).write(to: apple.appendingPathComponent("board.pdf"))
        try FileManager.default.createSymbolicLink(at: root.appendingPathComponent("cycle"), withDestinationURL: root)
        let tree = try LibraryIndex.scan(root: root)
        XCTAssertEqual(tree.map(\.name), ["Apple"])
        XCTAssertEqual(tree[0].children?[0].children?[0].name, "board.pdf")
        XCTAssertEqual(try LibraryIndex.scan(root: root, search: "BOARD").count, 1)
        XCTAssertTrue(try LibraryIndex.scan(root: root, search: "missing").isEmpty)
    }
}
