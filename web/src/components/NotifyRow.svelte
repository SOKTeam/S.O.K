<script lang="ts">
  import { SERVICE_COLUMNS } from "../lib/columns";
  import { t } from "../lib/i18n.svelte";
  import { saveSettings, testNotification, type NotificationTest } from "../lib/settings.svelte";

  // A target of the notifications, as a row of its table: its fields,
  // whether it is on, and a test. A secret never comes back from the
  // server; an address does.
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

<div class={[SERVICE_COLUMNS, "border-b border-line py-3 text-sm last:border-0"]}>
  <div class="min-w-0">
    <p class="font-medium">{name}</p>
    {#if fields.length}
      <p class="mt-0.5 text-xs text-muted">{text}</p>
    {/if}
  </div>
  <div class="flex min-w-0 flex-col gap-1.5">
    <!-- Without a field (the script), the text fills the column. -->
    {#if !fields.length}
      <p class="text-xs text-muted">{text}</p>
    {/if}
    {#each fields as field (field.key)}
      <form
        class="flex items-center gap-3"
        onsubmit={(event) => {
          event.preventDefault();
          if (typed[field.key]?.trim()) save(field.key, typed[field.key]);
        }}
      >
        <input
          class="field max-w-xs py-1.5 font-mono text-xs"
          type={field.secret ? "password" : "url"}
          autocomplete="off"
          value={typed[field.key] ?? field.value ?? ""}
          oninput={(event) => (typed[field.key] = event.currentTarget.value)}
          aria-label={`${name} ${field.key}`}
          placeholder={field.secret && field.set
            ? t("web_notify_replace", "Saved: type a new one to replace it…")
            : field.example}
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
  </div>
  <div class="min-w-0">
    <p class={set ? "" : "text-muted"}>
      {set ? t("web_notify_set", "On") : t("web_notify_off", "Off")}
    </p>
    {#if test && test !== "testing"}
      <p class={["mt-0.5 text-xs", test.ok ? "text-muted" : "text-error"]} role="status">
        {testText(test)}
      </p>
    {/if}
  </div>
  <div class="text-right">
    {#if set}
      <button
        type="button"
        class="button-outline px-3 py-1"
        disabled={test === "testing"}
        onclick={runTest}
      >
        {test === "testing" ? t("testing", "Testing...") : t("test", "Test")}
      </button>
    {/if}
  </div>
</div>
