# Meta Keyguard

Create expiring Meta API keys and revoke them when Cost Center limits are exceeded. Requires **WSL 2 with Windows interop** and **Windows Google Chrome 116+**, signed in at [dev.meta.ai](https://dev.meta.ai/).

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
meta-keyguard create dev --ttl 2h
meta-keyguard exec dev -- python app.py
```

Replace `python app.py` with your application's command. `exec` supplies `META_API_KEY` to that process. Avoid copying the secret into configuration files.

```bash
meta-keyguard status
meta-keyguard revoke dev
```

`status` checks key lifetimes and failures; `revoke` deletes the key immediately.

## 3. Test TTL expiry and deletion

Keep Chrome open and dev.meta.ai signed in throughout both tests. Use a separate test key so expiry does not interrupt your normal work.

```bash
meta-keyguard create ttl-test --ttl 15s
meta-keyguard list --all
```

1. Open the API keys page on dev.meta.ai. Confirm a key named `ttl-test-kg...` exists.
2. Wait 15 seconds for expiry. The reaper runs once a minute, so allow up to another minute for automatic deletion (up to about 75 seconds total). Do not manually revoke it.
3. Refresh the API keys page and run:

```bash
meta-keyguard status
meta-keyguard list --history
meta-keyguard exec ttl-test -- printenv META_API_KEY
```

**Pass:** `ttl-test-kg...` is gone from Meta's API keys page, history shows it revoked, and `exec` refuses to supply the expired key. A local refusal alone does not prove deletion: check the dashboard too.

If the key remains, run `meta-keyguard doctor` and check for an overdue deletion in `status`.

## 4. Test budget-triggered key deletion

First [install Cost Center](./2_muse_cost_monitor.md). Create a fresh key with a long enough TTL that this test proves the budget deleted it:

```bash
meta-keyguard create budget-test --ttl 2h
meta-cost alert set --monthly-usd 0.01 --at 100 --revoke-keys 'budget-test'
meta-keyguard cost-center on
meta-keyguard cost-center check
```

The key match targets only `budget-test`. If this month's estimated usage already exceeds $0.01, enabling the check can delete it immediately.

1. Run `meta-cost show` and open **Alerts**. Confirm the one-cent alert matches `budget-test` and is enforced.
2. If monthly usage is not already over $0.01, run small Muse Code tasks on this machine until `meta-cost month` reports more than $0.01. Stop generating usage once the threshold is crossed.
3. Allow about 15 seconds for collection and up to another minute for Keyguard's automatic check. Do not manually revoke the key.
4. Check the result:

```bash
meta-cost alert status --json
meta-keyguard cost-center check
meta-keyguard list --history
meta-keyguard exec budget-test -- printenv META_API_KEY
```

**Pass:** the alert exceeds its limit, Cost Center's **Alerts** page reports Keyguard revoked `budget-test`, and `exec` refuses to supply it. Refresh Meta's API keys page and confirm `budget-test-kg...` is gone **before its two-hour TTL expires**. This proves budget-triggered deletion.

Keyguard may leave a sentinel key because Meta requires a team to retain one key. The named test key must still disappear.

After testing, edit the alert on **Alerts** to set your real budget and match the keys you use. Leave the Cost Center check on for enforcement.

**Keep Chrome open, the extension loaded, and dev.meta.ai signed in.** Expiry and spending checks run about once a minute. If Chrome is closed, the computer sleeps, or the session expires, deletion cannot happen until the connection returns. Cost Center only counts local Muse logs, and spending can exceed the threshold before revocation. This is not an account-wide hard spending cap.

After upgrading, rerun `meta-keyguard install-bridge`, reload the extension, and run `meta-keyguard doctor`.

[Full instructions and updates](https://github.com/omenking/meta-keyguard#readme)
