import XCTest
@testable import BoardVaultCore

final class SearchQueryTests: XCTestCase {
    func testPreciseModelQueries() {
        let cases: [(String, String, Bool)] = [
            ("820-1960 (project M50).rar", "M5", false),
            ("MacBook_Pro_M5.pdf", "MacBook Pro M5", true),
            ("MacBookPro M5Pro schematic.pdf", "MacBook Pro M5", true),
            ("Mac Book Pro M5.pdf", "macbook pro m5", true),
            ("MacBook Pro M4.pdf", "MacBook Pro M5", false),
            ("MacBook Air M5.pdf", "MacBook Pro M5", false),
            ("MacBook Pro M50.pdf", "MacBook Pro M5", false),
            ("MacBook Pro M5.pdf", "M5 Max", false),
            ("820-1960.pdf", "820-1960", true),
            ("820-19601.pdf", "820-1960", false),
            ("any.pdf", " ", true),
            ("any.pdf", "---", false)
        ]
        for (text, query, expected) in cases {
            XCTAssertEqual(SearchQuery.matches(text, query: query), expected, "\(text) / \(query)")
        }
    }
}
