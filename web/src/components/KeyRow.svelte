<script lang="ts">
  import { SERVICE_COLUMNS } from "../lib/columns";
  import { t } from "../lib/i18n.svelte";
  import { saveSettings, testKey, type KeyTest, type ServiceKeys } from "../lib/settings.svelte";

  // A service and its keys, as a row of the keys table: whether they are
  // set, fields to change them, and a test. A key never comes back from the
  // server.
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

<div class={[SERVICE_COLUMNS, "border-b border-line py-3 text-sm last:border-0"]}>
  <div class="min-w-0">
    <p class="font-medium">{service.name}</p>
    {#if t(`api_desc_${service.service}`, "")}
      <p class="mt-0.5 text-xs text-muted">{t(`api_desc_${service.service}`, "")}</p>
    {/if}
  </div>
  <div class="flex min-w-0 flex-col gap-1.5">
    {#if locked}
      <p class="text-muted">{t("web_key_locked", "Set by an environment variable")}</p>
    {:else}
      {#each service.keys as field (field.key)}
        <form
          class="flex items-center gap-3"
          onsubmit={(event) => {
            event.preventDefault();
            if (typed[field.key]?.trim()) save(field.key, typed[field.key]);
          }}
        >
          <input
            class="field max-w-xs py-1.5 font-mono text-xs"
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
          {#if typed[field.key]?.trim()}
            <button class="link">{t("web_save", "Save")}</button>
          {:else if field.set}
            <button
              type="button"
              class="text-sm text-muted hover:text-error"
              onclick={() => save(field.key, "")}
            >
              {t("web_remove", "Remove")}
            </button>
          {/if}
        </form>
      {/each}
    {/if}
  </div>
  <div class="min-w-0">
    {#if test && test !== "testing"}
      <p class={test === "ok" ? "" : "text-error"} role="status">{testText(test)}</p>
    {:else}
      <p class={set ? "" : "text-muted"}>
        {set ? t("key_configured", "Key configured") : t("no_key_configured", "No key configured")}
      </p>
    {/if}
  </div>
  <div class="flex flex-col items-end gap-1">
    <button
      type="button"
      class="button-outline px-3 py-1"
      disabled={test === "testing"}
      onclick={runTest}
    >
      {test === "testing" ? t("testing", "Testing...") : t("test", "Test")}
    </button>
    {#if service.url && !locked}
      <a class="link text-xs" href={service.url} target="_blank" rel="noreferrer">
        {t("web_get_key", "Get a key")}
      </a>
    {/if}
  </div>
</div>
