import SwiftUI

struct ControlBar: View {
    @ObservedObject var viewModel: ContentViewModel

    var body: some View {
        VStack(spacing: 12) {
            // Class Mode Toggle
            HStack {
                Text("Class Mode")
                    .font(.headline)

                Spacer()

                Toggle("", isOn: $viewModel.isClassMode)
                    .labelsHidden()
                    .tint(.green)
            }
            .padding(.horizontal)
            .padding(.top, 8)

            // Browser Controls
            HStack(spacing: 20) {
                // Back Button
                Button(action: {
                    NotificationCenter.default.post(name: .webViewGoBack, object: nil)
                }) {
                    Image(systemName: "chevron.left")
                        .font(.title2)
                }
                .disabled(!viewModel.canGoBack)
                .opacity(viewModel.canGoBack ? 1.0 : 0.3)

                // Forward Button
                Button(action: {
                    NotificationCenter.default.post(name: .webViewGoForward, object: nil)
                }) {
                    Image(systemName: "chevron.right")
                        .font(.title2)
                }
                .disabled(!viewModel.canGoForward)
                .opacity(viewModel.canGoForward ? 1.0 : 0.3)

                // Reload Button
                Button(action: {
                    NotificationCenter.default.post(name: .webViewReload, object: nil)
                }) {
                    Image(systemName: "arrow.clockwise")
                        .font(.title2)
                }

                Spacer()

                // Bookmarks Button
                Button(action: {
                    viewModel.showBookmarks.toggle()
                }) {
                    Image(systemName: "book.fill")
                        .font(.title2)
                }
            }
            .padding(.horizontal)
            .padding(.bottom, 8)

            // Status Indicator
            if viewModel.isClassMode {
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                    Text("Screen will stay awake")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.bottom, 8)
            }
        }
        .background(Color(.systemBackground))
        .shadow(radius: 2)
    }
}

extension Notification.Name {
    static let webViewGoBack = Notification.Name("webViewGoBack")
    static let webViewGoForward = Notification.Name("webViewGoForward")
    static let webViewReload = Notification.Name("webViewReload")
}
