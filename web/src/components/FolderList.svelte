<script lang="ts">
  import Icon from "./Icon.svelte";
  import { t } from "../lib/i18n.svelte";

  // The folders of a role: a list, a field to add one, a button to remove one.
  // The paths are those the server sees (inside the container).
  let {
    label,
    paths,
    example,
    error = "",
    onchange,
  }: {
    label: string;
    paths: string[];
    /** An example of path, in the empty field. */
    example: string;
    error?: string;
    onchange: (paths: string[]) => Promise<boolean>;
  } = $props();

  let typed = $state("");

  async function add(event: SubmitEvent) {
    event.preventDefault();
    const path = typed.trim();
    if (path && (await onchange([...paths, path]))) {
      typed = "";
    }
  }
</script>

<div class="flex flex-col gap-2 px-4 py-3">
  <p class="text-sm font-semibold">{label}</p>
  {#each paths as path, index (path)}
    <div class="flex items-center gap-2 rounded-lg bg-bg px-3 py-1.5 text-sm">
      <Icon name="folder" class="size-4 shrink-0 text-muted" />
      <span class="min-w-0 flex-1 truncate font-mono text-xs" title={path}>{path}</span>
      {#if index === 0 && paths.length > 1}
        <span class="text-xs text-muted">{t("web_default", "Default")}</span>
      {/if}
      <button
        type="button"
        class="rounded p-1 text-muted hover:bg-hover hover:text-error"
        aria-label={t("web_remove_folder", "Remove {path}", { path })}
        onclick={() => onchange(paths.filter((p) => p !== path))}
      >
        <Icon name="cross" class="size-3.5" />
      </button>
    </div>
  {/each}
  <form class="flex gap-2" onsubmit={add}>
    <input
      class="field font-mono text-xs"
      bind:value={typed}
      placeholder={example}
      aria-label={label}
    />
    <button class="button shrink-0" disabled={!typed.trim()}>{t("drop_add", "Add")}</button>
  </form>
  {#if error}
    <p class="text-sm text-error" role="alert">{error}</p>
  {/if}
</div>
