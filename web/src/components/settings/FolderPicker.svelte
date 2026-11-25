<script lang="ts">
  import { untrack } from "svelte";

  import { api } from "../../lib/api";
  import { errorText } from "../../lib/errors";
  import { t } from "../../lib/i18n.svelte";

  // The folder browser of the server, in the scene: the browser cannot see
  // the disks of the server, so the server lists them
  // (GET /api/settings/browse). The path at the bottom can be typed too.
  let {
    title,
    start,
    onpick,
    oncancel,
  }: {
    /** "Un dossier pour Films". */
    title: string;
    /** The folder shown first; the root of the server when absent. */
    start?: string;
    onpick: (path: string) => void;
    oncancel: () => void;
  } = $props();

  interface Listing {
    path: string;
    parent: string | null;
    folders: { name: string; path: string }[];
  }

  let listing = $state<Listing | null>(null);
  let typed = $state<string | null>(null);
  let error = $state("");
  let loading = $state(false);

  async function show(path?: string, fallback = false) {
    loading = true;
    error = "";
    try {
      const query = path ? `?path=${encodeURIComponent(path)}` : "";
      listing = await api<Listing>(`/api/settings/browse${query}`);
      typed = null;
    } catch (exc) {
      // A start folder gone since: the root instead.
      if (fallback) return show();
      error = errorText(exc);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    const first = start;
    untrack(() => show(first, Boolean(first)));
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
</script>

<div class="flex min-h-0 w-full flex-1 flex-col">
  <p class="label mb-1.5">{t("web_choose_folder", "Choose a folder of the server")}</p>
  <p class="text-[24px] leading-[1.15] font-[650] tracking-[-0.03em]">{title}</p>
  <nav class="mt-3.5 flex flex-wrap items-center font-mono text-[12.5px] text-muted">
    {#each crumbs as crumb, index (crumb.path)}
      {#if index > 1}<span class="px-0.5 text-faint">/</span>{/if}
      <button
        type="button"
        class={[
          "cursor-pointer rounded px-1 py-0.5 hover:text-ink",
          index === crumbs.length - 1 && "text-ink",
        ]}
        onclick={() => show(crumb.path)}
      >
        {crumb.name}
      </button>
    {/each}
  </nav>

  <div class="-mx-2.5 mt-2 min-h-[120px] flex-1 overflow-y-auto">
    {#if listing?.parent}
      <button
        type="button"
        class="flex w-full cursor-pointer items-center gap-3 rounded-lg px-2.5 py-[7px] text-left text-[14px] text-muted hover:bg-raised hover:text-ink"
        onclick={() => show(listing!.parent!)}
      >
        <span class="w-4 text-center font-mono">↑</span>
        {t("web_parent_folder", "Parent folder")}
      </button>
    {/if}
    {#each listing?.folders ?? [] as folder (folder.path)}
      <button
        type="button"
        class="flex w-full cursor-pointer items-center gap-3 rounded-lg px-2.5 py-[7px] text-left text-[14px] text-ink hover:bg-raised"
        onclick={() => show(folder.path)}
      >
        <svg
          class="size-4 shrink-0 text-faint"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          stroke-width="1.3"
          aria-hidden="true"
        >
          <path
            d="M1.8 4.2c0-.6.4-1 1-1h3.4l1.4 1.6h5.6c.6 0 1 .4 1 1v6.4c0 .6-.4 1-1 1H2.8c-.6 0-1-.4-1-1z"
          />
        </svg>
        <span class="truncate">{folder.name}</span>
      </button>
    {/each}
    {#if listing && !listing.folders.length && !loading}
      <p class="px-2.5 py-4 text-[14px] text-faint">{t("web_no_subfolder", "No folder inside.")}</p>
    {/if}
    {#if error}
      <p class="px-2.5 py-3 text-[13px] text-danger" role="alert">{error}</p>
    {/if}
  </div>

  <form
    class="mt-3 border-t border-line pt-3.5"
    onsubmit={(event) => {
      event.preventDefault();
      if (typed?.trim()) show(typed.trim());
    }}
  >
    <input
      class="w-full border-b border-line-strong bg-transparent pb-1.5 font-mono text-[13px] text-ink outline-none focus:border-accent"
      value={typed ?? listing?.path ?? ""}
      oninput={(event) => (typed = event.currentTarget.value)}
      aria-label={t("web_folder_path", "Path of the folder")}
      spellcheck="false"
      autocomplete="off"
    />
  </form>
  <div class="mt-4 flex gap-2.5">
    <button
      type="button"
      class="key key-primary"
      disabled={!listing || loading}
      onclick={() => listing && onpick(listing.path)}
    >
      {t("web_choose_this_folder", "Choose this folder")}
    </button>
    <button type="button" class="key" onclick={oncancel}>{t("web_cancel", "Cancel")}</button>
  </div>
</div>
