<script lang="ts">
  import Icon from "./Icon.svelte";
  import Poster from "./Poster.svelte";
  import StatusPill from "./StatusPill.svelte";
  import { ApiError } from "../lib/api";
  import { errorText, searchErrorText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";
  import { changeRow, searchRow, type Row } from "../lib/rows";

  // A row of a tab: a movie, a track, a book, a game, or a series or an album
  // with its files. Its panel shows the results to pick and a search field.
  let {
    row,
    destinations,
    selected = false,
    onselect,
    onchange,
  }: {
    row: Row;
    /** The destination folders of its media type. */
    destinations: string[];
    /** Ticked, to be renamed with "Rename the selection". */
    selected?: boolean;
    onselect: (selected: boolean) => void;
    onchange: (row: Row) => void;
  } = $props();

  let open = $state(false);
  let unfolded = $state(false);
  let query = $state("");
  let busy = $state(false);
  let error = $state("");

  const match = $derived(row.selected === null ? null : row.candidates[row.selected]);
  const grouped = $derived(row.files.length > 1);
  // Files shown when a group is unfolded, before "+ n more".
  const SHOWN = 8;
  let all = $state(false);

  function openPanel() {
    open = !open;
    query = row.query ?? "";
    error = "";
  }

  async function pick(index: number) {
    busy = true;
    error = "";
    try {
      onchange(await changeRow(row.id, { selected: index }));
      open = false;
    } catch (exc) {
      error = errorText(exc);
    } finally {
      busy = false;
    }
  }

  async function search(event: SubmitEvent) {
    event.preventDefault();
    busy = true;
    error = "";
    try {
      const found = await searchRow(row.id, query);
      onchange(found);
      if (!found.candidates.length) {
        error = t("no_results", "No results");
      }
    } catch (exc) {
      error = exc instanceof ApiError && exc.status === 409 ? searchErrorText(exc) : errorText(exc);
    } finally {
      busy = false;
    }
  }

  async function changeDestination(index: number) {
    try {
      onchange(await changeRow(row.id, { destination: index }));
    } catch (exc) {
      error = errorText(exc);
    }
  }

  function count(row: Row): string {
    const n = row.files.length;
    switch (row.kind) {
      case "episode":
        return t("web_episodes_count", "{n} episodes", { n });
      case "album":
        return t("web_tracks_count", "{n} tracks", { n });
      default:
        return t("web_files_count", "{n} files", { n });
    }
  }

  /** The last folder of a path: /data/movies → movies. */
  function folderName(path: string): string {
    return path.split("/").filter(Boolean).pop() ?? path;
  }
</script>

<div class="border-b border-line last:border-0">
  <div class={["flex items-center gap-3 px-4 py-2.5", open && "bg-hover"]}>
    <input
      type="checkbox"
      class="size-4 shrink-0 accent-(--color-accent) disabled:opacity-30"
      checked={selected && row.status === "ok"}
      disabled={row.status !== "ok"}
      aria-label={t("web_select_row", "Select")}
      onchange={(event) => onselect(event.currentTarget.checked)}
    />
    <Poster poster={match?.poster ?? null} />
    <div class="min-w-0 flex-1">
      <button
        type="button"
        class="flex max-w-full items-center gap-1 text-left text-sm"
        onclick={openPanel}
        aria-expanded={open}
      >
        {#if match}
          <span class="truncate font-semibold">{match.title}</span>
          {#if match.year}
            <span class="shrink-0 text-muted">({match.year})</span>
          {/if}
          {#if match.by}
            <span class="truncate text-muted">· {match.by}</span>
          {/if}
        {:else if row.status === "pending"}
          <span class="truncate font-semibold">{row.title ?? row.files[0].name}</span>
        {:else}
          <span class="text-muted italic">{t("no_results", "No results")}</span>
        {/if}
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="size-3.5 shrink-0 text-muted"><path d="m6 9 6 6 6-6" /></svg
        >
      </button>
      {#if grouped}
        <button
          type="button"
          class="mt-0.5 flex items-center gap-1 text-xs text-muted hover:text-fg"
          onclick={() => (unfolded = !unfolded)}
          aria-expanded={unfolded}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            class={["size-3.5 transition-transform", !unfolded && "-rotate-90"]}
            ><path d="m6 9 6 6 6-6" /></svg
          >
          {#if row.title && row.title.toLowerCase() !== match?.title?.toLowerCase()}
            <span class="truncate">{row.title} ·</span>
          {/if}
          {count(row)}
        </button>
      {:else}
        <p class="mt-0.5 truncate font-mono text-xs text-muted" title={row.files[0].path}>
          {row.files[0].name}
          {#if row.status === "ok" && row.files[0].new_name}
            <span class="text-faint">→</span>
            <span class="text-fg">{row.files[0].new_name}</span>
          {/if}
        </p>
        {#if row.files[0].error}
          <p class="mt-0.5 text-xs text-error">{row.files[0].error.message}</p>
        {/if}
      {/if}
    </div>
    {#if destinations.length > 1}
      <label class="flex shrink-0 items-center gap-1 text-xs text-muted">
        <Icon name="folder" class="size-3.5" />
        <select
          class="rounded-md border border-line bg-input px-1.5 py-1 text-xs"
          aria-label={t("destination", "Destination")}
          value={row.destination}
          onchange={(event) => changeDestination(Number(event.currentTarget.value))}
        >
          {#each destinations as path, index (path)}
            <option value={index} title={path}>{folderName(path)}</option>
          {/each}
        </select>
      </label>
    {/if}
    <StatusPill status={row.status} />
    <button
      type="button"
      class="rounded p-1.5 text-muted hover:bg-hover hover:text-fg"
      aria-label={t("search", "Search")}
      onclick={openPanel}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="size-4"
        ><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg
      >
    </button>
  </div>

  {#if open}
    <div class="bg-hover px-4 pt-1 pb-4 pl-22">
      {#if row.candidates.length}
        <p class="mb-2 text-xs text-muted">
          {t("web_pick_text", "Pick the right result, or search another title.")}
        </p>
        <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {#each row.candidates as candidate, index (index)}
            <button
              type="button"
              disabled={busy}
              class={[
                "flex gap-3 rounded-lg border p-2 text-left disabled:opacity-60",
                row.selected === index && row.status === "ok"
                  ? "border-accent bg-accent/10"
                  : "border-line bg-card hover:border-accent/50",
              ]}
              onclick={() => pick(index)}
            >
              <Poster poster={candidate.poster} class="h-20 w-14" />
              <span class="min-w-0">
                <span class="block text-sm font-semibold">
                  {candidate.title}
                  {#if candidate.year}<span class="font-normal text-muted">({candidate.year})</span
                    >{/if}
                </span>
                {#if candidate.by}
                  <span class="block truncate text-xs">{candidate.by}</span>
                {/if}
                {#if candidate.original_title && candidate.original_title !== candidate.title}
                  <span class="block truncate text-xs text-muted italic"
                    >{candidate.original_title}</span
                  >
                {/if}
                <span class="mt-1 line-clamp-3 text-xs text-muted">{candidate.overview}</span>
              </span>
            </button>
          {/each}
        </div>
      {/if}
      <form class="mt-3 flex max-w-md gap-2" onsubmit={search}>
        <input class="field py-1.5" bind:value={query} aria-label={t("search", "Search")} />
        <button class="button shrink-0" disabled={busy || !query.trim()}>
          {busy ? t("searching", "Searching...") : t("search", "Search")}
        </button>
      </form>
      {#if error}
        <p class="mt-2 text-sm text-error" role="alert">{error}</p>
      {/if}
    </div>
  {/if}

  {#if grouped && unfolded}
    <div class="pb-2">
      {#each all ? row.files : row.files.slice(0, SHOWN) as file (file.path)}
        <div class="flex items-center gap-2 py-1 pr-4 pl-22 font-mono text-xs">
          <span class="w-72 shrink-0 truncate text-muted" title={file.path}>{file.name}</span>
          {#if file.new_name && row.status === "ok"}
            <span class="text-faint">→</span>
            <span class="truncate">{file.new_name}</span>
          {/if}
          {#if file.error}
            <span class="truncate font-sans text-error">{file.error.message}</span>
          {/if}
        </div>
      {/each}
      {#if !all && row.files.length > SHOWN}
        <button
          type="button"
          class="py-1 pl-22 text-xs text-muted hover:text-fg"
          onclick={() => (all = true)}
        >
          {t("web_more_files", "+ {n} more", { n: row.files.length - SHOWN })}
        </button>
      {/if}
    </div>
  {/if}
</div>
