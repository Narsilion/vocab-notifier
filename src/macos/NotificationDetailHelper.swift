import AppKit
import Foundation

final class NotificationDelegate: NSObject, NSUserNotificationCenterDelegate {
    private let detailURL: URL
    private let acknowledgementCommand: String?
    private let timeout: TimeInterval

    init(detailURL: URL, acknowledgementCommand: String?, timeout: TimeInterval = 20) {
        self.detailURL = detailURL
        self.acknowledgementCommand = acknowledgementCommand
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
            if let acknowledgementCommand {
                runAcknowledgementCommand(acknowledgementCommand)
            } else {
                NSWorkspace.shared.open(detailURL)
            }
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

    private func runAcknowledgementCommand(_ command: String) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/bin/zsh")
        process.arguments = ["-lc", command]
        try? process.run()
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
guard arguments.count == 5 || arguments.count == 6 else {
    fputs(
        "Usage: swift NotificationDetailHelper.swift <title> <subtitle> <body> <page-path> [ack-command]\n",
        stderr
    )
    exit(1)
}

let title = arguments[1]
let subtitle = arguments[2]
let body = arguments[3]
let pagePath = arguments[4]
let acknowledgementCommand = arguments.count == 6 ? arguments[5] : nil
let detailURL = URL(fileURLWithPath: pagePath)

let center = NSUserNotificationCenter.default
let delegate = NotificationDelegate(detailURL: detailURL, acknowledgementCommand: acknowledgementCommand)
center.delegate = delegate
center.deliver(makeNotification(title: title, subtitle: subtitle, body: body))
delegate.run()
