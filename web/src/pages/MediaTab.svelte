<script lang="ts">
  import RowItem from "../components/RowItem.svelte";
  import { errorText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";
  import type { Page } from "../lib/pages";
  import { loadRows, type Row } from "../lib/rows";
  import { analysis, refreshSummary, type RowStatus } from "../lib/scan.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";

  // The tab of a media type: its rows, filtered by status.
  let { page }: { page: Page } = $props();

  let rows = $state<Row[] | null>(null);
  let filter = $state<RowStatus | "all">("all");
  let error = $state("");

  const mediaType = $derived(page.mediaType!);

  // Read again at each analysis, and when the tab changes.
  $effect(() => {
    void analysis.changes;
    const wanted = mediaType;
    loadRows(wanted)
      .then((found) => {
        if (wanted === mediaType) rows = found;
      })
      .catch((exc) => (error = errorText(exc)));
  });

  $effect(() => {
    if (!settings.data) loadSettings().catch(() => {});
  });

  $effect(() => {
    void mediaType;
    filter = "all";
  });

  const shown = $derived(
    rows === null ? [] : filter === "all" ? rows : rows.filter((row) => row.status === filter),
  );

  function count(status: RowStatus): number {
    return rows?.filter((row) => row.status === status).length ?? 0;
  }

  function replace(changed: Row) {
    if (rows) rows = rows.map((row) => (row.id === changed.id ? changed : row));
    // The counts of the sidebar.
    refreshSummary().catch(() => {});
  }

  const FILTERS = $derived([
    ["all", t("web_all", "All"), rows?.length ?? 0],
    ["ok", t("status_ready", "Ready"), count("ok")],
    ["ambiguous", t("status_ambiguous", "Pick one"), count("ambiguous")],
    ["missing", t("status_missing", "Missing"), count("missing")],
  ] as const);
</script>

<div class="mx-auto max-w-6xl pb-16">
  <h1 class="text-2xl font-bold">{t(page.key, page.english)}</h1>
  <div class="mt-3 flex flex-wrap gap-1" role="tablist">
    {#each FILTERS as [value, label, n] (value)}
      <button
        type="button"
        role="tab"
        aria-selected={filter === value}
        class={[
          "rounded-full px-3 py-1 text-xs font-semibold",
          filter === value ? "bg-fg text-bg" : "text-muted hover:bg-hover",
        ]}
        onclick={() => (filter = value)}
      >
        {label}
        <span class="tabular-nums">{n}</span>
      </button>
    {/each}
  </div>

  {#if error}
    <p class="mt-4 text-sm text-error" role="alert">{error}</p>
  {/if}

  {#if rows !== null}
    {#if shown.length}
      <div class="mt-6 overflow-hidden rounded-xl border border-line bg-card">
        {#each shown as row (row.id)}
          <RowItem
            {row}
            destinations={settings.data?.folders[mediaType] ?? []}
            onchange={replace}
          />
        {/each}
      </div>
    {:else}
      <p class="mt-10 text-center text-sm text-muted">
        {rows.length
          ? t("web_no_rows_filter", "No row with this status.")
          : t("web_no_rows", "Nothing here yet: analyze the source folders.")}
      </p>
    {/if}
  {/if}
</div>
