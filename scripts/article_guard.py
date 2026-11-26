"""
Calls Claude for an article and makes sure the article is not cut off.

The old scripts used max_tokens=4096 (neetgov 1500). Long articles hit that cap
and were published ending mid-sentence. This helper:
  - raises the cap to 16,000 tokens,
  - if Claude still stops because of the cap, tries once more,
  - if it is cut off again, stops the run with an error (red run in GitHub)
    so a half article is never published.
"""
import sys

MAX_TOKENS = 16000


def create(client, **kwargs):
    kwargs["max_tokens"] = max(int(kwargs.get("max_tokens", 0)), MAX_TOKENS)
    for attempt in range(2):
        message = client.messages.create(**kwargs)
        if message.stop_reason != "max_tokens":
            return message
        print(f"Article was cut off at the length limit (attempt {attempt + 1}), retrying...")
    print("ERROR: article was cut off twice - not publishing a half article.")
    sys.exit(1)
