<script lang="ts">
  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import Icon from "../components/Icon.svelte";
  import { errorText } from "../lib/errors";
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

  // Read again after each rename.
  $effect(() => {
    void renames.current?.status;
    if (tab === "operations") {
      loadHistory()
        .then((found) => (operations = found))
        .catch((exc) => (error = errorText(exc)));
    } else {
      loadProcessed()
        .then((found) => (processed = found))
        .catch((exc) => (error = errorText(exc)));
    }
  });

  function date(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
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

<div class="mx-auto flex max-w-5xl flex-col gap-6 pb-16">
  <div>
    <h1 class="text-2xl font-bold">{t("history", "History")}</h1>
    <div class="mt-3 flex gap-1" role="tablist">
      {#each [["operations", "/history", t("web_renames", "Renames")], ["processed", "/history/processed", t("web_processed", "Already processed")]] as [value, path, label] (value)}
        <button
          type="button"
          role="tab"
          aria-selected={tab === value}
          class={[
            "rounded-full px-3 py-1 text-xs font-semibold",
            tab === value ? "bg-fg text-bg" : "text-muted hover:bg-hover",
          ]}
          onclick={() => navigate(path)}
        >
          {label}
        </button>
      {/each}
    </div>
  </div>

  {#if error}
    <p class="text-sm text-error" role="alert">{error}</p>
  {/if}

  {#if tab === "operations"}
    {#if report}
      <div class="rounded-xl border border-line bg-card p-4 text-sm" role="status">
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
      <p class="mt-6 text-center text-sm text-muted">
        {t("history_empty", "No rename yet.")}
      </p>
    {/if}

    <div class="flex flex-col gap-3">
      {#each operations ?? [] as operation (operation.id)}
        {@const page = pageOf(operation)}
        {@const open = unfolded.includes(operation.id)}
        <div class="rounded-xl border border-line bg-card">
          <div class="flex items-center gap-3 px-4 py-3">
            <Icon name={page?.icon ?? "file"} class="size-4.5 shrink-0 text-accent" />
            <button
              type="button"
              class="min-w-0 flex-1 text-left"
              aria-expanded={open}
              onclick={() =>
                (unfolded = open
                  ? unfolded.filter((id) => id !== operation.id)
                  : [...unfolded, operation.id])}
            >
              <span class="block text-sm font-semibold">
                {page ? t(page.key, page.english) : operation.kind}
                <span class="font-normal text-muted">· {date(operation.date)}</span>
              </span>
              <span class="block text-xs text-muted">
                {t("history_files", "{0} file(s)", { 0: videos(operation) })}
                {#if subtitles(operation)}
                  · {t("history_subtitles", "{0} subtitle(s)", { 0: subtitles(operation) })}
                {/if}
                · {modeName(operation.files[0]?.mode ?? "move")}
              </span>
            </button>
            {#if operation.undone}
              <span class="rounded-full bg-hover px-2 py-0.5 text-xs text-muted">
                {t("history_undone", "Undone")}
              </span>
            {:else}
              {#if operation.partly_undone}
                <span class="rounded-full bg-warn/15 px-2 py-0.5 text-xs text-warn">
                  {t("history_partly_undone", "Partly undone")}
                </span>
              {/if}
              <button
                type="button"
                class="rounded-lg border border-line px-3 py-1.5 text-xs font-semibold hover:bg-hover"
                onclick={() => ask(operation)}
              >
                {t("undo_rename", "Undo the rename")}
              </button>
            {/if}
          </div>
          {#if open}
            <div class="border-t border-line py-2">
              {#each operation.files as file (file.index)}
                <div
                  class={[
                    "flex items-center gap-2 py-1 pr-4 font-mono text-xs",
                    file.follows ? "pl-14" : "pl-11",
                    file.undone && "opacity-50",
                  ]}
                >
                  <span class="min-w-0 flex-1 truncate" title={`${file.source} → ${file.target}`}>
                    <span class="text-muted">{fileName(file.source)}</span>
                    <span class="text-faint">→</span>
                    {fileName(file.target)}
                  </span>
                  {#if file.undone}
                    <span class="font-sans text-muted">{t("history_undone", "Undone")}</span>
                  {:else if !file.follows}
                    <button
                      type="button"
                      class="font-sans font-semibold text-accent hover:underline"
                      onclick={() => ask(operation, file.index)}
                    >
                      {t("history_undo_file", "Put this file back")}
                    </button>
                  {/if}
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {:else}
    <p class="text-sm text-muted">
      {t(
        "web_processed_text",
        "Renamed with a hard link or a copy, these files stay in the downloads: the analyses leave them out while they do not change. Analyze one again to rename it once more.",
      )}
    </p>
    {#if processed?.length === 0}
      <p class="mt-6 text-center text-sm text-muted">
        {t("web_processed_empty", "No file processed yet.")}
      </p>
    {:else if processed}
      <div class="flex items-center justify-between">
        <label class="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            class="size-4 accent-(--color-accent)"
            checked={picked.length === processed.length}
            onchange={(event) =>
              (picked = event.currentTarget.checked ? processed!.map((f) => f.path) : [])}
          />
          {t("web_select_all", "Select all")}
        </label>
        <button type="button" class="button" disabled={!picked.length} onclick={forget}>
          {t("web_analyze_again", "Analyze again ({n})", { n: picked.length })}
        </button>
      </div>
      <div class="divide-y divide-line rounded-xl border border-line bg-card">
        {#each processed as file (file.path)}
          <label class="flex items-center gap-3 px-4 py-2.5">
            <input
              type="checkbox"
              class="size-4 shrink-0 accent-(--color-accent)"
              checked={picked.includes(file.path)}
              onchange={(event) =>
                (picked = event.currentTarget.checked
                  ? [...picked, file.path]
                  : picked.filter((p) => p !== file.path))}
            />
            <span class="min-w-0 flex-1">
              <span class="block truncate font-mono text-xs" title={file.path}>
                {fileName(file.path)}
              </span>
              <span class="block truncate font-mono text-xs text-muted" title={file.target}>
                → {fileName(file.target)}
              </span>
            </span>
            <span class="shrink-0 text-xs text-muted">{date(file.date)}</span>
          </label>
        {/each}
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
