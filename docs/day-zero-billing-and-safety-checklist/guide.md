# Day Zero Billing and Safety Checklist

Meta Model API currently has inmature Billing and API Key safegaurds.

https://dev.meta.ai/

## Problem 1 - The Billing Safeguard Problem

For Meta Model API even if you get free credits you must attach a credit card for either:
- Pay as You Go (PAYG) via API Key
- or Subscription.

### Other Providers Method - Prepay Billing
Other providers like Google, Anthropic and OpenAI use PrePay Billing.
This means you load up an amount and it spends to zero.
So you avoid a runway bill.

### Meta Billing Method - Pay As You Go (PAYG)
Meta Model API uses PAYG also known as On-Demand billing.
You are charged for what you use. Similar to Cloud Service Providers (CSPS) eg. AWS, Google Cloud, Microsoft Azure.

Without proper billing safeguards and practices you can end up with an expensive bill.
And Meta does not have the same kind of Customer Support if you are overbilled like AWS.

So there may be no forgivement, so you don't want to mess this up.

https://dev.meta.ai/help/billing/spend-limit-alert

> Meta Model API doesn't currently offer a spending limit that places a hard cap on usage. You can, however, set a monthly spend limit alert to receive an email when your usage costs reach an amount you choose.

### Spending Limits Does Not Limit

Meta has a Spending Limits feature in the https://dev.meta.ai/billing but it does not actually "limit" spend.

What it does do is allow you to set an Email Notification when your monthly spend reaches a specific amount.
You can only set a single notification for the entire month.

So to clarify there is no hard guardrail against runway spend.

## Problem 2 - The Long Lived Key Problem

A long-lived API key is a API key that never expires. 

## Other Providers API Key Expiry

Other first-party AI providers have the option for TTL (Time to Live).
So when you create the key you set a fixed duration per key when it will expire eg. 24 hours, 2, days, 30 days.

## Meta's API Key Expiry Problem

Meta does not currently have a feature to set an expiry date for an API key
So your keys are always long-lived.

This is compounded with the lack of other API Key features.

## Meta's API Key Deletion Problem

Meta will not let you delete all keys. You must always have a single key in your account.
You can delete all keys but you would first have to make another key to delete an the last remaining on.

https://dev.meta.ai/help/api-keys/delete-api-key

> Your team must have at least two API keys to delete one — you can't delete your last remaining key.

There is also no options to simply "deactivate" a key, so you can't just deactivate the remaining key.