## Meta AI Developer Community Field Notes

The Unofficial and Independently maintained field notes to help people working with Meta AI APIs.

The goal is to provide community-driven experiments, examples, discoveries, and documentation gaps across Meta's developer APIs and features. 

![./assets/Jolly-Field-Notes.png](./assets/Jolly-Field-Notes.png)

## Before You Build

Before you start building there are features lacking around billing and safety
that could cause you to have a very bad day. 

Make sure you complete this guide before you dare start building:

- [Day Zero Billing and Safety Checklist](./docs/day-zero-billing-and-safety-checklist/guide.md)

## Technical Exploration Questions

These are questions raised about technical features or 

- [Q001](./docs/q001-programatic-user-wonder-full/question.md) [verified] Is it possible to use Meta Wonder Full Programmatically?
- [Q002](./docs/q002-muse-code-sessions/question.md) [unexplored] Are Muse Code Sessions portable and do Muse Code Subscription Sessions expire?
- [Q003](./docs/q003-lawnmower-sim-engine-comparison/question.md) [unexplored] How do results change when the same one-shot prompt is built through different toolchains?

## Communtiy Tools

- [Meta Benchmark](https://github.com/danphillips-cloud/meta-benchmark) a way of measuring one-shots
- [Meta Cost Center](https://github.com/omenking/meta-costcenter) a way of tracking spend and token usage based on local machine logging, can also set your own more robust billing notifications.

## Meta Feature Requests

These are features I Think Meta Model API should consider adding.
Meta if you're reading, have at em:

### API Key Management

- add `set expiry` setting when creating an API key
  - discourage setting `no expiry` option and have them checkbox an aknowledement
- allow you to delete the last key
- allow you to deactivate/activate a key
- for spending limits actually add a limit where spend stops:
  - at the key level
  - at the account level
- for spending notification add the ability to add multiple notifications for the month
  - allow you to specify a percentage from your spending limit