import AppKit
import Foundation

final class NotificationDelegate: NSObject, NSUserNotificationCenterDelegate {
    private let detailURL: URL
    private let timeout: TimeInterval

    init(detailURL: URL, timeout: TimeInterval = 20) {
        self.detailURL = detailURL
        self.timeout = timeout
        super.init()
    }

    func userNotificationCenter(
        _ center: NSUserNotificationCenter,
        shouldPresent notification: NSUserNotification
    ) -> Bool {
        true
    }

    func userNotificationCenter(
        _ center: NSUserNotificationCenter,
        didActivate notification: NSUserNotification
    ) {
        switch notification.activationType {
        case .actionButtonClicked, .contentsClicked:
            NSWorkspace.shared.open(detailURL)
        default:
            break
        }

        center.removeDeliveredNotification(notification)
        CFRunLoopStop(CFRunLoopGetMain())
    }

    func run() {
        let deadline = Date().addingTimeInterval(timeout)
        while RunLoop.current.run(mode: .default, before: deadline) && Date() < deadline {
        }
    }
}

func makeNotification(title: String, subtitle: String, body: String) -> NSUserNotification {
    let notification = NSUserNotification()
    notification.title = title
    notification.subtitle = subtitle.isEmpty ? nil : subtitle
    notification.informativeText = body
    notification.soundName = nil
    notification.hasActionButton = true
    notification.actionButtonTitle = "Open Card"
    notification.otherButtonTitle = "Dismiss"
    return notification
}

let arguments = CommandLine.arguments
guard arguments.count == 5 else {
    fputs("Usage: swift NotificationDetailHelper.swift <title> <subtitle> <body> <page-path>\n", stderr)
    exit(1)
}

let title = arguments[1]
let subtitle = arguments[2]
let body = arguments[3]
let pagePath = arguments[4]
let detailURL = URL(fileURLWithPath: pagePath)

let center = NSUserNotificationCenter.default
let delegate = NotificationDelegate(detailURL: detailURL)
center.delegate = delegate
center.deliver(makeNotification(title: title, subtitle: subtitle, body: body))
delegate.run()
