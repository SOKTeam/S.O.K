<script lang="ts">
  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import Icon from "../components/Icon.svelte";
  import Tabs from "../components/Tabs.svelte";
  import { errorText } from "../lib/errors";
  import { dayKey, daysAgo } from "../lib/format";
  import {
    forgetProcessed,
    loadHistory,
    loadProcessed,
    undo,
    type Operation,
    type ProcessedFile,
    type UndoReport,
  } from "../lib/history";
  import { i18n, t } from "../lib/i18n.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { OPERATION_COLUMNS, PROCESSED_COLUMNS } from "../lib/columns";
  import { navigate, router } from "../lib/router.svelte";
  import { renames } from "../lib/renames.svelte";

  // The renames, newest first, with their undo; and the files already
  // processed, which the analyses leave out (/history/processed).
  let operations = $state<Operation[] | null>(null);
  let processed = $state<ProcessedFile[] | null>(null);
  let unfolded = $state<string[]>([]);
  let error = $state("");
  let report = $state<UndoReport | null>(null);
  let asking = $state<{ operation: Operation; index?: number } | null>(null);
  let confirming = $state(false);
  let picked = $state<string[]>([]);

  const tab = $derived(router.path === "/history/processed" ? "processed" : "operations");

  // Both lists, for the counts of the tabs; read again after each rename.
  $effect(() => {
    void renames.current?.status;
    loadHistory()
      .then((found) => (operations = found))
      .catch((exc) => (error = errorText(exc)));
    loadProcessed()
      .then((found) => (processed = found))
      .catch((exc) => (error = errorText(exc)));
  });

  const TABS = $derived([
    { value: "operations", label: t("web_renames", "Renames"), count: operations?.length },
    {
      value: "processed",
      label: t("web_processed", "Already processed"),
      count: processed?.length,
    },
  ]);

  // The operations by day, newest first: "Today", "Yesterday", then dates.
  const days = $derived.by(() => {
    const groups: { key: string; label: string; operations: Operation[] }[] = [];
    const today = new Date();
    for (const operation of operations ?? []) {
      const when = new Date(operation.date);
      const key = dayKey(when);
      let group = groups.find((g) => g.key === key);
      if (!group) {
        const ago = daysAgo(when, today);
        const label =
          ago < 2
            ? new Intl.RelativeTimeFormat(i18n.language, { numeric: "auto" }).format(-ago, "day")
            : new Intl.DateTimeFormat(i18n.language, { dateStyle: "full" }).format(when);
        group = { key, label, operations: [] };
        groups.push(group);
      }
      group.operations.push(operation);
    }
    return groups;
  });

  const allPicked = $derived(
    Boolean(processed?.length) && processed!.every((f) => picked.includes(f.path)),
  );
  const somePicked = $derived(!allPicked && picked.length > 0);

  function time(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, { timeStyle: "short" }).format(new Date(value));
  }

  function shortDate(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(value));
  }

  /** The folder a file went to: its last folder, the whole path on hover. */
  function folderOf(path: string): string {
    const parts = path.split("/").filter(Boolean);
    return parts.length > 1 ? parts[parts.length - 2] : "";
  }

  function fileName(path: string): string {
    return path.split("/").pop() ?? path;
  }

  function pageOf(operation: Operation) {
    return MEDIA_PAGES.find((page) => page.mediaType === operation.media_type);
  }

  function videos(operation: Operation): number {
    return operation.files.filter((file) => !file.follows).length;
  }

  function subtitles(operation: Operation): number {
    return operation.files.filter((file) => file.follows).length;
  }

  /** The files an undo would put back: one file and its subtitles, or all. */
  function backCount(operation: Operation, index?: number): number {
    const files =
      index === undefined
        ? operation.files
        : operation.files.filter(
            (file) => file.index === index || file.follows === operation.files[index].target,
          );
    return files.filter((file) => !file.undone).length;
  }

  function ask(operation: Operation, index?: number) {
    asking = { operation, index };
    confirming = true;
  }

  async function runUndo() {
    if (!asking) return;
    error = "";
    try {
      report = await undo(asking.operation.id, asking.index);
      const changed = report.operation;
      operations = (operations ?? []).map((op) => (op.id === changed.id ? changed : op));
    } catch (exc) {
      error = errorText(exc);
    }
  }

  function reasonText(reason: string): string {
    switch (reason) {
      case "missing":
        return t("undo_missing", "moved or deleted since the rename");
      case "occupied":
        return t("undo_occupied", "another file has its old name");
      default:
        return t("undo_failed", "could not be moved");
    }
  }

  async function forget() {
    error = "";
    try {
      await forgetProcessed(picked);
      processed = (processed ?? []).filter((file) => !picked.includes(file.path));
      picked = [];
    } catch (exc) {
      error = errorText(exc);
    }
  }

  function modeName(mode: string): string {
    switch (mode) {
      case "link":
        return t("file_mode_link", "Hard link");
      case "copy":
        return t("file_mode_copy", "Copy");
      default:
        return t("file_mode_move", "Move");
    }
  }
</script>

<div class="mx-auto flex max-w-5xl flex-col pb-16">
  <h1 class="text-3xl font-bold">{t("history", "History")}</h1>
  <div class="mt-5">
    <Tabs
      tabs={TABS}
      current={tab}
      onselect={(value) => navigate(value === "processed" ? "/history/processed" : "/history")}
    />
  </div>

  {#if error}
    <p class="mt-4 text-sm text-error" role="alert">{error}</p>
  {/if}

  {#if tab === "operations"}
    {#if report}
      <div class="mt-5 rounded-xl border border-line bg-card px-4 py-3 text-sm" role="status">
        <p class="font-semibold">
          {t("undo_restored", "✓ {0} file(s) put back.", { 0: report.restored.length })}
        </p>
        {#if report.skipped.length}
          <p class="mt-2 text-warn">
            {t("undo_skipped", "{0} file(s) left in place:", { 0: report.skipped.length })}
          </p>
          <ul class="mt-1 text-xs">
            {#each report.skipped as skipped (skipped.target)}
              <li>
                <span class="font-mono">{fileName(skipped.target)}</span>
                <span class="text-muted">· {reasonText(skipped.reason)}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}

    {#if operations?.length === 0}
      <p class="mt-10 text-center text-sm text-muted">
        {t("history_empty", "No rename yet.")}
      </p>
    {/if}

    {#each days as day (day.key)}
      <p class="label mt-7 mb-2.5 px-1">{day.label}</p>
      <div class="overflow-hidden rounded-xl border border-line bg-card">
        <div class={[OPERATION_COLUMNS, "label h-10 border-b border-line"]}>
          <span></span>
          <span>{t("web_time", "Time")}</span>
          <span>{t("web_type", "Type")}</span>
          <span>{t("files", "Files")}</span>
          <span>{t("file_mode", "File mode")}</span>
          <span>{t("web_state", "Status")}</span>
          <span></span>
        </div>
        {#each day.operations as operation (operation.id)}
          {@const page = pageOf(operation)}
          {@const open = unfolded.includes(operation.id)}
          {@const toggle = () =>
            (unfolded = open
              ? unfolded.filter((id) => id !== operation.id)
              : [...unfolded, operation.id])}
          <div class="border-b border-line last:border-0">
            <div
              class={[OPERATION_COLUMNS, "min-h-13 cursor-pointer text-sm hover:bg-hover"]}
              role="button"
              tabindex="0"
              aria-expanded={open}
              onclick={toggle}
              onkeydown={(event) => (event.key === "Enter" || event.key === " ") && toggle()}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                class={["size-4 text-muted transition-transform", !open && "-rotate-90"]}
                ><path d="m6 9 6 6 6-6" /></svg
              >
              <span class="tabular-nums">{time(operation.date)}</span>
              <span class="flex items-center gap-2.5 font-medium">
                <Icon name={page?.icon ?? "file"} class="size-4.5 shrink-0 text-icon" />
                <span class="truncate">{page ? t(page.key, page.english) : operation.kind}</span>
              </span>
              <span class="truncate">
                {t("history_files", "{0} file(s)", { 0: videos(operation) })}
                {#if subtitles(operation)}
                  · {t("history_subtitles", "{0} subtitle(s)", { 0: subtitles(operation) })}
                {/if}
              </span>
              <span class="truncate text-muted">
                {modeName(operation.files[0]?.mode ?? "move")}
                {#if operation.auto}· {t("web_automatic", "automatic")}{/if}
              </span>
              <span class="truncate text-muted">
                {#if operation.undone}
                  {t("history_undone", "Undone")}
                {:else if operation.partly_undone}
                  {t("history_partly_undone", "Partly undone")}
                {/if}
              </span>
              <span class="text-right">
                {#if !operation.undone}
                  <button
                    type="button"
                    class="button-outline px-3.5 py-1"
                    onclick={(event) => {
                      event.stopPropagation();
                      ask(operation);
                    }}
                  >
                    {t("undo", "Undo")}
                  </button>
                {/if}
              </span>
            </div>
            {#if open}
              <div class="px-4 pb-2.5">
                {#each operation.files as file (file.index)}
                  <div
                    class="grid grid-cols-[1rem_minmax(0,1fr)_minmax(0,1.2fr)_8rem] items-center gap-x-3.5 border-t border-line py-1.5 text-[13px] first:border-0"
                  >
                    <span></span>
                    <span
                      class={[
                        "truncate font-mono text-xs text-muted",
                        file.undone && "line-through opacity-60",
                      ]}
                      title={file.source}
                    >
                      {fileName(file.source)}
                    </span>
                    <span class="min-w-0" title={file.target}>
                      <span
                        class={[
                          "block truncate font-mono",
                          file.undone
                            ? "line-through opacity-60"
                            : file.follows
                              ? "text-muted"
                              : "font-semibold text-ok",
                        ]}
                      >
                        {fileName(file.target)}
                      </span>
                      <span class="block truncate text-xs text-muted">
                        {file.follows
                          ? t("web_subtitle_follows", "subtitle, follows its video")
                          : folderOf(file.target)}
                      </span>
                    </span>
                    <span class="text-right">
                      {#if file.undone}
                        <span class="text-muted">{t("web_put_back_done", "Put back")}</span>
                      {:else if !file.follows}
                        <button
                          type="button"
                          class="link"
                          onclick={() => ask(operation, file.index)}
                        >
                          {t("web_put_back", "Put back")}
                        </button>
                      {/if}
                    </span>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/each}
  {:else}
    <p class="mt-6 px-1 text-sm text-muted">
      {t(
        "web_processed_text",
        "Renamed with a hard link or a copy, these files stay in the downloads: the analyses leave them out while they do not change. Analyze one again to rename it once more.",
      )}
    </p>
    {#if processed?.length === 0}
      <p class="mt-10 text-center text-sm text-muted">
        {t("web_processed_empty", "No file processed yet.")}
      </p>
    {:else if processed}
      <div class="mt-4 overflow-hidden rounded-xl border border-line bg-card">
        <div class={[PROCESSED_COLUMNS, "label h-10 border-b border-line"]}>
          <input
            type="checkbox"
            class="check"
            checked={allPicked}
            indeterminate={somePicked}
            aria-label={t("web_select_all", "Select all")}
            onchange={(event) =>
              (picked = event.currentTarget.checked ? processed!.map((f) => f.path) : [])}
          />
          <span>{t("web_file", "File")}</span>
          <span>{t("web_renamed_to", "Renamed to")}</span>
          <span>{t("web_date", "Date")}</span>
        </div>
        {#each processed as file (file.path)}
          <label
            class={[
              PROCESSED_COLUMNS,
              "min-h-11 cursor-pointer border-b border-line text-[13px] last:border-0 hover:bg-hover",
            ]}
          >
            <input
              type="checkbox"
              class="check"
              checked={picked.includes(file.path)}
              onchange={(event) =>
                (picked = event.currentTarget.checked
                  ? [...picked, file.path]
                  : picked.filter((p) => p !== file.path))}
            />
            <span class="truncate font-mono" title={file.path}>{fileName(file.path)}</span>
            <span class="truncate font-mono" title={file.target}>{fileName(file.target)}</span>
            <span class="text-muted">{shortDate(file.date)}</span>
          </label>
        {/each}
      </div>
      <div class="mt-3.5 flex items-center justify-end gap-3.5 text-[13px] text-muted">
        <span>{t("web_selected_count", "{n} selected", { n: picked.length })}</span>
        <button type="button" class="button-outline" disabled={!picked.length} onclick={forget}>
          {t("web_analyze_selection", "Analyze the selection again")}
        </button>
      </div>
    {/if}
  {/if}
</div>

<ConfirmDialog
  bind:open={confirming}
  text={t("history_confirm_undo", "Put {0} file(s) back where they were?", {
    0: asking ? backCount(asking.operation, asking.index) : 0,
  })}
  action={t("undo", "Undo")}
  onconfirm={runUndo}
/>
