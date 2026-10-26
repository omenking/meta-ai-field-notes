# Meta Keyguard

Create expiring Meta API keys and revoke them when Cost Center limits are exceeded. Requires **WSL 2 with Windows interop** and **Windows Google Chrome 116+**, signed in at [dev.meta.ai](https://dev.meta.ai/).

## 0. Use the same test project

```bash
mkdir -p ~/Projects/day-zero-test
cd ~/Projects/day-zero-test
```

Use the same folder as the [Cost Center guide](./2_muse_cost_monitor.md). Dedicate the keys below to this project. Their labels and the alert's project filter connect the two tools; the folder does not make a key unusable elsewhere or create a project in Meta's dashboard.

## 1. Install

Run in WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/omenking/meta-keyguard/main/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
meta-keyguard install-bridge
```

Add the `export PATH` line to your shell startup file if needed.

In Windows Chrome:

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the extension folder printed by `install-bridge`.
4. Open `https://dev.meta.ai/` and sign in.

Check the connection in WSL:

```bash
meta-keyguard doctor
```

## 2. Create and use a key

```bash
meta-keyguard create day-zero-dev --ttl 2h
meta-keyguard exec day-zero-dev -- python app.py
```

Replace `python app.py` with your application's command. `exec` supplies `META_API_KEY` to that process. Avoid copying the secret into configuration files.

```bash
meta-keyguard status
meta-keyguard revoke day-zero-dev
```

`status` checks key lifetimes and failures; `revoke` deletes the key immediately.

## 3. Test TTL expiry and deletion

Keep Chrome open and dev.meta.ai signed in throughout both tests. Use a separate test key so expiry does not interrupt your normal work.

```bash
meta-keyguard create day-zero-ttl --ttl 15s
meta-keyguard list --all
```

1. Open the API keys page on dev.meta.ai. Confirm a key named `day-zero-ttl-kg...` exists.
2. Wait 15 seconds for expiry. The reaper runs once a minute, so allow up to another minute for automatic deletion (up to about 75 seconds total). Do not manually revoke it.
3. Refresh the API keys page and run:

```bash
meta-keyguard status
meta-keyguard list --history
meta-keyguard exec day-zero-ttl -- printenv META_API_KEY
```

**Pass:** `day-zero-ttl-kg...` is gone from Meta's API keys page, history shows it revoked, and `exec` refuses to supply the expired key. A local refusal alone does not prove deletion: check the dashboard too.

If the key remains, run `meta-keyguard doctor` and check for an overdue deletion in `status`.

## 4. Test budget-triggered key deletion

First complete the [Cost Center guide](./2_muse_cost_monitor.md), including its project-specific one-cent alert. Create a fresh key with a long enough TTL that this test proves the budget deleted it:

```bash
meta-keyguard create day-zero-budget --ttl 2h
```

In Cost Center's **Alerts** page, edit the existing alert for **project `day-zero-test`**, with a **monthly limit of $0.01**. Enable **Revoke Meta API keys when the limit is exceeded**, enter the exact key match `day-zero-budget`, and save. Then enable enforcement:

```bash
meta-keyguard cost-center on
meta-keyguard cost-center check
```

The project filter counts only `day-zero-test` usage; the key match deletes only `day-zero-budget`. If this project's monthly estimate already exceeds $0.01, enabling the check can delete the key immediately.

1. Run `meta-cost show` and open **Alerts**. Confirm the one-cent alert covers project `day-zero-test`, matches `day-zero-budget`, and is enforced.
2. If the project's monthly usage is not already over $0.01, start Muse Code from `~/Projects/day-zero-test` through `meta-keyguard exec day-zero-budget -- YOUR_MUSE_COMMAND` (replace `YOUR_MUSE_COMMAND` with your Muse Code launch command). Use API-key/PAYG mode so Muse uses the supplied `META_API_KEY`. Run small tasks until `meta-cost month --project day-zero-test` reports more than $0.01. Stop generating usage once the threshold is crossed.
3. Allow about 15 seconds for collection and up to another minute for Keyguard's automatic check. Do not manually revoke the key.
4. Check the result:

```bash
meta-cost alert status --json
meta-keyguard cost-center check
meta-keyguard list --history
meta-keyguard exec day-zero-budget -- printenv META_API_KEY
```

**Pass:** the project alert exceeds its limit, Cost Center's **Alerts** page reports Keyguard revoked `day-zero-budget`, and `exec` refuses to supply it. Refresh Meta's API keys page and confirm `day-zero-budget-kg...` is gone **before its two-hour TTL expires**. This proves budget-triggered deletion.

Keyguard may leave a sentinel key because Meta requires a team to retain one key. The named test key must still disappear.

After testing, edit the alert on **Alerts** to set your real budget and match the keys you use. Leave the Cost Center check on for enforcement.

**Keep Chrome open, the extension loaded, and dev.meta.ai signed in.** Expiry and spending checks run about once a minute. If Chrome is closed, the computer sleeps, or the session expires, deletion cannot happen until the connection returns. Cost Center only counts local Muse logs, and spending can exceed the threshold before revocation. This is not an account-wide hard spending cap.

After upgrading, rerun `meta-keyguard install-bridge`, reload the extension, and run `meta-keyguard doctor`.

[Full instructions and updates](https://github.com/omenking/meta-keyguard#readme)
