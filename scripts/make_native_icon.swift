// Rebuild: swift scripts/make_native_icon.swift native/resources/app.png
import AppKit

let canvas: CGFloat = 1024
let tile = NSRect(x: 80, y: 80, width: 864, height: 864)
let board = NSRect(x: 225, y: 225, width: 574, height: 574)
let vault = NSRect(x: 363, y: 363, width: 298, height: 298)
let traceRows: [CGFloat] = [414, 512, 610]
let traceWidth: CGFloat = 20
let padRadius: CGFloat = 17
func color(_ hex: UInt32) -> NSColor {
    NSColor(srgbRed: CGFloat((hex >> 16) & 255) / 255,
            green: CGFloat((hex >> 8) & 255) / 255, blue: CGFloat(hex & 255) / 255, alpha: 1)
}
let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: Int(canvas), pixelsHigh: Int(canvas),
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
    bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
func plate(_ rect: NSRect, radius: CGFloat, top: UInt32, bottom: UInt32, edge: UInt32) {
    let path = NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
    NSGradient(starting: color(bottom), ending: color(top))!.draw(in: path, angle: 70)
    color(edge).setStroke()
    path.lineWidth = 3
    path.stroke()
}
plate(tile, radius: 190, top: 0x263d50, bottom: 0x0b1424, edge: 0x4c6578)
plate(board, radius: 96, top: 0x207f80, bottom: 0x11424f, edge: 0x49a99e)
color(0x9cf6e1).set()
for row in traceRows {
    for (start, end) in [(CGFloat(286), vault.minX), (CGFloat(738), vault.maxX)] {
        for vertical in [false, true] {
            let from = NSPoint(x: vertical ? row : start, y: vertical ? start : row)
            let to = NSPoint(x: vertical ? row : end, y: vertical ? end : row)
            let path = NSBezierPath()
            path.move(to: from); path.line(to: to)
            path.lineWidth = traceWidth; path.lineCapStyle = .round; path.stroke()
            NSBezierPath(ovalIn: NSRect(x: from.x - padRadius, y: from.y - padRadius,
                width: padRadius * 2, height: padRadius * 2)).fill()
        }
    }
}
plate(vault, radius: 58, top: 0xeefaf8, bottom: 0xa5cacd, edge: 0xffffff)
let mark = NSBezierPath()
mark.move(to: NSPoint(x: 437, y: 573))
mark.line(to: NSPoint(x: 512, y: 441))
mark.line(to: NSPoint(x: 587, y: 573))
color(0x16394a).setStroke()
mark.lineWidth = 36; mark.lineCapStyle = .round; mark.lineJoinStyle = .round; mark.stroke()
NSGraphicsContext.restoreGraphicsState()
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
