import SwiftUI

struct BookmarksView: View {
    @ObservedObject var viewModel: ContentViewModel
    @State private var showAddBookmark = false

    var body: some View {
        NavigationView {
            List {
                ForEach(viewModel.bookmarks) { bookmark in
                    Button(action: {
                        viewModel.loadURL(bookmark.url)
                    }) {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(bookmark.name)
                                    .font(.headline)
                                Text(bookmark.url)
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                            }
                            Spacer()
                            Image(systemName: "chevron.right")
                                .foregroundColor(.secondary)
                                .font(.caption)
                        }
                    }
                    .foregroundColor(.primary)
                }
                .onDelete(perform: viewModel.deleteBookmark)
            }
            .navigationTitle("Bookmarks")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Done") {
                        viewModel.showBookmarks = false
                    }
                }

                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        showAddBookmark = true
                    }) {
                        Image(systemName: "plus")
                    }
                }
            }
            .sheet(isPresented: $showAddBookmark) {
                AddBookmarkView(viewModel: viewModel)
            }
        }
    }
}

struct AddBookmarkView: View {
    @ObservedObject var viewModel: ContentViewModel
    @Environment(\.dismiss) var dismiss

    @State private var bookmarkName = ""
    @State private var bookmarkURL = ""

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Bookmark Details")) {
                    TextField("Name", text: $bookmarkName)
                    TextField("URL", text: $bookmarkURL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                }

                Section {
                    Button("Add Bookmark") {
                        let urlString = bookmarkURL.hasPrefix("http") ? bookmarkURL : "https://\(bookmarkURL)"
                        viewModel.addBookmark(name: bookmarkName, url: urlString)
                        dismiss()
                    }
                    .disabled(bookmarkName.isEmpty || bookmarkURL.isEmpty)
                }
            }
            .navigationTitle("Add Bookmark")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
            }
        }
    }
}
