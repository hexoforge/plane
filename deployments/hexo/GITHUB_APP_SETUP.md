# GitHub App setup for Plane (plane.hexoforge.dev)

Create at: GitHub > Settings (org hexoforge or your account) > Developer settings > GitHub Apps > New GitHub App.

## Basic

- GitHub App name: Hexoforge Plane (slug becomes e.g. `hexoforge-plane`, use it for GITHUB_APP_SLUG)
- Homepage URL: https://plane.hexoforge.dev
- Callback URL: leave empty (no user OAuth is used)
- Request user authorization (OAuth) during installation: unchecked
- Setup URL: https://plane.hexoforge.dev/api/integrations/github/setup/
- Redirect on update: checked
- Webhook: Active, checked
- Webhook URL: https://plane.hexoforge.dev/api/integrations/github/webhook/
- Webhook secret: generate a long random string (e.g. `openssl rand -hex 32`), use it for GITHUB_APP_WEBHOOK_SECRET
- SSL verification: enabled

## Repository permissions

- Contents: Read-only (branch names on PRs)
- Issues: Read and write (create comments, close and reopen issues)
- Pull requests: Read-only
- Metadata: Read-only (mandatory)

Organization and account permissions: none.

## Subscribe to events

- Issues
- Issue comment
- Pull request
- Installation target / Installation repositories are sent automatically (installation events always delivered)

## Where can this app be installed

- Only on this account (recommended)

## After creating

1. Note the App ID (GITHUB_APP_ID).
2. Generate a private key (.pem). Paste it into the env var GITHUB_APP_PRIVATE_KEY (full PEM; newlines can be literal `\n`).
3. Add to Dokploy compose env for plane (api, worker, beat-worker read it):
   GITHUB_APP_ID=...
   GITHUB_APP_SLUG=...
   GITHUB_APP_WEBHOOK_SECRET=...
   GITHUB_APP_PRIVATE_KEY=...
4. The compose already passes these to api, worker and beat-worker via x-app-env (empty means the feature is off).
5. In Plane: Workspace settings > Integrations > GitHub > Install GitHub App, choose repos, you return to Plane connected.
6. Project settings > GitHub: link repos, set state mapping (PR opened, PR merged, issue closed, issue reopened).
7. Test: open a PR with branch `PROJ-12-something`; it should appear on the work item and move it to the mapped state.
