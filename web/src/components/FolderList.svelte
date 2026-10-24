<script lang="ts">
  import FolderBrowser from "./FolderBrowser.svelte";
  import Icon from "./Icon.svelte";
  import { parentFolder } from "../lib/format";
  import { t } from "../lib/i18n.svelte";

  // The folders of a role, as rows of the folders card: the label on the
  // first one, a button to remove each, and "Add a folder…", which opens a
  // field and the folder browser. The paths are those the server sees
  // (inside the container).
  let {
    label,
    icon,
    paths,
    example,
    near,
    error = "",
    onchange,
  }: {
    label: string;
    icon: string;
    paths: string[];
    /** An example of path, in the empty field. */
    example: string;
    /** Where the browser opens while the list is empty. */
    near?: string;
    error?: string;
    onchange: (paths: string[]) => Promise<boolean>;
  } = $props();

  let adding = $state(false);
  let typed = $state("");
  let browsing = $state(false);

  /** The browser opens next to the last folder of the list. */
  const start = $derived(paths.length ? parentFolder(paths[paths.length - 1]) : near);

  async function add(event: SubmitEvent) {
    event.preventDefault();
    const path = typed.trim();
    if (path && (await onchange([...paths, path]))) {
      typed = "";
      adding = false;
    }
  }
</script>

{#snippet name(first: boolean)}
  <span class="flex w-48 shrink-0 items-center gap-2.5 font-medium">
    {#if first}
      <Icon name={icon} class="size-4.5 shrink-0 text-icon" />
      {label}
    {/if}
  </span>
{/snippet}

<div class="border-b border-line last:border-0">
  {#each paths as path, index (path)}
    <div class="flex min-h-12 items-center gap-4 px-4 py-2 text-sm">
      {@render name(index === 0)}
      <!-- Cut at the start: the end of a path tells it apart. -->
      <span class="min-w-0 flex-1 truncate text-left font-mono [direction:rtl]" title={path}>
        <bdi>{path}</bdi>
      </span>
      {#if index === 0 && paths.length > 1}
        <span class="text-xs text-muted">{t("web_default", "Default")}</span>
      {/if}
      <button
        type="button"
        class="rounded-full p-1.5 text-muted hover:bg-hover hover:text-fg"
        aria-label={t("web_remove_folder", "Remove {path}", { path })}
        onclick={() => onchange(paths.filter((p) => p !== path))}
      >
        <Icon name="cross" class="size-3.5" />
      </button>
    </div>
  {/each}
  {#if !paths.length}
    <div class="flex min-h-12 items-center gap-4 px-4 py-2 text-sm">
      {@render name(true)}
      <span class="text-muted">{t("web_no_folder", "No folder")}</span>
    </div>
  {/if}
  <div class="flex items-center gap-4 px-4 pb-3 text-sm">
    {@render name(false)}
    {#if adding}
      <form class="flex flex-1 flex-wrap items-center gap-2" onsubmit={add}>
        <!-- svelte-ignore a11y_autofocus -->
        <input
          class="field max-w-sm flex-1 py-1.5 font-mono"
          bind:value={typed}
          placeholder={example}
          aria-label={label}
          autofocus
        />
        <button type="button" class="button-outline px-3 py-1" onclick={() => (browsing = true)}>
          {t("web_browse", "Browse…")}
        </button>
        <button class="link" disabled={!typed.trim()}>{t("drop_add", "Add")}</button>
        <button
          type="button"
          class="text-sm text-muted hover:text-fg"
          onclick={() => {
            adding = false;
            typed = "";
          }}
        >
          {t("web_cancel", "Cancel")}
        </button>
      </form>
    {:else}
      <button type="button" class="link" onclick={() => (adding = true)}>
        {t("web_add_folder", "Add a folder…")}
      </button>
    {/if}
  </div>
  {#if error}
    <p class="px-4 pb-3 pl-56 text-sm text-error" role="alert">{error}</p>
  {/if}
</div>

<FolderBrowser
  bind:open={browsing}
  {start}
  onpick={(path) => {
    if (!paths.includes(path)) onchange([...paths, path]);
    adding = false;
  }}
/>
