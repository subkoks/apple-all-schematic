import Foundation

public struct OrganizeMove: Codable, Identifiable, Sendable {
    public var id: String { src }
    public let src: String
    public let dest: String
    public let category: String
    public let confidence: String
}

public struct EngineEvent: Codable, Sendable {
    public let type: String
    public var version: Int? = 1
    public var channel: String?
    public var filename: String?
    public var path: String?
    public var done: Int64?
    public var total: Int64?
    public var bytes: Int64?
    public var count: Int?
    public var skipped: Int?
    public var errors: Int?
    public var message: String?
    public var field: String?
    public var status: String?
    public var channels: [String: [String]]?
    public var moves: [OrganizeMove]?
    public var planID: String?

    public init(type: String, message: String? = nil) {
        self.type = type
        self.message = message
    }
}

public struct EngineCommand: Encodable, Sendable {
    public let command: String
    public let field: String?
    public let value: String?
    public init(_ command: String, field: String? = nil, value: String? = nil) {
        self.command = command
        self.field = field
        self.value = value
    }
}

public enum EngineFailure: Error { case alreadyRunning, unavailable, notRunning }

public actor EngineClient {
    public static let cancellationGrace: UInt64 = 2_000_000_000
    private static let maxLineBytes = 1_048_576
    private var process: Process?
    private var input: FileHandle?
    private var continuation: AsyncStream<EngineEvent>.Continuation?
    private var buffer = Data()
    private var receivedDone = false
    private var failedProtocol = false
    private var generation = UUID()
    private var exitStatus: Int32?
    private var outputEnded = false

    public init() {}

    public func start(executable: URL, arguments: [String], environment: [String: String] = [:],
                      directory: URL? = nil) throws -> AsyncStream<EngineEvent> {
        guard process == nil else { throw EngineFailure.alreadyRunning }
        let child = Process()
        let stdin = Pipe(), stdout = Pipe(), stderr = Pipe()
        child.executableURL = executable
        child.arguments = arguments
        child.currentDirectoryURL = directory
        // Explicit allowlist: never inherit unrelated credentials into the sidecar.
        var childEnvironment = ["PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "PYTHONUNBUFFERED": "1",
                                "PYTHON_DOTENV_DISABLED": "1", "LANG": "en_US.UTF-8"]
        childEnvironment["HOME"] = NSHomeDirectory()
        childEnvironment.merge(environment) { _, new in new }
        child.environment = childEnvironment
        child.standardInput = stdin
        child.standardOutput = stdout
        child.standardError = stderr
        let stream = AsyncStream<EngineEvent> { continuation = $0 }
        buffer.removeAll(keepingCapacity: true)
        receivedDone = false
        failedProtocol = false
        generation = UUID()
        let runID = generation
        exitStatus = nil
        outputEnded = false
        child.terminationHandler = { [weak self] child in
            Task { await self?.recordExit(child.terminationStatus, runID: runID) }
        }
        do { try child.run() } catch {
            continuation?.finish()
            continuation = nil
            throw EngineFailure.unavailable
        }
        process = child
        input = stdin.fileHandleForWriting
        // Drain both pipes independently. Never block MainActor or retain stderr values.
        Task.detached {
            while !stderr.fileHandleForReading.availableData.isEmpty {}
            try? stderr.fileHandleForReading.close()
        }
        Task.detached { [self] in
            while true {
                let chunk = stdout.fileHandleForReading.availableData
                if chunk.isEmpty { break }
                await ingest(chunk, runID: runID)
            }
            try? stdout.fileHandleForReading.close()
            await endedOutput(runID: runID)
        }
        continuation?.onTermination = { [weak self] _ in
            Task { await self?.cancel(runID: runID) }
        }
        return stream
    }

    private func ingest(_ data: Data, runID: UUID) {
        guard runID == generation, !failedProtocol else { return }
        buffer.append(data)
        while let newline = buffer.firstIndex(of: 10) {
            let line = buffer.prefix(upTo: newline)
            guard line.count <= Self.maxLineBytes,
                  let event = try? JSONDecoder().decode(EngineEvent.self, from: line),
                  event.version == 1, !receivedDone else {
                protocolError(runID: runID)
                return
            }
            buffer.removeSubrange(...newline)
            if event.type == "done" { receivedDone = true }
            continuation?.yield(event)
        }
        if buffer.count > Self.maxLineBytes { protocolError(runID: runID) }
    }

    private func protocolError(runID: UUID) {
        guard runID == generation, !failedProtocol else { return }
        failedProtocol = true
        continuation?.yield(EngineEvent(type: "error", message: "Invalid engine response."))
        terminate(runID: runID)
    }

    private func recordExit(_ status: Int32, runID: UUID) {
        guard runID == generation else { return }
        exitStatus = status
        finishIfReady(runID: runID)
    }

    private func endedOutput(runID: UUID) {
        guard runID == generation else { return }
        outputEnded = true
        finishIfReady(runID: runID)
    }

    private func finishIfReady(runID: UUID) {
        guard outputEnded, let status = exitStatus else { return }
        guard runID == generation else { return }
        if status != 0 || !receivedDone || !buffer.isEmpty {
            continuation?.yield(EngineEvent(type: "error", message: "Engine exited unexpectedly (\(status))."))
        }
        try? input?.close()
        input = nil
        process = nil
        continuation?.finish()
        continuation = nil
    }

    public func send(_ command: EngineCommand) throws {
        guard let input, process?.isRunning == true else { throw EngineFailure.notRunning }
        var data = try JSONEncoder().encode(command)
        data.append(10)
        try input.write(contentsOf: data)
    }

    public func cancel() { cancel(runID: generation) }

    private func cancel(runID: UUID) {
        guard runID == generation, let child = process, child.isRunning else { return }
        try? send(EngineCommand("cancel"))
        Task {
            try? await Task.sleep(nanoseconds: Self.cancellationGrace)
            terminate(runID: runID)
        }
    }

    private func terminate(runID: UUID) {
        guard runID == generation, let child = process, child.isRunning else { return }
        child.terminate()
        Task {
            try? await Task.sleep(nanoseconds: Self.cancellationGrace)
            forceStop(runID: runID)
        }
    }

    private func forceStop(runID: UUID) {
        guard runID == generation, let child = process, child.isRunning else { return }
        kill(child.processIdentifier, SIGKILL)
    }
}
