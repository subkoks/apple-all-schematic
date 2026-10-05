import XCTest
@testable import BoardVaultCore

final class EngineClientTests: XCTestCase {
    private func run(_ script: String) async throws -> [EngineEvent] {
        let client = EngineClient()
        let stream = try await client.start(executable: URL(fileURLWithPath: "/usr/bin/python3"), arguments: ["-u", "-c", script])
        var events: [EngineEvent] = []
        for await event in stream { events.append(event) }
        return events
    }

    func testSplitLinesAndProgress() async throws {
        let events = try await run("import sys; sys.stdout.write('{\"type\":\"progress\",\"version\":1,\"done\":2,'); sys.stdout.flush(); print('\"total\":4}'); print('{\"type\":\"done\",\"version\":1,\"status\":\"ok\"}')")
        XCTAssertEqual(events.map(\.type), ["progress", "done"])
        XCTAssertEqual(events.first?.done, 2)
    }

    func testCrashAndMissingDone() async throws {
        let events = try await run("import sys; sys.exit(7)")
        XCTAssertEqual(events.last?.type, "error")
    }

    func testMalformedAndUnterminatedOutput() async throws {
        for script in ["print('not json')", "print('{', end='')", "print('{\"type\":\"done\",\"version\":999}')"] {
            let events = try await run(script)
            XCTAssertEqual(events.last?.type, "error")
        }
    }

    func testStderrCannotBlockOrLeak() async throws {
        let events = try await run("import sys; sys.stderr.write('sensitive' * 100000); print('{\"type\":\"done\",\"version\":1}')")
        XCTAssertEqual(events.map(\.type), ["done"])
    }

    func testLoginAndCancelCommand() async throws {
        let client = EngineClient()
        let script = "import json,sys; print('{\"type\":\"login_required\",\"version\":1,\"field\":\"code\"}'); c=json.loads(input()); assert c['value']=='fixture'; c=json.loads(input()); assert c['command']=='cancel'; print('{\"type\":\"done\",\"version\":1,\"status\":\"cancelled\"}')"
        let stream = try await client.start(executable: URL(fileURLWithPath: "/usr/bin/python3"), arguments: ["-u", "-c", script])
        var types: [String] = []
        for await event in stream {
            types.append(event.type)
            if event.type == "login_required" {
                try await client.send(EngineCommand("login_response", field: "code", value: "fixture"))
                await client.cancel()
            }
        }
        XCTAssertEqual(types, ["login_required", "done"])
    }

    func testMalformedEngineIgnoringTerminationIsKilled() async throws {
        let events = try await run("import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('broken', flush=True); time.sleep(30)")
        XCTAssertEqual(events.first?.message, "Invalid engine response.")
        XCTAssertEqual(events.last?.type, "error")
    }

    func testCancellationFallback() async throws {
        let client = EngineClient()
        let stream = try await client.start(executable: URL(fileURLWithPath: "/usr/bin/python3"), arguments: ["-u", "-c", "import time; time.sleep(30)"])
        await client.cancel()
        var events: [EngineEvent] = []
        for await event in stream { events.append(event) }
        XCTAssertEqual(events.last?.type, "error")
    }
}
