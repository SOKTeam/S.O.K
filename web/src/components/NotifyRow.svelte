<script lang="ts">
  import { t } from "../lib/i18n.svelte";
  import { saveSettings, testNotification, type NotificationTest } from "../lib/settings.svelte";

  // A target of the notifications: its fields, whether it is set, and a
  // test. A secret never comes back from the server; an address does.
  interface Field {
    key: string;
    secret: boolean;
    /** The address saved; nothing for a secret. */
    value?: string;
    set: boolean;
    example: string;
  }

  let {
    target,
    name,
    text,
    fields,
    set,
    onerror,
  }: {
    target: string;
    name: string;
    text: string;
    fields: Field[];
    set: boolean;
    onerror: (error: unknown) => void;
  } = $props();

  let typed = $state<Record<string, string>>({});
  let test = $state<NotificationTest | "testing" | null>(null);

  async function save(key: string, value: string) {
    try {
      await saveSettings({ notifications: { [key]: value } });
      // The field shows the saved address again, or nothing for a secret.
      delete typed[key];
      test = null;
    } catch (error) {
      onerror(error);
    }
  }

  async function runTest() {
    test = "testing";
    try {
      test = await testNotification(target);
    } catch (error) {
      test = null;
      onerror(error);
    }
  }

  function testText(result: NotificationTest): string {
    if (result.ok) return t("web_notify_ok", "Sent");
    if (result.error === "not_set") return t("web_notify_not_set", "Fill it in first.");
    return t("web_notify_failed", "Failed: {error}", { error: result.error ?? "" });
  }
</script>

<div class="flex flex-col gap-2 px-4 py-3">
  <div class="flex items-start justify-between gap-4">
    <div class="min-w-0">
      <p class="text-sm font-semibold">{name}</p>
      <p class="text-xs text-muted">{text}</p>
    </div>
    <span
      class={[
        "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium",
        set ? "bg-ok/15 text-ok" : "bg-hover text-muted",
      ]}
    >
      {set ? t("web_notify_set", "On") : t("web_notify_off", "Off")}
    </span>
  </div>

  {#each fields as field (field.key)}
    <form
      class="flex gap-2"
      onsubmit={(event) => {
        event.preventDefault();
        if (typed[field.key]?.trim()) save(field.key, typed[field.key]);
      }}
    >
      <input
        class="field font-mono text-xs"
        type={field.secret ? "password" : "url"}
        autocomplete="off"
        value={typed[field.key] ?? field.value ?? ""}
        oninput={(event) => (typed[field.key] = event.currentTarget.value)}
        aria-label={`${name} ${field.key}`}
        placeholder={field.secret && field.set
          ? t("web_notify_replace", "Saved: type a new one to replace it…")
          : field.example}
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

  {#if set}
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
        <span class={["text-xs", test.ok ? "text-ok" : "text-error"]} role="status">
          {testText(test)}
        </span>
      {/if}
    </div>
  {/if}
</div>
