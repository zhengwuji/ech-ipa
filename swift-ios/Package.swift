// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "ECHWorkers",
    platforms: [
        .iOS(.v14)
    ],
    products: [
        .executable(name: "ECHWorkers", targets: ["ECHWorkers"])
    ],
    targets: [
        .executableTarget(
            name: "ECHWorkers",
            dependencies: [],
            path: ".",
            sources: [
                "ECHWorkersApp.swift",
                "ContentView.swift",
                "ECHNetworkManager.swift"
            ],
            resources: [
                .copy("Assets.xcassets")
            ]
        )
    ]
)
