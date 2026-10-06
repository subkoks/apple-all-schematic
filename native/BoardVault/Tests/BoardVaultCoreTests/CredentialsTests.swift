import XCTest
@testable import BoardVaultCore

final class CredentialsTests: XCTestCase {
    private let fixtureHash = String(repeating: "a", count: 32)
    func testMigrationAndValidationWithoutKeychainAccess() throws {
        let credentials = try Credentials.legacy(contents: "# fixture only\nexport TG_API_ID='12345'\nTG_API_HASH=\"\(fixtureHash)\" # comment\nUNRELATED=ignored")
        XCTAssertEqual(credentials.apiID, "12345")
        XCTAssertEqual(credentials.apiHash, fixtureHash)
        XCTAssertEqual(Set(credentials.environment.keys), ["TG_API_ID", "TG_API_HASH"])
        XCTAssertThrowsError(try Credentials(apiID: "-1", apiHash: fixtureHash))
        XCTAssertThrowsError(try Credentials(apiID: "12345", apiHash: "invalid"))
        XCTAssertThrowsError(try Credentials.legacy(contents: "TG_API_ID=12345"))
    }
}
