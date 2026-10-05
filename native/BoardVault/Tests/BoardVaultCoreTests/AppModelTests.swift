import XCTest
import BoardVaultCore
@testable import BoardVault

final class AppModelTests: XCTestCase {
    @MainActor func testCatalogUpdatePreservesChoicesAndRemovedChannels() {
        let existing = [Channel(name: "CUSTOM", category: "apple", selected: true),
                        Channel(name: "boardviews", category: "laptop", selected: true)]
        let additions = [Channel(name: "BoardViews", category: "laptop"),
                         Channel(name: "removed", category: "laptop"),
                         Channel(name: "newsource", category: "laptop", note: "Archive only")]
        let merged = AppModel.mergingAdditions(existing, additions: additions, seen: ["removed"])
        XCTAssertEqual(merged.map(\.name), ["CUSTOM", "boardviews", "newsource"])
        XCTAssertTrue(merged[0].selected)
        XCTAssertTrue(merged[1].selected)
        XCTAssertFalse(merged[2].selected)
        XCTAssertEqual(merged[2].note, "Archive only")
        let afterRemoval = AppModel.mergingAdditions(existing, additions: additions, seen: ["removed", "newsource"])
        XCTAssertEqual(afterRemoval.map(\.name), existing.map(\.name))
    }

    @MainActor func testDownloadProgressAndFailure() throws {
        let model = AppModel(loadSavedState: false)
        model.transfers = [Transfer(channel: "fixture")]
        let decoder = JSONDecoder()
        func event(_ json: String) throws -> EngineEvent { try decoder.decode(EngineEvent.self, from: Data(json.utf8)) }
        model.handle(try event(#"{"type":"file_start","channel":"fixture","filename":"a.pdf"}"#), operation: "download")
        model.handle(try event(#"{"type":"progress","channel":"fixture","done":50,"total":100}"#), operation: "download")
        XCTAssertEqual(model.transfers[0].fraction, 0.5)
        model.handle(try event(#"{"type":"channel_done","channel":"fixture","count":1,"skipped":2,"errors":0}"#), operation: "download")
        XCTAssertEqual(model.totalFiles, 1)
        XCTAssertEqual(model.transfers[0].skipped, 2)
        model.handle(EngineEvent(type: "error", message: "Fixture error"), operation: "download")
        XCTAssertEqual(model.error, "Fixture error")
    }

    @MainActor func testLoginPromptAndBoundedLogs() throws {
        let model = AppModel(loadSavedState: false)
        let login = try JSONDecoder().decode(EngineEvent.self, from: Data(#"{"type":"login_required","field":"password"}"#.utf8))
        model.handle(login, operation: "login")
        XCTAssertEqual(model.loginField, "password")
        XCTAssertTrue(model.logs.isEmpty)
        for _ in 0...Layout.maxLogEntries { model.handle(EngineEvent(type: "file_done"), operation: "download") }
        XCTAssertEqual(model.logs.count, Layout.maxLogEntries)
    }
}
