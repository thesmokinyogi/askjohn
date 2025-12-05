import SwiftUI
import Combine

class ContentViewModel: ObservableObject {
    @Published var isClassMode: Bool = false {
        didSet {
            updateIdleTimerState()
        }
    }

    @Published var currentURL: String = ""
    @Published var canGoBack: Bool = false
    @Published var canGoForward: Bool = false
    @Published var showBookmarks: Bool = false

    @Published var bookmarks: [Bookmark] = [
        Bookmark(name: "Spotify", url: "https://open.spotify.com"),
        Bookmark(name: "Pandora", url: "https://www.pandora.com"),
        Bookmark(name: "Tidal", url: "https://listen.tidal.com"),
        Bookmark(name: "Apple Music", url: "https://music.apple.com")
    ]

    private let bookmarksKey = "saved_bookmarks"

    init() {
        loadBookmarks()
        // Start with Spotify by default
        currentURL = "https://open.spotify.com"
    }

    private func updateIdleTimerState() {
        UIApplication.shared.isIdleTimerDisabled = isClassMode
    }

    func toggleClassMode() {
        isClassMode.toggle()
    }

    func loadURL(_ urlString: String) {
        currentURL = urlString
        showBookmarks = false
    }

    func addBookmark(name: String, url: String) {
        let bookmark = Bookmark(name: name, url: url)
        bookmarks.append(bookmark)
        saveBookmarks()
    }

    func deleteBookmark(at indexSet: IndexSet) {
        bookmarks.remove(atOffsets: indexSet)
        saveBookmarks()
    }

    private func saveBookmarks() {
        if let encoded = try? JSONEncoder().encode(bookmarks) {
            UserDefaults.standard.set(encoded, forKey: bookmarksKey)
        }
    }

    private func loadBookmarks() {
        if let data = UserDefaults.standard.data(forKey: bookmarksKey),
           let decoded = try? JSONDecoder().decode([Bookmark].self, from: data) {
            bookmarks = decoded
        }
    }
}

struct Bookmark: Identifiable, Codable {
    let id: UUID
    let name: String
    let url: String

    init(id: UUID = UUID(), name: String, url: String) {
        self.id = id
        self.name = name
        self.url = url
    }
}
