<script lang="ts">
  import Poster from "./Poster.svelte";
  import StatusText from "./StatusText.svelte";
  import { ApiError } from "../lib/api";
  import { ROW_COLUMNS } from "../lib/columns";
  import { errorText, searchErrorText } from "../lib/errors";
  import { splitName } from "../lib/format";
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

  // The folders of the new names under the destination: "Show/Season 1".
  const folders = $derived(
    [
      ...new Set(
        row.files
          .map((file) => (file.new_name ? splitName(file.new_name).folder : ""))
          .filter(Boolean),
      ),
    ].sort((a, b) => a.localeCompare(b, undefined, { numeric: true })),
  );
</script>

{#snippet chevron(open: boolean)}
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    class={["size-3.5 shrink-0 transition-transform", !open && "-rotate-90"]}
    ><path d="m6 9 6 6 6-6" /></svg
  >
{/snippet}

<div class="border-b border-line last:border-0">
  <div class={[ROW_COLUMNS, "min-h-16 py-2", open ? "bg-hover" : "hover:bg-hover"]}>
    <input
      type="checkbox"
      class="check"
      checked={selected && row.status === "ok"}
      disabled={row.status !== "ok"}
      aria-label={t("web_select_row", "Select")}
      onchange={(event) => onselect(event.currentTarget.checked)}
    />
    <Poster poster={match?.poster ?? null} class="h-12 w-8.5" />

    <div class="min-w-0">
      <button
        type="button"
        class="flex max-w-full items-baseline gap-1.5 text-left text-sm"
        onclick={openPanel}
        aria-expanded={open}
      >
        {#if match}
          <span class="truncate font-semibold">{match.title}</span>
          {#if match.year}
            <span class="shrink-0 text-muted">{match.year}</span>
          {/if}
          {#if match.by}
            <span class="truncate text-muted">· {match.by}</span>
          {/if}
        {:else if row.status === "pending"}
          <span class="truncate font-semibold">{row.title ?? row.files[0].name}</span>
        {:else}
          <span class="text-muted italic">{t("no_results", "No results")}</span>
        {/if}
      </button>
      {#if grouped}
        <button
          type="button"
          class="mt-0.5 flex max-w-full items-center gap-1 text-xs text-muted hover:text-fg"
          onclick={() => (unfolded = !unfolded)}
          aria-expanded={unfolded}
        >
          {@render chevron(unfolded)}
          {#if row.title && row.title.toLowerCase() !== match?.title?.toLowerCase()}
            <span class="truncate">{row.title} ·</span>
          {/if}
          {count(row)}
        </button>
      {:else}
        <p class="mt-0.5 truncate font-mono text-xs text-muted" title={row.files[0].path}>
          {row.files[0].name}
        </p>
        {#if row.files[0].error}
          <p class="mt-0.5 text-xs text-error">{row.files[0].error.message}</p>
        {/if}
      {/if}
    </div>

    <div class="min-w-0 text-[13px]">
      {#if grouped}
        <!-- A group: the folders of its files, its names below once unfolded. -->
        <p
          class={["truncate font-mono", row.status === "ok" && "font-semibold text-ok"]}
          title={folders.join("\n")}
        >
          {folders.length ? folders.join(" · ") : count(row)}
        </p>
      {:else if row.files[0].new_name}
        {@const name = splitName(row.files[0].new_name).name}
        <p
          class={["truncate font-mono", row.status === "ok" && "font-semibold text-ok"]}
          title={row.files[0].new_name}
        >
          {name}
        </p>
      {:else}
        <p class="text-faint">—</p>
      {/if}
      {#if (!grouped && folders.length) || destinations.length > 1}
        <div class="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-muted">
          {#if destinations.length > 1}
            <select
              class="-ml-1 [field-sizing:content] max-w-40 shrink-0 cursor-pointer truncate rounded bg-transparent px-1 hover:bg-hover"
              aria-label={t("destination", "Destination")}
              value={row.destination}
              onchange={(event) => changeDestination(Number(event.currentTarget.value))}
            >
              {#each destinations as path, index (path)}
                <option value={index} title={path}>{folderName(path)}</option>
              {/each}
            </select>
            {#if !grouped && folders.length}<span class="text-faint">/</span>{/if}
          {/if}
          {#if !grouped && folders.length}
            <span class="truncate" title={folders[0]}>{folders[0]}</span>
          {/if}
        </div>
      {/if}
    </div>

    <StatusText status={row.status} />
    <button
      type="button"
      class="rounded-full p-1.5 text-muted hover:bg-hover hover:text-fg"
      aria-label={t("search", "Search")}
      onclick={openPanel}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="size-4"
        ><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg
      >
    </button>
  </div>

  {#if open}
    <div class="bg-hover px-4 pt-1 pb-4 pl-[6.25rem]">
      {#if row.candidates.length}
        <p class="mb-2.5 text-[13px] text-muted">
          {t("web_pick_text", "Pick the right result, or search another title.")}
        </p>
        <div class="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
          {#each row.candidates as candidate, index (index)}
            <button
              type="button"
              disabled={busy}
              class={[
                "flex gap-3 rounded-lg border bg-input p-2 text-left disabled:opacity-60",
                row.selected === index && row.status === "ok"
                  ? "border-accent"
                  : "border-line hover:border-accent",
              ]}
              onclick={() => pick(index)}
            >
              <Poster poster={candidate.poster} class="h-21 w-14" />
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
        <button class="button" disabled={busy || !query.trim()}>
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
        <div class={[ROW_COLUMNS, "py-1 text-xs"]}>
          <span class="col-start-3 truncate font-mono text-muted" title={file.path}>
            {file.name}
          </span>
          {#if file.error}
            <span class="truncate text-error">{file.error.message}</span>
          {:else if file.new_name}
            <span
              class={["truncate font-mono", row.status === "ok" && "font-semibold text-ok"]}
              title={file.new_name}
            >
              {splitName(file.new_name).name}
            </span>
          {/if}
        </div>
      {/each}
      {#if !all && row.files.length > SHOWN}
        <button
          type="button"
          class="py-1 pl-[6.25rem] text-xs text-muted hover:text-fg"
          onclick={() => (all = true)}
        >
          {t("web_more_files", "+ {n} more", { n: row.files.length - SHOWN })}
        </button>
      {/if}
    </div>
  {/if}
</div>
