# Meta Model API Basic Safety

- [ ] MFA and a backup method are configured.
- [ ] Spending notification is enabled.
- [ ] Test Spending notifcation is one cent threshold
- [ ] Explore Usage tabs and export a cost usage report
- [ ] Install and Use Muse CostCenter
- [ ] Install and Use Muse Keyguard

## 1. Secure Your Account with MFA

1. Sign in at https://dev.meta.ai/.
2. Open your account menu → Account.
3. Click on Account Center
4. Under Security, select Account Password and Security.
5. Open Set up two-factor authentication.
6. Configure an authenticator app or security key.
7. Add a backup authentication method.

## 2. Configure your spending notification

1. Open Billing in the Meta developer dashboard.
2. Locate Spend Limits.
3. Set a monthly notification threshold that suits your testing budget.
4. Save the setting.
5. Confirm your billing email address is monitored.

### Test Spend Notification Works

You can set the spend notification down to `$0.01`
Then use the API with some spend until you pass that one cent threshold.
See if you get an email.

## 3. Explore Usage Tab

1. Open Usage Tab
2. Notice you can filter usage based on all or a specific API key
3. Notice you can filter usage based on all models or a specific model
4. Notice you can download change the date range
5. Notice beside the date range the download button to export cost usage CSV file.
6. Notice the warning at the bottom of the page "Usage metrics are in limited availability. Any discrepancies will be resolved via credit adjustment."

## 4. Install and Use Muse CostCenter

[Muse Cost Monitor Guide](./2_muse_cost_monitor.md)

This is an unoffical community tool to help keep track in-realtime of your local spend. Its limited to your local machine and cannot track spend across multiple machines.

##  5. Install and Use Muse Keyguard

[Muse Keyguard Guide](./3_muse_keyguard.md)

This is an unoffical community tool to help keep centralize and manage your Muse API keys. It limited to your local machine and cannot manage API keys across multiple machines.