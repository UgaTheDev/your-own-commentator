// Records ONE window (by CGWindowID) with its app's audio, even when other windows cover it.
// Usage: winrec <windowID> <out.mov> <seconds>    Prints the epoch ms when the first frame lands.
import Foundation
import ScreenCaptureKit
import AVFoundation
import AppKit

_ = NSApplication.shared  // initializes the window-server connection ScreenCaptureKit needs

let args = CommandLine.arguments
guard args.count == 4, let wid = UInt32(args[1]), let secs = Double(args[3]) else {
    FileHandle.standardError.write("usage: winrec <windowID> <out.mov> <seconds>\n".data(using: .utf8)!); exit(2)
}
let out = URL(fileURLWithPath: args[2])
try? FileManager.default.removeItem(at: out)

final class Delegate: NSObject, SCRecordingOutputDelegate {
    func recordingOutputDidStartRecording(_ r: SCRecordingOutput) {
        print("start_ms \(Int(Date().timeIntervalSince1970 * 1000))"); fflush(stdout)
    }
    func recordingOutput(_ r: SCRecordingOutput, didFailWithError e: Error) {
        FileHandle.standardError.write("record failed: \(e)\n".data(using: .utf8)!); exit(1)
    }
}

Task {
    do {
        let content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
        guard let win = content.windows.first(where: { $0.windowID == wid }) else {
            FileHandle.standardError.write("window \(wid) not found\n".data(using: .utf8)!); exit(1)
        }
        let filter = SCContentFilter(desktopIndependentWindow: win)
        let cfg = SCStreamConfiguration()
        let scale = CGFloat(filter.pointPixelScale)
        cfg.width = Int(win.frame.width * scale)
        cfg.height = Int(win.frame.height * scale)
        cfg.minimumFrameInterval = CMTime(value: 1, timescale: 30)
        cfg.showsCursor = false
        cfg.capturesAudio = true
        cfg.excludesCurrentProcessAudio = true
        cfg.sampleRate = 48000
        cfg.channelCount = 2
        let rc = SCRecordingOutputConfiguration()
        rc.outputURL = out
        rc.outputFileType = .mov
        rc.videoCodecType = .h264
        let del = Delegate()
        let rec = SCRecordingOutput(configuration: rc, delegate: del)
        let stream = SCStream(filter: filter, configuration: cfg, delegate: nil)
        try stream.addRecordingOutput(rec)
        try await stream.startCapture()
        try await Task.sleep(nanoseconds: UInt64(secs * 1e9))
        try await stream.stopCapture()
        try await Task.sleep(nanoseconds: 1_000_000_000)  // let the file finalize
        print("saved \(out.path) \(cfg.width)x\(cfg.height)")
        exit(0)
    } catch {
        FileHandle.standardError.write("error: \(error)\n".data(using: .utf8)!); exit(1)
    }
}
RunLoop.main.run()
