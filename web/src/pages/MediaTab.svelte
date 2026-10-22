<script lang="ts">
  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import RenameStatus from "../components/RenameStatus.svelte";
  import RowItem from "../components/RowItem.svelte";
  import { errorText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";
  import type { Page } from "../lib/pages";
  import { loadRows, type Row } from "../lib/rows";
  import { analysis, refreshSummary, type RowStatus } from "../lib/scan.svelte";
  import { renames, startRename } from "../lib/renames.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";

  // The tab of a media type: its rows, filtered by status.
  let { page }: { page: Page } = $props();

  let rows = $state<Row[] | null>(null);
  let filter = $state<RowStatus | "all">("all");
  let error = $state("");
  // The rows ticked, to rename only them.
  let ticked = $state<number[]>([]);
  // What the confirmation would rename: the rows ticked, or all the Ready ones.
  let asked = $state<number[] | null>(null);
  let confirming = $state(false);
  // The result of a rename closed by the user.
  let dismissed = $state<number | null>(null);

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
    ticked = [];
  });

  const ready = $derived(rows?.filter((row) => row.status === "ok") ?? []);
  // A row renamed or no longer Ready is no longer ticked.
  const selection = $derived(ticked.filter((id) => ready.some((row) => row.id === id)));
  const rename = $derived(
    renames.current?.media_type === mediaType && renames.current.id !== dismissed
      ? renames.current
      : null,
  );

  function filesOf(ids: number[]): number {
    return (rows ?? [])
      .filter((row) => ids.includes(row.id))
      .reduce((n, row) => n + row.files.length, 0);
  }

  function ask(ids: number[] | null) {
    asked = ids;
    confirming = true;
  }

  async function runRename() {
    error = "";
    try {
      await startRename(mediaType, asked ?? undefined);
      ticked = [];
    } catch (exc) {
      error = errorText(exc);
    }
  }

  function modeName(): string {
    switch (settings.data?.settings.file_mode) {
      case "link":
        return t("file_mode_link", "Hard link");
      case "copy":
        return t("file_mode_copy", "Copy");
      default:
        return t("file_mode_move", "Move");
    }
  }

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
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div>
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
    </div>
    <div class="flex items-center gap-3">
      {#if settings.data}
        <span class="text-xs text-muted">{t("file_mode", "File mode")} : {modeName()}</span>
      {/if}
      <button
        type="button"
        class="rounded-lg border border-line px-3 py-2 text-sm font-semibold hover:bg-hover disabled:opacity-50"
        disabled={!selection.length || renames.running}
        onclick={() => ask(selection)}
      >
        {t("web_rename_selection", "Rename the selection ({n})", { n: selection.length })}
      </button>
      <button
        type="button"
        class="button"
        disabled={!ready.length || renames.running}
        onclick={() => ask(null)}
      >
        {t("web_rename_ready", "Rename the Ready ones ({n})", { n: ready.length })}
      </button>
    </div>
  </div>

  {#if rename}
    <RenameStatus {rename} ondismiss={() => (dismissed = rename.id)} />
  {/if}

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
            selected={selection.includes(row.id)}
            onselect={(on) =>
              (ticked = on ? [...ticked, row.id] : ticked.filter((id) => id !== row.id))}
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

<ConfirmDialog
  bind:open={confirming}
  text={t("rename_confirm_files", "Rename {0} file(s)?", {
    0: filesOf(asked ?? ready.map((row) => row.id)),
  })}
  detail={[
    `${t("file_mode", "File mode")} : ${modeName()}.`,
    asked === null && count("ambiguous")
      ? t("rename_skips_to_pick", "{0} file(s) still to pick will be left as they are.", {
          0: filesOf((rows ?? []).filter((r) => r.status === "ambiguous").map((r) => r.id)),
        })
      : "",
  ].join(" ")}
  action={t("web_rename", "Rename")}
  onconfirm={runRename}
/>
