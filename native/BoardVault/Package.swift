// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "BoardVault",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "BoardVault", targets: ["BoardVault"])],
    targets: [
        .target(name: "BoardVaultCore"),
        .executableTarget(name: "BoardVault", dependencies: ["BoardVaultCore"]),
        .testTarget(name: "BoardVaultCoreTests", dependencies: ["BoardVaultCore"])
    ]
)
