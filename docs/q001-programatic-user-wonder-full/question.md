---
question:  Is it possible to use Meta Wonder Full Programmatically?
date: 2026-10-23
status:  verified
scope:
  - meta-wonder-full-1.0
  - muse-code-headless
  - muse-sdk
---

There is a single-shot on X.com that claims Meta Wonder Full 1.0 at the time does not preform well at 3d Graphics. I wanted to replicate the single-shot prompt against Meta Wonder Full 1.0 to verify the outcome for myself.

While I can use Meta Code in interactive mode directly and provide it the prompt, this will not capture latency, logs, token usage or output the results and its not a repetable experiment for others.

So I want to programmaticaly interact with Muse Code via SDK or headless CLI and build the additional layer to build a proper experiment.

I generated a script to perform singleshot, and the AI decided to use muse code exec (Headless mode) and was able to capture the logging details I wanted.

I had used the script on meta-wonder-1.0 and it worked, but when I used meta-wonder-full-.10 I encountered an error:

> model 'muse-wonder-full-1.0' does not exist or you lack access

Muse Wonder Full is restricted to paid subscribers to Power and Maximum Usage via Muse Code cannot be called via a cusstom backend API endpoint.

Even if you have a subscription, you cannot simply create create an API key and load it into Muse Code or the SDK, which my error confirms.

But can you use Meta Wonder Full in headless mode authenicated as a subscription via a script?

The anwser is yes. You can.

See my singleshot script extracted from my singleshot project: [./run_benchmark.py](./run_benchmark.py)

Here is a minimal example if you want to test subscription.

```sh
# login with your subscription
muse login
# use headless mode specifying the model
muse exec --json \
      --provider meta \
      --model muse-wonder-full-1.0 \
      --prompt "Say hi" \
      --workspace /tmp/demo \
      --disable-approval
```

## Conclusion

If you want to use Muse Wonder Full 1.0 programtically use `muse exec` within your codebase.
The enviroment that needs to execute your script will need to be logged in via the subscription.
This could pose issues in automated environments. It might be possible to preform `muse login` 
in a local envirnoment located where the session is stored, and copy and paste it to your target
automated enviroment. 


## New Questions

- Are Muse Code Sessions portable and do Muse Code Subscription Sessions expire?
  - Where is the Muse Code sessions store on the local machine?
  - Do Muse Code Subscriptions sessions ever expire?
  - Can you copy and paste the session file to another enviroment and will it simply work?
