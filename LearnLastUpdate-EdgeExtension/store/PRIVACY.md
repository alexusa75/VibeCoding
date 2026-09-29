# Privacy policy: Learn Last Update (Microsoft Edge extension)

_Last updated: September 28, 2026_

Learn Last Update shows when the Microsoft Learn page you're viewing was last updated and who its technical writer is. This policy explains what the extension reads, stores and sends.

## What it reads

The extension runs only on `learn.microsoft.com` and `review.learn.microsoft.com`. On those pages it reads metadata that the page already publishes: the update dates, the writer's GitHub username and Microsoft alias, the reviewer and the source-repository links. This happens inside your browser.

The extension doesn't read other websites, your browsing history, form fields, or anything you type.

## What it stores

- **Your two settings** (*Card on page* and *GitHub lookups*) are kept in Microsoft Edge's extension storage. Edge syncs them across your devices if you use Edge sync.
- **A cache of GitHub lookup results** is kept in local extension storage: writer display names for 7 days, the latest commit for 6 hours, and "not found" results for 1 day. This cache keeps the extension within GitHub's rate limits.
- **Hiding the card** with × on a page is remembered in that tab's session storage until you close the tab.

Removing the extension deletes everything it stored.

## What it sends

The extension doesn't collect, sell or share any data about you. The developer runs no server and receives no data from the extension. There's no analytics, telemetry or advertising.

When **GitHub lookups** is on (the default), the extension contacts GitHub:

- It calls GitHub's public API (`api.github.com`) with the writer's public GitHub username and the article's public source-file path. This returns the writer's display name and the latest commit.
- It loads the writer's public avatar image from `github.com`.

As with any web request, GitHub receives your IP address and standard browser headers. See the [GitHub General Privacy Statement](https://docs.github.com/site-policy/privacy-policies/github-general-privacy-statement).

Turn off **GitHub lookups** in the extension's popup and the extension makes no requests to GitHub at all.

## Your choices

- Turn **GitHub lookups** off in the popup to stop all requests to GitHub.
- Turn **Card on page** off to stop the card from appearing on Learn pages.
- Remove the extension in `edge://extensions` to stop it entirely and delete its stored data.

## Changes and contact

If the extension's data practices change, this policy will be updated and the date above will change. For questions, use the support contact on the extension's Microsoft Edge Add-ons listing.
