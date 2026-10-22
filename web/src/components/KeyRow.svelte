<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import { saveSettings, testKey, type KeyTest, type ServiceKeys } from "../lib/settings.svelte";

  // A service and its keys: whether they are set, a field to change them,
  // and a test. A key never comes back from the server.
  let { service, onerror }: { service: ServiceKeys; onerror: (error: unknown) => void } = $props();

  let typed = $state<Record<string, string>>({});
  let test = $state<KeyTest["status"] | "testing" | null>(null);

  const set = $derived(service.keys.every((key) => key.set));
  const locked = $derived(service.keys.some((key) => key.locked));

  async function save(key: string, value: string) {
    try {
      await saveSettings({ keys: { [key]: value } });
      typed[key] = "";
      test = null;
    } catch (error) {
      onerror(error);
    }
  }

  async function runTest() {
    test = "testing";
    try {
      test = (await testKey(service.service)).status;
    } catch (error) {
      test = null;
      onerror(error);
    }
  }

  function testText(status: KeyTest["status"]): string {
    switch (status) {
      case "ok":
        return t("operational", "Operational");
      case "wrong_key":
        return t("invalid_key", "Invalid key");
      case "missing_key":
        return t("no_key_configured", "No key configured");
      case "rate_limited":
        return t("web_key_rate_limited", "Quota used: try again later");
      case "service_error":
        return t("web_key_service_error", "The service answered with an error");
      case "unreachable":
        return t("web_key_unreachable", "The service cannot be reached");
      case "unsupported":
        return t("web_key_unsupported", "This key cannot be tested");
    }
  }
</script>

<div class="flex flex-col gap-2 px-4 py-3">
  <div class="flex items-start justify-between gap-4">
    <div class="min-w-0">
      <p class="text-sm font-semibold">{service.name}</p>
      <p class="text-xs text-muted">
        {t(`api_desc_${service.service}`, "")}
        {#if service.url && !locked}
          · <a
            class="text-accent hover:underline"
            href={service.url}
            target="_blank"
            rel="noreferrer">{t("web_get_key", "Get a key")}</a
          >
        {/if}
      </p>
    </div>
    <span
      class={[
        "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
        locked ? "bg-hover text-muted" : set ? "bg-ok/15 text-ok" : "bg-hover text-muted",
      ]}
    >
      {#if locked}
        {t("web_key_locked", "Set by an environment variable")}
      {:else if set}
        {t("key_configured", "Key configured")}
      {:else}
        {t("no_key_configured", "No key configured")}
      {/if}
    </span>
  </div>

  {#if !locked}
    {#each service.keys as field (field.key)}
      <form
        class="flex gap-2"
        onsubmit={(event) => {
          event.preventDefault();
          if (typed[field.key]?.trim()) save(field.key, typed[field.key]);
        }}
      >
        <input
          class="field font-mono text-xs"
          type="password"
          autocomplete="off"
          bind:value={typed[field.key]}
          aria-label={`${service.name} ${field.key}`}
          placeholder={field.key.includes("secret")
            ? t("web_secret_placeholder", "Secret…")
            : field.set
              ? t("web_key_replace", "New key, to replace the current one…")
              : t("your_api_key", "Your API key...")}
        />
        <button class="button shrink-0" disabled={!typed[field.key]?.trim()}>
          {t("web_save", "Save")}
        </button>
        {#if field.set}
          <button
            type="button"
            class="shrink-0 rounded-lg px-3 text-sm font-medium text-muted hover:bg-hover hover:text-error"
            onclick={() => save(field.key, "")}
          >
            {t("web_remove", "Remove")}
          </button>
        {/if}
      </form>
    {/each}
  {/if}

  <div class="flex items-center gap-3">
    <button
      type="button"
      class="rounded-lg border border-line px-3 py-1 text-xs font-semibold hover:bg-hover disabled:opacity-50"
      disabled={test === "testing"}
      onclick={runTest}
    >
      {test === "testing" ? t("testing", "Testing...") : t("test", "Test")}
    </button>
    {#if test && test !== "testing"}
      <span class={["text-xs", test === "ok" ? "text-ok" : "text-error"]} role="status">
        {testText(test)}
      </span>
    {/if}
  </div>
</div>
