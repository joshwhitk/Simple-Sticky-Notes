# Microsoft Store Submission

This document is the current submission plan for publishing `Simple Sticky Notes` in Microsoft Partner Center.

## Recommended Product Type

Use the `EXE/MSI` submission path for the first Store release.

Why this is the pragmatic first submission:

- the app already has a working offline Windows installer
- the installer supports silent install parameters required by the `EXE/MSI` flow
- moving to `MSIX` would add packaging work and runtime validation risk around startup integration and file-access behavior before the first Store launch

Current blocker discovered during Partner Center entry:

- GitHub release asset URLs are not acceptable as the `EXE/MSI` package URL because Partner Center rejects redirecting download links
- use a directly hosted installer URL you control for actual submission

Future note:

- `MSIX` remains a valid later upgrade if Store-managed packaging, identity, or update behavior becomes more valuable than the migration cost
- do not start the first product as `MSIX/PWA` unless an actual Store-ready `MSIX` package exists

## New Product Values

When creating the Partner Center product:

- Product type: `EXE/MSI`
- Reserved name: `Simple Sticky Notes`

## Submission Values

### Availability

- Pricing: `Free`
- Discoverability: `Available in Microsoft Store`
- Markets: start with the default market set unless there is a legal reason to limit distribution

### Properties

- Primary category: `Productivity`
- Secondary category: leave blank unless Partner Center strongly suggests one
- Does this product access, collect, or transmit personal information: `Yes`
  Reason: the app reads and writes user-authored markdown notes and note metadata in a user-chosen local folder, which may be inside an Obsidian vault
- Privacy policy URL: use the public URL for [PRIVACY_POLICY_DRAFT.md](PRIVACY_POLICY_DRAFT.md) once hosted
- Website: `https://github.com/joshwhitk/Simple-Sticky-Notes`
- Support contact: `https://github.com/joshwhitk/Simple-Sticky-Notes/issues`
- Non-Microsoft drivers or NT services: `No`
- Tested to meet accessibility guidelines: leave unchecked unless accessibility validation is completed separately
- Supports pen and ink input: `No`

### Packages

- App type: `EXE`
- Architecture: `x64`
- Language: `en-US`
- Package URL: `https://github.com/joshwhitk/Simple-Sticky-Notes/releases/download/v1.0.1/Simple-Sticky-Notes-Setup.exe`
- Silent install parameters: `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-`

Package notes:

- the Store `EXE/MSI` flow requires a stable direct package URL with no redirect
- do not replace the file at an existing version URL after submission
- publish a new release asset for each update
- GitHub Releases do not currently satisfy the direct-URL requirement for this field
- host the installer on your own origin or CDN with a non-redirecting HTTPS download URL

### Store Listing

Use the text in [STORE_LISTING_DRAFT.md](STORE_LISTING_DRAFT.md).

### Certification Notes

Use something close to this in the certification notes field:

> Simple Sticky Notes is a standalone Windows desktop sticky-note app. It stores note bodies as normal markdown files and stores window state in local sidecar metadata. Users typically keep the storage root inside an Obsidian vault, but the app can also use another local folder. The installer is offline and supports silent install. The app does not install drivers or Windows services. Uninstall removes the app but is intended to leave user note files in their chosen storage folder untouched.

## Required Public URLs

Before submission, make sure these are publicly reachable:

- privacy policy URL
- support URL
- website URL
- direct non-redirecting installer URL

GitHub is acceptable for the website and support links. The privacy policy also needs a public URL, but it should be presented as a stable human-readable policy page rather than only as a local repo file.

## Screenshot And Art Requirements

Use [STORE_ASSETS_CHECKLIST.md](STORE_ASSETS_CHECKLIST.md).

Current Microsoft listing requirements relevant to this app:

- at least one screenshot is required
- four or more screenshots are recommended
- desktop screenshots must be PNG and at least `1366 x 768`
- one `1:1` box-art image is required
- `2:3` poster art is recommended

## Submission Checklist

- reserve `Simple Sticky Notes` as an `EXE/MSI` product
- host the installer at a direct non-redirecting HTTPS URL
- host the privacy policy at a public URL
- prepare at least four desktop screenshots
- prepare required store logo and 1:1 box art
- fill the listing from [STORE_LISTING_DRAFT.md](STORE_LISTING_DRAFT.md)
- add certification notes describing local markdown storage and uninstall behavior
- submit the package for certification

## Microsoft Source Notes

This plan follows Microsoft guidance current on `2026-04-22`:

- Microsoft says the Store supports both `MSIX` and traditional `EXE/MSI` submissions, and that `MSIX` is recommended in general while `EXE/MSI` remains supported for traditional desktop installers.
- For `EXE/MSI` submissions, Microsoft requires a package URL, installer parameters for silent install, and listing metadata such as description, screenshots, logos, and applicable license terms.
- Microsoft also requires the `EXE/MSI` package URL to be a direct secure download URL, not a redirecting link.
- Microsoft says a listing needs at least one screenshot, while four or more are recommended.
- Microsoft says `broadFileSystemAccess` is a restricted capability for packaged apps and requires additional explanation if used in a Store submission. That is one reason this first plan stays with the current `EXE` installer rather than adding `MSIX` work first.

## Current Status

As of `2026-04-23`:

- the first product has been created in Microsoft Partner Center
- the first Store submission has been sent for review
- Partner Center ID: `78b96f9d-3b84-447d-93c2-50fe1a3e52a6`
- reported review estimate: about `3` days

Official references:

- [Submit your app to Microsoft Store](https://learn.microsoft.com/en-us/windows/apps/publish/faq/submit-your-app)
- [Create an app submission for your MSI/EXE app](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msi/create-app-submission)
- [Add and edit Store listing info for MSIX app](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/add-and-edit-store-listing-info)
- [App screenshots, images, and trailers for MSIX app](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/screenshots-and-images)
- [File access permissions](https://learn.microsoft.com/en-us/windows/apps/develop/files/file-access-permissions)
