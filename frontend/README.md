# PassForge PWA — Deployment Guide

A white-label Apple Wallet pass generator powered by the WalletWallet API.

## Files

```
passforge-pwa/
├── index.html       ← Full app (single file)
├── manifest.json    ← PWA manifest
├── sw.js            ← Service worker (offline support)
├── icons/
│   ├── icon-192.png
│   └── icon-512.png
└── README.md
```

## Deploy in 60 seconds

### Option A — Netlify (recommended, free)
1. Go to https://app.netlify.com/drop
2. Drag the entire `passforge-pwa/` folder onto the page
3. Done — you get a live HTTPS URL instantly

### Option B — Vercel
```bash
npm i -g vercel
cd passforge-pwa
vercel
```

### Option C — GitHub Pages
1. Push this folder to a GitHub repo
2. Settings → Pages → Source: main branch / root
3. Site live at https://yourusername.github.io/repo-name

### Option D — Cloudflare Pages
1. Push to GitHub
2. Cloudflare Dashboard → Pages → Connect to Git
3. No build command, output directory: `/` (root)

### Option E — Any static host
Upload the folder contents to any web server that serves static files over HTTPS.

> ⚠️ HTTPS is required for PWA install, service worker, and localStorage to work.

## Branding / Customization

Open `index.html` and search for these to rebrand:

| Find | Replace with |
|------|-------------|
| `PassForge` | Your app name |
| `#1a7a5e` | Your primary color |
| `#0a0f0d` | Your background color |

## PWA Features

- **Installable** — Add to Home Screen on iOS/Android/Desktop
- **Offline shell** — App loads without internet after first visit
- **API calls** — Always live (never cached), requires internet
- **Safe area** — Notch/home bar aware on iPhone
- **Dark theme** — Native dark mode throughout

## API Key

Users enter their own WalletWallet API key in the Settings tab.
Keys are stored in `localStorage` — never sent anywhere except the WalletWallet API.

Get a free key at: https://www.walletwallet.dev/signup/

## Pro Features

The following fields are marked "Pro" in the UI (require a Pro WalletWallet plan):
- Custom hex color (`color` field)
- Logo URL (`logoURL`)
- Thumbnail URL (`thumbnailURL`)
- Strip image URL (`stripURL`)
