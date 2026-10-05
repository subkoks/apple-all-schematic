import AppKit

@MainActor
enum DockProgress {
    private static let inset: CGFloat = 8
    private static let barHeight: CGFloat = 12

    static func update(fraction: Double?, label: String?) {
        guard let app = NSApp else { return }
        let tile = app.dockTile
        guard let fraction else {
            tile.contentView = nil
            tile.badgeLabel = nil
            tile.display()
            return
        }
        let view = NSView(frame: NSRect(origin: .zero, size: tile.size))
        let icon = NSImageView(frame: view.bounds)
        icon.image = app.applicationIconImage
        view.addSubview(icon)
        let bar = NSProgressIndicator(frame: NSRect(x: inset, y: inset,
            width: tile.size.width - inset * 2, height: barHeight))
        bar.style = .bar
        bar.isIndeterminate = false
        bar.minValue = 0
        bar.maxValue = 1
        bar.doubleValue = max(0, min(1, fraction))
        view.addSubview(bar)
        tile.contentView = view
        tile.badgeLabel = label
        tile.display()
    }
}
