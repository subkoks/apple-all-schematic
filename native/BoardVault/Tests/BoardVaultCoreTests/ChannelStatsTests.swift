import XCTest
@testable import BoardVault

final class ChannelStatsTests: XCTestCase {
    func testPublicPreviewCountParsing() {
        XCTAssertEqual(ChannelStats.parse(#"<div class="tgme_page_extra">147 966 subscribers</div>"#), 147966)
        XCTAssertEqual(ChannelStats.parse(#"<div class="tgme_page_extra">2,350 members</div>"#), 2350)
        XCTAssertNil(ChannelStats.parse("<div>Private channel</div>"))
    }
}
