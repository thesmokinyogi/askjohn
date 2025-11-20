# Class Companion

A simple iOS app that helps you stay focused during class by keeping your screen awake and providing easy access to web-based media players and tools.

## Features

- **Class Mode Toggle**: One-tap toggle to keep your screen awake
- **Embedded Web Browser**: Access Spotify, Pandora, Tidal, and other web apps without leaving the app
- **Custom Bookmarks**: Add your own web apps and services
- **Browser Controls**: Navigate back, forward, and reload pages
- **Persistent Settings**: Your bookmarks and preferences are saved

## How It Works

When "Class Mode" is enabled, your iPhone screen will stay awake as long as the app is in the foreground. This allows you to:

1. Use the Spotify Web Player (or other media services) within the app
2. Browse course materials, Canvas, etc.
3. Keep your screen on during presentations or note-taking

## Default Bookmarks

- Spotify (open.spotify.com)
- Pandora (pandora.com)
- Tidal (listen.tidal.com)
- Apple Music (music.apple.com)

You can add unlimited custom bookmarks through the app.

## Requirements

- iOS 15.0 or later
- iPhone or iPad
- Spotify Premium (for full Spotify Web Player functionality)

## Installation

1. Open the project in Xcode
2. Select your development team in the project settings
3. Build and run on your device

## Usage

1. Launch the app
2. Toggle "Class Mode" ON to keep your screen awake
3. Tap the bookmark icon to access your saved sites
4. Navigate using the back/forward/reload controls
5. Add custom bookmarks with the "+" button
6. Toggle "Class Mode" OFF when you're done to restore normal auto-lock behavior

## Technical Notes

- The app uses `UIApplication.shared.isIdleTimerDisabled` to prevent screen sleep
- Screen wake-lock only works while the app is in the foreground
- Web content is displayed using WKWebView
- Bookmarks are persisted using UserDefaults

## License

MIT License - feel free to use and modify as needed.
