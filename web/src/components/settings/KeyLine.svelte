<script lang="ts">
  import Line from "./Line.svelte";
  import OpenBox from "./OpenBox.svelte";
  import { t } from "../../lib/i18n.svelte";
  import { saveSettings, testKey, type KeyTest, type ServiceKeys } from "../../lib/settings.svelte";

  // A service that takes a key, as a line of the Sources block: the state of
  // its key at the right; the line opens on its fields, Save, Test and
  // Remove. A key never comes back from the server.
  let {
    service,
    open,
    ontoggle,
    onerror,
  }: {
    service: ServiceKeys;
    open: boolean;
    ontoggle: () => void;
    onerror: (error: unknown) => void;
  } = $props();

  let typed = $state<Record<string, string>>({});
  let test = $state<KeyTest["status"] | "testing" | null>(null);
  let busy = $state(false);

  const set = $derived(service.keys.every((key) => key.set));
  const locked = $derived(service.keys.some((key) => key.locked));
  const anyTyped = $derived(service.keys.some((key) => typed[key.key]?.trim()));

  async function save() {
    const keys = Object.fromEntries(
      service.keys
        .filter((key) => typed[key.key]?.trim())
        .map((key) => [key.key, typed[key.key].trim()]),
    );
    busy = true;
    try {
      await saveSettings({ keys });
      typed = {};
      test = null;
    } catch (error) {
      onerror(error);
    } finally {
      busy = false;
    }
  }

  async function remove() {
    busy = true;
    try {
      await saveSettings({ keys: Object.fromEntries(service.keys.map((key) => [key.key, ""])) });
      test = null;
    } catch (error) {
      onerror(error);
    } finally {
      busy = false;
    }
  }

  async function runTest() {
    test = "testing";
    try {
      const [key, secret] = service.keys.map((field) => typed[field.key]?.trim());
      test = (await testKey(service.service, key, secret)).status;
    } catch (error) {
      test = null;
      onerror(error);
    }
  }

  function testText(status: KeyTest["status"]): string {
    switch (status) {
      case "ok":
        return t("web_key_works", "Works");
      case "wrong_key":
        return t("web_key_refused", "Key refused");
      case "missing_key":
        return t("web_key_to_set", "To set up");
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

  const shown = $derived.by((): { value: string; tone: "muted" | "caution" } => {
    if (test && test !== "testing") {
      return { value: testText(test), tone: test === "ok" ? "muted" : "caution" };
    }
    if (locked)
      return { value: t("web_key_locked", "Set by an environment variable"), tone: "muted" };
    if (set) return { value: t("key_configured", "Key configured"), tone: "muted" };
    return { value: t("web_key_to_set", "To set up"), tone: "caution" };
  });
</script>

<Line label={service.name} value={shown.value} tone={shown.tone} {open} onclick={ontoggle} />
{#if open}
  <OpenBox text={t(`api_desc_${service.service}`, "")}>
    {#if locked}
      <p class="text-[13px] leading-[1.5] text-muted">
        {t(
          "web_key_locked_text",
          "An environment variable of the container gives this key: change it there.",
        )}
      </p>
    {:else}
      <form
        class="grid gap-2"
        onsubmit={(event) => {
          event.preventDefault();
          if (anyTyped) save();
        }}
      >
        {#each service.keys as field (field.key)}
          <input
            class="field h-[38px] font-mono text-[13px]"
            type="password"
            autocomplete="off"
            bind:value={typed[field.key]}
            aria-label={`${service.name} ${field.key}`}
            placeholder={field.key.includes("secret")
              ? t("web_secret_placeholder", "Secret…")
              : field.set
                ? t("web_key_replace", "New key, to replace the current one…")
                : t("web_your_key", "Your API key…")}
          />
        {/each}
        <button type="submit" class="hidden" aria-hidden="true" tabindex="-1"></button>
      </form>
    {/if}
    <div class="mt-2.5 flex flex-wrap items-center gap-2">
      {#if !locked}
        <button type="button" class="key key-sm" disabled={!anyTyped || busy} onclick={save}>
          {t("web_save", "Save")}
        </button>
      {/if}
      <button type="button" class="key key-sm" disabled={test === "testing"} onclick={runTest}>
        {test === "testing" ? t("testing", "Testing...") : t("test", "Test")}
      </button>
      <span class="ml-auto flex items-center gap-4 text-[13px]">
        {#if set && !locked}
          <button
            type="button"
            class="cursor-pointer text-muted hover:text-danger"
            disabled={busy}
            onclick={remove}
          >
            {t("web_remove", "Remove")}
          </button>
        {/if}
        {#if service.url && !locked}
          <a
            class="font-medium text-accent-text hover:text-ink"
            href={service.url}
            target="_blank"
            rel="noreferrer"
          >
            {t("web_get_key", "Get a key")} ↗
          </a>
        {/if}
      </span>
    </div>
  </OpenBox>
{/if}
