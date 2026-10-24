<script lang="ts">
  import Icon from "./Icon.svelte";
  import { api } from "../lib/api";
  import { errorText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";

  // A window to pick a folder of the server: the browser cannot see its disks,
  // so the server lists them (GET /api/settings/browse).
  let {
    open = $bindable(false),
    start,
    onpick,
  }: {
    open?: boolean;
    /** The folder shown first; the root of the server when absent. */
    start?: string;
    onpick: (path: string) => void;
  } = $props();

  interface Listing {
    path: string;
    parent: string | null;
    folders: { name: string; path: string }[];
  }

  let dialog = $state<HTMLDialogElement>();
  let listing = $state<Listing | null>(null);
  let error = $state("");
  let loading = $state(false);

  async function show(path?: string) {
    loading = true;
    error = "";
    try {
      const query = path ? `?path=${encodeURIComponent(path)}` : "";
      listing = await api<Listing>(`/api/settings/browse${query}`);
    } catch (exc) {
      // A start folder gone since: the root instead.
      if (path && path === start && !listing) {
        return show();
      }
      error = errorText(exc);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (open && !dialog?.open) {
      listing = null;
      dialog?.showModal();
      show(start);
    }
    if (!open && dialog?.open) dialog?.close();
  });

  /** The folders from the root to the one shown, to go back with one click. */
  const crumbs = $derived.by(() => {
    if (!listing) return [];
    const parts = listing.path.split("/").filter(Boolean);
    return [
      { name: "/", path: "/" },
      ...parts.map((name, i) => ({ name, path: "/" + parts.slice(0, i + 1).join("/") })),
    ];
  });

  function pick() {
    if (!listing) return;
    onpick(listing.path);
    open = false;
  }
</script>

<dialog
  bind:this={dialog}
  onclose={() => (open = false)}
  class="m-auto h-[70vh] w-full max-w-xl flex-col rounded-2xl border border-line bg-card p-0 text-fg shadow-xl backdrop:bg-black/40 open:flex"
>
  <div class="border-b border-line px-5 py-4">
    <p class="font-semibold">{t("web_choose_folder", "Choose a folder of the server")}</p>
    <nav class="mt-2 flex flex-wrap items-center gap-0.5 font-mono text-xs">
      {#each crumbs as crumb, index (crumb.path)}
        {#if index > 1}<span class="text-faint">/</span>{/if}
        <button
          type="button"
          class="rounded px-1 py-0.5 hover:bg-hover hover:text-accent"
          onclick={() => show(crumb.path)}
        >
          {crumb.name}
        </button>
      {/each}
    </nav>
  </div>

  <div class="min-h-0 flex-1 overflow-y-auto py-1">
    {#if listing?.parent}
      <button
        type="button"
        class="flex w-full items-center gap-3 px-5 py-2 text-left text-sm text-muted hover:bg-hover"
        onclick={() => show(listing!.parent!)}
      >
        <span class="w-4 text-center">↑</span>
        {t("web_parent_folder", "Parent folder")}
      </button>
    {/if}
    {#each listing?.folders ?? [] as folder (folder.path)}
      <button
        type="button"
        class="flex w-full items-center gap-3 px-5 py-2 text-left text-sm hover:bg-hover"
        onclick={() => show(folder.path)}
      >
        <Icon name="folder" class="size-4 shrink-0 text-accent" />
        <span class="truncate">{folder.name}</span>
      </button>
    {/each}
    {#if listing && !listing.folders.length && !loading}
      <p class="px-5 py-6 text-center text-sm text-muted">
        {t("web_no_subfolder", "No folder inside.")}
      </p>
    {/if}
    {#if error}
      <p class="px-5 py-3 text-sm text-error" role="alert">{error}</p>
    {/if}
  </div>

  <div class="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
    <span class="min-w-0 truncate font-mono text-xs text-muted" title={listing?.path}>
      {listing?.path ?? ""}
    </span>
    <div class="flex shrink-0 gap-2">
      <button type="button" class="button-outline" onclick={() => (open = false)}>
        {t("web_cancel", "Cancel")}
      </button>
      <button type="button" class="button" disabled={!listing} onclick={pick}>
        {t("web_choose_this_folder", "Choose this folder")}
      </button>
    </div>
  </div>
</dialog>
