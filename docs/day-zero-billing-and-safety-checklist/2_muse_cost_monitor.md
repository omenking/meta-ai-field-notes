# Meta Cost Center

Track local Muse Code token usage and estimated API costs. Requires Linux or WSL (amd64 or arm64) and a browser. No API key is needed.

## 0. Create a test project

```bash
mkdir -p ~/Projects/day-zero-test
cd ~/Projects/day-zero-test
```

Use this folder for every Muse session in both guides. Cost Center uses the workspace folder name, `day-zero-test`, as the project label. This is a local usage group; creating a folder does not restrict an API key's permissions.

## 1. Install

Run in Linux or WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/omenking/meta-costcenter/main/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
meta-cost doctor
```

Add the `export PATH` line to your shell startup file if that directory is not already on your PATH.

## 2. Open the dashboard

```bash
meta-cost show
```

Open the printed URL (normally `http://127.0.0.1:8765/`). On WSL, paste it into your Windows browser if needed. Allow a few seconds for the first import.

- **Overview:** review estimated spend and tokens.
- **Sessions / Projects:** find what used them.
- **Alerts:** set a daily, weekly, or monthly USD limit and warning percentages.

Leave the command running for live updates. Press Ctrl+C to stop.

## 3. Test a $0.01 spending alert

Start a Muse Code session from `~/Projects/day-zero-test` and run one small task so Cost Center can discover the project. This incurs usage charges. Then open **Alerts**, create an alert, and set:

- **Project:** `day-zero-test` (instead of all projects).
- **Period:** monthly.
- **Limit:** `$0.01` USD.
- **Warning:** `100%`.

Save the alert. Keep key revocation off until the Keyguard test below.

1. Keep the dashboard open on **Alerts**.
2. Run small Muse Code tasks from the same folder, then check `meta-cost month --project day-zero-test`.
3. If the estimated monthly cost is still below $0.01, repeat with another small task. Stop once it exceeds $0.01; this test incurs usage charges.
4. Allow about 15 seconds for collection. Confirm the dashboard shows the alert at or above 100% and displays a spending alert banner.

If this project's imported monthly usage already exceeds $0.01, the alert should trigger immediately after collection; no additional usage is needed. Other projects do not count toward this alert. The budget covers the calendar month, not just usage since you created the alert.

For desktop notifications, allow browser notifications and keep the dashboard tab open.

**Pass:** the one-cent alert triggers. **This alone does not delete a key.** Complete the [Keyguard tests](./3_muse_keyguard.md#4-test-budget-triggered-key-deletion) to prove deletion works.

After testing, edit the alert on **Alerts** to use your intended budget and warning levels.

Costs are estimates from retained local Muse logs. Other machines and direct API calls are excluded; unpriced usage can understate totals. Check Meta's billing dashboard for actual charges.

[Full instructions and updates](https://github.com/omenking/meta-costcenter#readme)
