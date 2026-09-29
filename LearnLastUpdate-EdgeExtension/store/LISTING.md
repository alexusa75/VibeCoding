# Microsoft Edge Add-ons submission: Learn Last Update

Everything you need to publish the extension to the [Microsoft Edge Add-ons](https://microsoftedge.microsoft.com) website and share it with your team. Each section below matches a page in Partner Center; paste the text as is.

## Files in this folder

| File | Partner Center field |
| --- | --- |
| `learn-last-update-1.0.0.zip` | **Packages** → upload |
| `logo-300.png` | **Store listings** → Extension logo (required) |
| `tile-small-440x280.png` | Small promotional tile (optional) |
| `tile-large-1400x560.png` | Large promotional tile (optional) |
| `screenshot-1-article-and-popup.png` … `screenshot-4-popup.png` | Screenshots, 1280 × 800 (optional, up to 6) |
| `PRIVACY.md` | Privacy policy text, if you choose to host one (see Privacy below) |

Rebuild the zip after any code change with `python tools\package.py`. Regenerate the images with `python tools\make_store_assets.py`.

## Step by step

1. **Developer account.** Sign in to [Partner Center for Microsoft Edge](https://partner.microsoft.com/dashboard/microsoftedge/public/login?ref=dd) and register for the Microsoft Edge program. Registration is free. Use an account you'll keep, because the extension stays tied to it.
2. **Create new extension.** Drag `learn-last-update-1.0.0.zip` onto **Upload package**, wait for validation, then select **Continue**.
3. **Availability.**
   - Visibility: **Hidden**. The extension won't appear in search or browsing, and only people with the listing link can install it. Choose **Public** instead if you want anyone to find it.
   - Markets: leave the default (all markets).
4. **Properties.** Category **Productivity**. Website and Support contact are optional; the support contact is shown to users. You can use the GitHub page as the website: `https://github.com/alexusa75/VibeCoding/tree/master/LearnLastUpdate-EdgeExtension`. Mature content: leave unchecked.
5. **Privacy.** Fill it in from the [Privacy](#privacy) section below.
6. **Store listings → English → Edit details.** Add the description, logo, tiles, screenshots and search terms from [Store listing](#store-listing), then select **Save draft**.
7. **Publish.** Paste the [Notes for certification](#notes-for-certification), then select **Publish**. Certification can take up to 7 business days.
8. **Share.** When the status changes to **In the Store**, copy the listing URL from the **Extension overview** page. It looks like `https://microsoftedge.microsoft.com/addons/detail/<extension-id>`. Send that link to your team.

## Store listing

**Extension name** (from the manifest, read-only): `Learn Last Update`

**Short description** (from the manifest, read-only): Shows when the Microsoft Learn article you're reading was last updated and who the technical writer is.

**Description**

```text
See at a glance when the Microsoft Learn page you're reading was last updated, and who wrote it.

Learn Last Update adds a small index card under the title of every Learn article, training module, and API or PowerShell reference page, in any language:
• Last updated: the same date Learn shows at the bottom of the page, with how long ago that was.
• Freshness stamp: Fresh (up to 6 months), Aging (up to a year) or Stale (older).
• Republished hint: shown when Learn published the page well after that date, so the content may have changed without a new date.
• Technical writer: GitHub name and avatar, with a link to the article's commit history.

The toolbar icon shows the page's age (for example 4mo or 2y) in the same colors. Click it for the full record:
• Last updated, the writer's review date (ms.date) and the last publish time (updated_at)
• Latest commit and build commit, with links to the source and history on GitHub
• The writer's GitHub profile and Microsoft alias, with Email and Teams chat shortcuts, plus the manager and reviewer
• Copy, for a ready-to-paste summary

Everything comes from metadata that Learn already publishes in each page. The extension collects nothing and has no analytics. Its only network requests are optional lookups of the writer's public GitHub name, avatar and latest public commit, which you can turn off in the popup.

Works on learn.microsoft.com and review.learn.microsoft.com, and follows Learn's light, dark and high-contrast themes.

Learn Last Update is an independent tool and isn't an official Microsoft Learn feature.
```

**Search terms** (7 terms, 13 words; the limits are 7 terms and 21 words):

```text
Microsoft Learn
last updated
documentation freshness
technical writer
docs author
article age
ms.date
```

**Images:** extension logo `logo-300.png`, small tile `tile-small-440x280.png`, large tile `tile-large-1400x560.png`, and screenshots 1 to 4 in order.

## Privacy

**Single purpose description**

```text
Shows when the Microsoft Learn page the user is viewing was last updated and who its technical writer is, in a card under the page title, a badge on the toolbar icon and a popup.
```

**Permission justification**

| Permission | Justification |
| --- | --- |
| `storage` | Saves the user's two settings (show the card on pages; allow GitHub lookups) and caches GitHub lookup results (writer display names for 7 days, latest commit for 6 hours) so the extension stays within GitHub's anonymous rate limit. |
| `scripting` | When the popup opens on a Learn tab that was already open before the extension was installed or updated, it injects the extension's own packaged content scripts (src/core.js, src/card-styles.js, src/content.js) into that tab to read the page's metadata. No remote or dynamically built code is injected. |
| `https://learn.microsoft.com/*` | The content script reads the article's published metadata (meta tags such as ms.date, updated_at, author and ms.author, and the date Learn displays) and shows the last-updated card under the title. |
| `https://review.learn.microsoft.com/*` | The same as learn.microsoft.com, for Learn's review site, where Microsoft writers and reviewers check articles before publication. |
| `https://api.github.com/*` | Optional, and can be turned off in the popup. Looks up the writer's public GitHub display name and the latest public commit for the article's source file. Only public article metadata is sent (a GitHub username and a repository path); no user data is sent. |

If Partner Center shows a single box for all host permissions, paste this:

```text
learn.microsoft.com and review.learn.microsoft.com: the content script reads each article's published metadata (ms.date, updated_at, author, ms.author, and the date Learn displays) and shows the last-updated card under the title. review.learn.microsoft.com is Learn's review site for Microsoft writers. api.github.com: optional (can be turned off in the popup) lookups of the writer's public GitHub display name and the latest public commit for the article's source file; only a public GitHub username and repository path are sent, never user data.
```

**Are you using remote code?** Select **No, I am not using remote code**. All code is packaged, and the extension uses Manifest V3.

**Data usage**

- *What user data do you plan to collect?* Leave every data type unchecked. The extension reads page metadata only inside the browser, and sends only public article metadata to GitHub. It collects nothing about the user.
- *I certify that the following disclosures are true.* Select all of the certification checkboxes.

**Privacy policy URL.** A policy is required only when an extension collects personal information, and this one doesn't. You can still add one for transparency. `PRIVACY.md` is already public in the repository, so paste `https://github.com/alexusa75/VibeCoding/blob/master/LearnLastUpdate-EdgeExtension/store/PRIVACY.md`.

## Notes for certification

```text
No account or sign-in is needed.

Test pages (dates depend on the current article):
1. https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-add-other-agents
   Expected: a card under the title with the last-updated date, a freshness stamp, the writer (Gary Pretty) and a "Republished" line. The toolbar icon badge shows the page's age. Click the icon to open the popup with the full record.
2. https://learn.microsoft.com/en-us/powershell/module/exchange/get-mailbox
   Expected: an orange STALE card (last updated in 2017).
3. https://learn.microsoft.com/en-us/training/modules/intro-to-azure-fundamentals/
   Expected: the card also works on training modules.
4. https://learn.microsoft.com/en-us/search/?terms=intune
   Expected: no card and no badge, because this isn't an article. The popup explains why.
5. Any non-Learn site
   Expected: the popup shows "Not a Learn article".

Popup settings: "Card on page" hides or shows the card. "GitHub lookups" stops all requests to GitHub (the writer's name, avatar and latest commit). The × on a card hides it on that page for the rest of the session.

review.learn.microsoft.com requires Microsoft sign-in; the extension behaves the same there as on learn.microsoft.com.
```

## Sharing with your team

- **Link install.** Teammates open the listing link in Edge, then select **Get** → **Add extension**. Edge updates the extension automatically whenever you publish a new version.
- **If you already loaded the unpacked copy,** remove it in `edge://extensions` after installing from the store. The store version has a different extension ID, so you'd otherwise see two cards.
- **Managed rollout (optional).** An IT admin can install it for a group through Intune or Group Policy with the Microsoft Edge policy *Control which extensions are installed silently* (`ExtensionInstallForcelist`). The value is `<extension-id>;https://edge.microsoft.com/extensionwebstorebase/v1/crx`.

## Publishing an update

1. Increase `version` in `manifest.json` (for example `1.0.1`). The store rejects a package whose version isn't higher than the live one.
2. Run `python tools\package.py` to build `store\learn-last-update-<version>.zip`.
3. In Partner Center, open the extension → **Packages** → upload the new zip → **Publish**. Summarize what changed in the notes for certification.
4. If the UI changed, run `python tools\make_store_assets.py` and replace the screenshots.
