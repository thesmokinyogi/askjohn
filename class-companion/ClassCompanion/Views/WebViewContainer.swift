import SwiftUI
import WebKit

struct WebViewContainer: View {
    @ObservedObject var viewModel: ContentViewModel

    var body: some View {
        ZStack {
            WebView(viewModel: viewModel)

            if viewModel.showBookmarks {
                BookmarksView(viewModel: viewModel)
                    .transition(.move(edge: .trailing))
            }
        }
    }
}

struct WebView: UIViewRepresentable {
    @ObservedObject var viewModel: ContentViewModel

    func makeUIView(context: Context) -> WKWebView {
        let webView = WKWebView()
        webView.navigationDelegate = context.coordinator
        webView.allowsBackForwardNavigationGestures = true

        // Subscribe to navigation notifications
        context.coordinator.setupNotifications(webView: webView)

        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        // Only load if URL changed and is not empty
        if !viewModel.currentURL.isEmpty,
           webView.url?.absoluteString != viewModel.currentURL {
            if let url = URL(string: viewModel.currentURL) {
                let request = URLRequest(url: url)
                webView.load(request)
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(viewModel: viewModel)
    }

    class Coordinator: NSObject, WKNavigationDelegate {
        var viewModel: ContentViewModel
        private var observers: [NSObjectProtocol] = []

        init(viewModel: ContentViewModel) {
            self.viewModel = viewModel
        }

        func setupNotifications(webView: WKWebView) {
            let backObserver = NotificationCenter.default.addObserver(
                forName: .webViewGoBack,
                object: nil,
                queue: .main
            ) { _ in
                if webView.canGoBack {
                    webView.goBack()
                }
            }

            let forwardObserver = NotificationCenter.default.addObserver(
                forName: .webViewGoForward,
                object: nil,
                queue: .main
            ) { _ in
                if webView.canGoForward {
                    webView.goForward()
                }
            }

            let reloadObserver = NotificationCenter.default.addObserver(
                forName: .webViewReload,
                object: nil,
                queue: .main
            ) { _ in
                webView.reload()
            }

            observers = [backObserver, forwardObserver, reloadObserver]
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            viewModel.canGoBack = webView.canGoBack
            viewModel.canGoForward = webView.canGoForward
        }

        func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
            viewModel.canGoBack = webView.canGoBack
            viewModel.canGoForward = webView.canGoForward
        }

        deinit {
            observers.forEach { NotificationCenter.default.removeObserver($0) }
        }
    }
}
