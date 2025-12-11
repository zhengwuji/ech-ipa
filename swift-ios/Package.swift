// swift-tools-version:5.5
import PackageDescription

let package = Package(
    name: "ECHWorkers",
    platforms: [
        .iOS(.v12)
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
                "ProxyManager.swift"
            ],
            resources: [
                .copy("Resources")
            ]
        )
    ]
)
