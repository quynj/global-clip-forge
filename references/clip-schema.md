# Clip Schema

`selected_clips.json` should be an array of objects with this shape:

```json
[
  {
    "id": "clip-01",
    "start": "00:12:03,000",
    "end": "00:13:22,500",
    "start_seconds": 723.0,
    "end_seconds": 802.5,
    "duration_seconds": 79.5,
    "title": "A working title in the target audience language",
    "summary": [
      "Sentence one explains what the clip is about.",
      "Sentence two explains why it is worth cutting out."
    ],
    "reason": "Why this moment works as a short-form clip"
  }
]
```

Rules:

- `id` must be unique and stable.
- `title` should be written in the target audience language.
- `summary` must contain exactly two sentences.
- `summary` should follow the target audience language unless the caller explicitly wants another review language.
- Timestamps must describe a complete thought.
- Prefer `20` to `180` seconds per clip.
