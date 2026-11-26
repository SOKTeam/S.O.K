<script lang="ts">
  import Line from "./Line.svelte";
  import OpenBox from "./OpenBox.svelte";
  import { t } from "../../lib/i18n.svelte";
  import { saveSettings, testNotification, type NotificationTest } from "../../lib/settings.svelte";

  // A target of the notifications, as a line of its block: on or off at the
  // right; the line opens on its fields, Save, Test and Remove. A secret
  // never comes back from the server; an address does.
  export interface NotifyField {
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
    open,
    ontoggle,
    onerror,
  }: {
    target: string;
    name: string;
    text: string;
    fields: NotifyField[];
    set: boolean;
    open: boolean;
    ontoggle: () => void;
    onerror: (error: unknown) => void;
  } = $props();

  let typed = $state<Record<string, string>>({});
  let test = $state<NotificationTest | "testing" | null>(null);
  let busy = $state(false);

  const changed = $derived(
    fields.some((field) => field.key in typed && typed[field.key].trim() !== (field.value ?? "")),
  );

  async function save(values: Record<string, string>) {
    busy = true;
    try {
      await saveSettings({ notifications: values });
      // The fields show the saved address again, or nothing for a secret.
      typed = {};
      test = null;
    } catch (error) {
      onerror(error);
    } finally {
      busy = false;
    }
  }

  function saveTyped() {
    const values = Object.fromEntries(
      fields
        .filter((field) => field.key in typed)
        .map((field) => [field.key, typed[field.key].trim()]),
    );
    save(values);
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
    if (result.ok) return t("web_notify_ok", "Sent") + " ✓";
    if (result.error === "not_set") return t("web_notify_not_set", "Fill it in first.");
    return t("web_notify_failed", "Failed: {error}", { error: result.error ?? "" });
  }
</script>

<Line
  label={name}
  value={set ? t("web_notify_set", "On") : t("web_notify_off", "Off")}
  tone="muted"
  {open}
  onclick={ontoggle}
/>
{#if open}
  <OpenBox {text}>
    {#if fields.length}
      <form
        class="grid gap-2"
        onsubmit={(event) => {
          event.preventDefault();
          if (changed) saveTyped();
        }}
      >
        {#each fields as field (field.key)}
          <input
            class="field h-[38px] font-mono text-[13px]"
            type={field.secret ? "password" : "url"}
            autocomplete="off"
            value={typed[field.key] ?? field.value ?? ""}
            oninput={(event) => (typed[field.key] = event.currentTarget.value)}
            aria-label={`${name} ${field.key}`}
            placeholder={field.secret && field.set
              ? t("web_notify_replace", "Saved: type a new one to replace it…")
              : field.example}
          />
        {/each}
        <button type="submit" class="hidden" aria-hidden="true" tabindex="-1"></button>
      </form>
    {/if}
    {#if fields.length || set}
      <div class={["flex flex-wrap items-center gap-2", fields.length && "mt-2.5"]}>
        {#if fields.length}
          <button type="button" class="key key-sm" disabled={!changed || busy} onclick={saveTyped}>
            {t("web_save", "Save")}
          </button>
        {/if}
        {#if set}
          <button type="button" class="key key-sm" disabled={test === "testing"} onclick={runTest}>
            {test === "testing" ? t("testing", "Testing...") : t("test", "Test")}
          </button>
        {/if}
        {#if test && test !== "testing"}
          <span class={["ml-1.5 text-[13px]", test.ok ? "text-ink" : "text-caution"]} role="status"
            >{testText(test)}</span
          >
        {/if}
        {#if set && fields.length}
          <button
            type="button"
            class="ml-auto cursor-pointer text-[13px] text-muted hover:text-danger"
            disabled={busy}
            onclick={() => save(Object.fromEntries(fields.map((field) => [field.key, ""])))}
          >
            {t("web_remove", "Remove")}
          </button>
        {/if}
      </div>
    {/if}
  </OpenBox>
{/if}
