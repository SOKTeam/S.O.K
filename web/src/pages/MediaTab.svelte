<script lang="ts">
  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import RenameStatus from "../components/RenameStatus.svelte";
  import RowItem from "../components/RowItem.svelte";
  import Tabs from "../components/Tabs.svelte";
  import { ROW_COLUMNS } from "../lib/columns";
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
    { value: "all", label: t("web_all", "All"), count: rows?.length ?? 0 },
    { value: "ok", label: t("web_ready_plural", "Ready"), count: count("ok") },
    { value: "ambiguous", label: t("web_to_pick", "To pick"), count: count("ambiguous") },
    { value: "missing", label: t("web_missing_plural", "Missing"), count: count("missing") },
  ]);

  const destinations = $derived(settings.data?.folders[mediaType] ?? []);

  /** The last folder of a path, with the whole path on hover. */
  function folderName(path: string): string {
    return path.split("/").filter(Boolean).pop() ?? path;
  }
  // The box of the header: every Ready row shown, or none.
  const readyShown = $derived(shown.filter((row) => row.status === "ok").map((row) => row.id));
  const allTicked = $derived(
    readyShown.length > 0 && readyShown.every((id) => selection.includes(id)),
  );
  const someTicked = $derived(!allTicked && readyShown.some((id) => selection.includes(id)));

  function tickAll(on: boolean) {
    ticked = on
      ? [...new Set([...ticked, ...readyShown])]
      : ticked.filter((id) => !readyShown.includes(id));
  }
</script>

<div class="mx-auto max-w-6xl pb-16">
  <div class="flex items-start justify-between gap-6">
    <div class="min-w-0 flex-1">
      <h1 class="text-3xl font-bold">{t(page.key, page.english)}</h1>
      {#if settings.data}
        <p class="mt-1.5 truncate text-[13px] text-muted">
          {modeName()}
          {#if destinations.length}
            · {t("web_to_folder", "to")}
            <span class="font-mono" title={destinations.join("\n")}>
              {folderName(destinations[0])}
            </span>
            {#if destinations.length > 1}
              <span>+{destinations.length - 1}</span>
            {/if}
          {/if}
        </p>
      {/if}
    </div>
    <button
      type="button"
      class="button px-5 py-2"
      disabled={!ready.length || renames.running}
      onclick={() => ask(null)}
    >
      {t("web_rename_ready", "Rename the Ready ones ({n})", { n: ready.length })}
    </button>
  </div>

  <div class="mt-5">
    <Tabs
      tabs={FILTERS}
      current={filter}
      onselect={(value) => (filter = value as RowStatus | "all")}
    />
  </div>

  {#if rename}
    <RenameStatus {rename} ondismiss={() => (dismissed = rename.id)} />
  {/if}

  {#if error}
    <p class="mt-4 text-sm text-error" role="alert">{error}</p>
  {/if}

  {#if rows !== null}
    {#if shown.length}
      <div class="mt-5 overflow-hidden rounded-xl border border-line bg-card">
        <div class={[ROW_COLUMNS, "label h-10 border-b border-line"]}>
          <input
            type="checkbox"
            class="check"
            checked={allTicked}
            indeterminate={someTicked}
            disabled={!readyShown.length}
            aria-label={t("web_select_all", "Select all")}
            onchange={(event) => tickAll(event.currentTarget.checked)}
          />
          <span class="col-span-2">{t("web_title", "Title")}</span>
          <span>{t("web_new_name", "New name")}</span>
          <span>{t("web_state", "Status")}</span>
          <span></span>
        </div>
        {#each shown as row (row.id)}
          <RowItem
            {row}
            {destinations}
            selected={selection.includes(row.id)}
            onselect={(on) =>
              (ticked = on ? [...ticked, row.id] : ticked.filter((id) => id !== row.id))}
            onchange={replace}
          />
        {/each}
      </div>
      <div class="mt-3.5 flex items-center justify-end gap-3.5 text-[13px] text-muted">
        <span>{t("web_selected_count", "{n} selected", { n: selection.length })}</span>
        <button
          type="button"
          class="button-outline"
          disabled={!selection.length || renames.running}
          onclick={() => ask(selection)}
        >
          {t("web_rename_the_selection", "Rename the selection")}
        </button>
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
    `${t("web_file_mode_is", "File mode: {mode}", { mode: modeName() })}.`,
    asked === null && count("ambiguous")
      ? t("rename_skips_to_pick", "{0} file(s) still to pick will be left as they are.", {
          0: filesOf((rows ?? []).filter((r) => r.status === "ambiguous").map((r) => r.id)),
        })
      : "",
  ].join(" ")}
  action={t("web_rename", "Rename")}
  onconfirm={runRename}
/>
