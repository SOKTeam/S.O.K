---
title: Translations
description:
  Translate interface text with tr() and keep the eight language files in sync.
---

S.O.K is translated into English, French, German, Spanish, Italian, Portuguese,
Russian and Polish. Every text shown to the user goes through `tr()`.

## Translate a text

```python
from sok.ui.i18n import tr

label = tr("drive_monitors", "Drive Monitors")
```

The first argument is the key, the second the English text used when the key is
missing from the current language file. Always give it, so the interface never
shows a raw key.

The language also sets the words used in folder names (`Season`, `Saison`,
`Staffel`…), so check the organize preview after adding such a key.

## Add a key

The translations are JSON files in `src/sok/resources/i18n/`, one per language
(`en.json`, `fr.json`, `de.json`, `es.json`, `it.json`, `pt.json`, `ru.json`,
`pl.json`). Add the new key to **every** file:

```json title="src/sok/resources/i18n/fr.json"
{
  "drive_monitors": "Moniteurs de disques"
}
```

Then run the check:

```sh
uv run python tools/verify_i18n.py
```

It finds every `tr("key", …)` call in `src/` and reports, for each language, the
keys missing from the file and the keys no longer used. It fails when a key is
missing, and the CI runs it on every pull request.

:::note
The check reads the key from the source code, so it only sees keys
written as plain strings: `tr("key", …)`, not `tr(variable, …)`.
:::
