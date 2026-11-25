<script lang="ts">
  // The History: the renames by day (older months folded), the scene of the
  // one open with its undo confirmed in place; and the files already
  // processed (/history/processed), which the analyses leave out.
  import { onMount, untrack } from "svelte";

  import Split from "../components/layout/Split.svelte";
  import Thumb from "../components/media/Thumb.svelte";
  import Facts, { type Fact } from "../components/scene/Facts.svelte";
  import { posterColor } from "../lib/color";
  import { sizeText } from "../lib/disks";
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
  import { sectionsOf, type Section } from "../lib/historyGroups";
  import { i18n, t, tn } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";
  import { follow, href, router } from "../lib/router.svelte";
  import { bigPosterUrl, posterUrl } from "../lib/rows";
  import { renames } from "../lib/renames.svelte";
  import { refreshSummary, startScan } from "../lib/scan.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";

  let operations = $state<Operation[] | null>(null);
  let processed = $state<ProcessedFile[] | null>(null);
  let error = $state("");
  let openId = $state<string | null>(null);
  let unfolded = $state<string[]>([]);
  // The undo: what is asked (the operation, or one of its files), its
  // report.
  let asking = $state<{ index?: number } | null>(null);
  let report = $state<UndoReport | null>(null);
  let busy = $state(false);
  // The files already processed chosen to analyze again.
  let picking = $state(false);
  let chosen = $state<string[]>([]);
  let anchor = $state<string | null>(null);

  const tab = $derived(router.path === "/history/processed" ? "processed" : "operations");

  onMount(() => {
    if (!settings.data) loadSettings().catch(() => {});
    const leave = (event: KeyboardEvent) => {
      if (event.key === "Escape" && picking) endPicking();
    };
    window.addEventListener("keydown", leave);
    return () => {
      window.removeEventListener("keydown", leave);
      setLight(null);
    };
  });

  // Both lists, for their counts; read again after each rename.
  $effect(() => {
    void renames.current?.status;
    loadHistory()
      .then((found) => {
        operations = found;
        untrack(() => {
          if (!openId || !found.some((op) => op.id === openId)) openId = found[0]?.id ?? null;
        });
      })
      .catch((exc) => (error = errorText(exc)));
    loadProcessed()
      .then((found) => (processed = found))
      .catch((exc) => (error = errorText(exc)));
  });

  const sections = $derived(operations ? sectionsOf(operations, new Date()) : []);
  const oldest = $derived(
    (operations ?? []).reduce(
      (first, op) => (Date.parse(op.date) < Date.parse(first) ? op.date : first),
      operations?.[0]?.date ?? "",
    ),
  );
  const open = $derived(operations?.find((op) => op.id === openId) ?? null);
  const videoFiles = (op: Operation) => op.files.filter((file) => !file.follows);
  const total = $derived((operations ?? []).reduce((sum, op) => sum + videoFiles(op).length, 0));

  // The light: the first cover of the operation open, or of the selection.
  $effect(() => {
    const poster =
      tab === "operations" ? (open?.covers?.[0] ?? null) : (coverOf(chosen[0]) ?? null);
    const url = bigPosterUrl(poster);
    if (!url) {
      setLight(null);
      return;
    }
    posterColor(url).then((color) => setLight(color ?? "251, 96, 72"));
  });

  // ------------------------------------------------------------ Undo

  function openOperation(op: Operation) {
    openId = op.id;
    asking = null;
    report = null;
  }

  async function runUndo() {
    if (!open || !asking) return;
    busy = true;
    error = "";
    try {
      report = await undo(open.id, asking.index);
      const changed = report.operation;
      operations = (operations ?? []).map((op) => (op.id === changed.id ? changed : op));
      asking = null;
      refreshSummary().catch(() => {});
    } catch (exc) {
      error = errorText(exc);
    } finally {
      busy = false;
    }
  }

  /** The files an undo would put back: one file and its subtitles, or all. */
  function backCount(op: Operation, index?: number): number {
    const files =
      index === undefined
        ? op.files
        : op.files.filter(
            (file) => file.index === index || file.follows === op.files[index].target,
          );
    return files.filter((file) => !file.undone).length;
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

  // -------------------------------------------------- Already processed

  /** The cover of a file processed: the first of its operation. */
  function coverOf(path: string | undefined): string | null {
    const file = processed?.find((one) => one.path === path);
    return operations?.find((op) => op.id === file?.operation)?.covers?.[0] ?? null;
  }

  /** How a file processed was renamed: link or copy, from its operation. */
  function modeOf(file: ProcessedFile): string {
    const move = operations
      ?.find((op) => op.id === file.operation)
      ?.files.find((one) => one.source === file.path);
    return move?.mode ?? "link";
  }

  function endPicking() {
    picking = false;
    chosen = [];
    anchor = null;
  }

  function toggle(path: string) {
    chosen = chosen.includes(path) ? chosen.filter((p) => p !== path) : [...chosen, path];
    anchor = path;
    if (!chosen.length) endPicking();
  }

  function clickFile(file: ProcessedFile, event: MouseEvent) {
    const paths = (processed ?? []).map((one) => one.path);
    if (event.shiftKey && anchor) {
      const [a, b] = [paths.indexOf(anchor), paths.indexOf(file.path)].sort((x, y) => x - y);
      picking = true;
      chosen = [...new Set([...chosen, ...paths.slice(a, b + 1)])];
      return;
    }
    if (picking || event.metaKey || event.ctrlKey) {
      picking = true;
      toggle(file.path);
    }
  }

  async function analyzeAgain() {
    error = "";
    try {
      await forgetProcessed(chosen);
      processed = (processed ?? []).filter((file) => !chosen.includes(file.path));
      endPicking();
      await startScan().catch(() => {});
    } catch (exc) {
      error = errorText(exc);
    }
  }

  // ------------------------------------------------------------ Texts

  function time(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, { timeStyle: "short" }).format(new Date(value));
  }

  function shortDay(value: string | Date): string {
    return new Intl.DateTimeFormat(i18n.language, { day: "numeric", month: "short" }).format(
      new Date(value),
    );
  }

  function sectionTitle(section: Section): string {
    const month = new Intl.DateTimeFormat(i18n.language, { month: "long" }).format(section.date);
    switch (section.kind) {
      case "today":
        return t("web_today", "Today");
      case "yesterday":
        return `${t("web_yesterday", "Yesterday")} · ${new Intl.DateTimeFormat(i18n.language, {
          weekday: "long",
          day: "numeric",
          month: "long",
        }).format(section.date)}`;
      case "earlier":
        return t("web_earlier_in", "Earlier in {month}", { month });
      default:
        return month;
    }
  }

  /** "Today at 09:30", "Yesterday at 21:42", "19 Nov at 03:15". */
  function when(value: string): string {
    const day = sectionsOf([{ date: value } as Operation], new Date())[0]?.kind;
    if (day === "today") return t("web_today_at", "Today at {time}", { time: time(value) });
    if (day === "yesterday")
      return t("web_yesterday_at", "Yesterday at {time}", { time: time(value) });
    return t("web_day_at", "{day} at {time}", { day: shortDay(value), time: time(value) });
  }

  /** "6 movies put away", from the media type and the videos. */
  function opTitle(op: Operation): string {
    const n = videoFiles(op).length;
    return tn(`web_op_${op.media_type}`, n, "{n} file put away", "{n} files put away");
  }

  /** The common folder of some paths, without the last part. */
  function commonFolder(paths: string[]): string {
    if (!paths.length) return "";
    const split = paths.map((path) => path.split("/").slice(0, -1));
    const first = split[0];
    let n = 0;
    while (n < first.length && split.every((parts) => parts[n] === first[n])) n += 1;
    return first.slice(0, n).join("/") || "/";
  }

  function fromOf(op: Operation): string {
    const sources = settings.data?.folders.sources ?? [];
    const first = videoFiles(op)[0]?.source ?? "";
    return (
      sources.find((folder) => first.startsWith(`${folder.replace(/\/$/, "")}/`)) ??
      commonFolder(videoFiles(op).map((file) => file.source))
    );
  }

  function toOf(op: Operation): string {
    const folders = settings.data?.folders[op.media_type] ?? [];
    const first = videoFiles(op)[0]?.target ?? "";
    return (
      folders.find((folder) => first.startsWith(`${folder.replace(/\/$/, "")}/`)) ??
      commonFolder(videoFiles(op).map((file) => file.target))
    );
  }

  function transferOf(op: Operation): string {
    switch (op.files[0]?.mode) {
      case "link":
        return t("web_transfer_link", "hard links");
      case "copy":
        return t("web_transfer_copy", "copied");
      default:
        return t("web_transfer_move", "moved");
    }
  }

  function name(path: string): string {
    return path.split("/").pop() ?? path;
  }

  const facts = $derived<Fact[]>(
    open
      ? [
          {
            label: t("web_put_away_by", "Put away by"),
            value: open.auto ? t("web_by_auto", "the automatic sorting") : t("web_by_you", "you"),
          },
          { label: t("web_from", "From"), value: fromOf(open) },
          { label: t("web_to", "To"), value: toOf(open) },
          { label: t("web_transfer", "Transfer"), value: transferOf(open) },
        ]
      : [],
  );

  // The files of the scene: the first ones, each with its subtitles.
  const FILES_SHOWN = 4;
  const sceneFiles = $derived(open ? open.files.slice(0, FILES_SHOWN) : []);
  const moreFiles = $derived(open ? Math.max(0, open.files.length - FILES_SHOWN) : 0);

  const processedFacts = $derived.by<Fact[]>(() => {
    const files = processed ?? [];
    const list: Fact[] = [];
    for (const folder of settings.data?.folders.sources ?? []) {
      const n = files.filter((file) =>
        file.path.startsWith(`${folder.replace(/\/$/, "")}/`),
      ).length;
      if (n) list.push({ label: folder, value: tn("web_n_files", n, "{n} file", "{n} files") });
    }
    const links = files.filter((file) => modeOf(file) === "link");
    const copies = files.filter((file) => modeOf(file) === "copy");
    if (links.length) {
      list.push({
        label: t("web_links", "Hard links"),
        value: t("web_links_room", "{n} · no extra room", { n: links.length }),
      });
    }
    if (copies.length) {
      list.push({
        label: t("web_copies", "Copies"),
        value: t("web_copies_room", "{n} · {size} twice", {
          n: copies.length,
          size: sizeText(
            copies.reduce((sum, file) => sum + file.size, 0),
            i18n.language,
          ),
        }),
      });
    }
    return list;
  });
</script>

{#snippet fan(op: Operation, big: boolean)}
  {@const covers = op.covers?.length ? op.covers : [null]}
  {@const square = op.media_type === "music"}
  {#if big}
    <div class="relative h-[176px] w-[320px] shrink-0" aria-hidden="true">
      {#each covers as cover, i (i)}
        {@const url = bigPosterUrl(cover)}
        {@const n = covers.length}
        {@const pos =
          n === 1
            ? [0, 0, 0]
            : n === 2
              ? [
                  [-40, 8, -5],
                  [40, 8, 5],
                ][i]
              : [
                  [-70, 18, -8],
                  [0, 0, 0],
                  [70, 18, 8],
                ][i]}
        <div
          class={[
            "absolute left-1/2 rounded-xl bg-raised bg-cover bg-center shadow-[0_30px_60px_var(--drop),inset_0_1px_0_rgb(255_255_255/0.25)]",
            square ? "top-3 -ml-[70px] size-[140px]" : "top-0 -ml-[54px] h-[162px] w-[108px]",
          ]}
          style:background-image={url ? `url("${url}")` : undefined}
          style:transform="translate({pos[0]}px, {pos[1]}px) rotate({pos[2]}deg)"
          style:z-index={n === 3 && i === 1 ? 3 : 2 - Math.min(i, 1)}
        ></div>
      {/each}
    </div>
  {:else}
    <span class="relative block h-[39px] w-[46px] shrink-0" aria-hidden="true">
      {#each covers as cover, i (i)}
        {@const url = posterUrl(cover)}
        <i
          class={[
            "absolute rounded-[5px] bg-raised bg-cover bg-center shadow-[inset_0_0_0_1px_rgb(255_255_255/0.1),0_4px_10px_rgb(0_0_0/0.45)]",
            square ? "top-[5px] size-[30px]" : "top-0 h-[39px] w-[26px]",
          ]}
          style:left="{i * 10}px"
          style:z-index={5 - i}
          style:background-image={url ? `url("${url}")` : undefined}
        ></i>
      {/each}
    </span>
  {/if}
{/snippet}

{#snippet filters()}
  <div class="mt-[22px] mb-2.5 flex items-baseline gap-5 text-[14px] font-semibold text-faint">
    <a
      href={href("/history")}
      onclick={follow}
      class={tab === "operations" ? "text-ink" : "hover:text-muted"}
      aria-current={tab === "operations" ? "page" : undefined}
    >
      {t("web_renames_word", "Renames")}<small class="ml-1 font-mono text-[11.5px] font-medium"
        >{operations?.length ?? ""}</small
      >
    </a>
    <a
      href={href("/history/processed")}
      onclick={follow}
      class={tab === "processed" ? "text-ink" : "hover:text-muted"}
      aria-current={tab === "processed" ? "page" : undefined}
    >
      {t("web_processed", "Already processed")}<small
        class="ml-1 font-mono text-[11.5px] font-medium">{processed?.length ?? ""}</small
      >
    </a>
    {#if picking}
      <button type="button" class="key key-sm -my-2 ml-auto" onclick={endPicking}>
        {t("web_done", "Done")}
      </button>
    {/if}
  </div>
{/snippet}

{#if operations?.length === 0 && tab === "operations"}
  <!-- No rename yet. -->
  <div class="flex h-full flex-col items-center justify-center px-[120px] pb-10 text-center">
    <div class="relative mb-[18px] h-[190px] w-[270px]" aria-hidden="true">
      {#each [0, 1, 2] as i (i)}
        <div
          class="absolute top-3.5 h-[150px] w-[110px] rounded-xl bg-linear-135 from-key to-surface shadow-[inset_0_0_0_1px_var(--color-line),0_20px_40px_rgb(0_0_0/0.3)]"
          style:left="{i * 80}px"
          style:transform="rotate({(i - 1) * 8}deg) translateY({i === 1 ? 0 : 14}px)"
          style:z-index={i === 1 ? 3 : 1}
        ></div>
      {/each}
    </div>
    <h1 class="m-0 text-[52px] leading-[1.04] font-[650] tracking-[-0.04em]">
      {t("web_history_empty_1", "No rename")}<span class="text-muted"
        >{t("web_history_empty_2", " yet.")}</span
      >
    </h1>
    <p class="mt-3 max-w-[640px] text-[16px] leading-[1.45] text-muted">
      {t(
        "web_history_empty_text",
        "The renames, yours and the automatic sorting's, show here. Each one can be undone while its files have not moved.",
      )}
    </p>
    <div class="mt-[26px]">
      <a href={href("/")} onclick={follow} class="key key-primary">
        {t("web_go_analysis", "Go to the Analysis")}
      </a>
    </div>
  </div>
{:else}
  <Split>
    {#if tab === "operations"}
      <h1 class="m-0 text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
        {t("history", "History")}<span class="text-muted">.</span>
      </h1>
      {#if operations?.length}
        <p class="mt-3 text-[15px] leading-[1.45] text-muted">
          {tn(
            "web_history_lead",
            operations.length,
            "{n} rename since {date}, {files} files.",
            "{n} renames since {date}, {files} files.",
            {
              date: shortDay(oldest),
              files: total,
            },
          )}
          {t("web_history_lead_undo", "Each one can be undone while its files have not moved.")}
        </p>
      {/if}
      {@render filters()}
      {#if error}<p class="text-[14px] text-danger" role="alert">{error}</p>{/if}
      <div class="-mx-2.5">
        {#each sections as section (section.key)}
          {@const opened = !section.folded || unfolded.includes(section.key)}
          {#if opened}
            <p class="label mt-[18px] mb-1.5 px-3.5 first:mt-1">{sectionTitle(section)}</p>
            {#each section.operations as op (op.id)}
              <div
                role="button"
                tabindex="0"
                aria-current={op.id === openId ? "true" : undefined}
                class={[
                  "grid cursor-pointer grid-cols-[54px_46px_minmax(0,1fr)_auto] items-center gap-x-4 rounded-xl px-3.5 py-[11px]",
                  op.id === openId
                    ? "bg-raised shadow-[inset_0_1px_0_var(--color-hi)]"
                    : "hover:bg-raised/60",
                ]}
                onclick={() => openOperation(op)}
                onkeydown={(event) => event.key === "Enter" && openOperation(op)}
              >
                <span class="font-mono text-[13px] whitespace-nowrap text-faint">
                  {section.kind === "today" || section.kind === "yesterday"
                    ? time(op.date)
                    : shortDay(op.date)}
                </span>
                <div class={op.undone ? "opacity-50" : ""}>{@render fan(op, false)}</div>
                <div class="min-w-0">
                  <div
                    class={[
                      "truncate text-[16px] leading-[22px] font-semibold tracking-[-0.02em]",
                      op.undone && "opacity-50",
                    ]}
                  >
                    {opTitle(op)}
                  </div>
                  <div class="truncate text-[13px] text-muted">
                    {t("web_from_to", "From {from} · to {to}", {
                      from: fromOf(op),
                      to: toOf(op),
                    })}
                  </div>
                </div>
                <span class="flex items-center justify-end gap-2 text-[13px] text-muted">
                  {#if op.auto}<span class="tag">auto</span>{/if}
                  {#if op.undone}
                    {t("history_undone", "Undone")}
                  {:else if op.partly_undone}
                    {t("history_partly_undone", "Partly undone")}
                  {/if}
                </span>
              </div>
            {/each}
          {:else}
            <div
              class="mt-3.5 grid grid-cols-[54px_minmax(0,1fr)_auto] items-center gap-x-4 px-3.5 py-2.5"
            >
              <span class="font-mono text-[13px] text-faint">{shortDay(section.date)}</span>
              <span class="text-[15px] text-muted">
                {tn(
                  "web_month_renames",
                  section.operations.length,
                  "{n} rename in {month}, {files} files",
                  "{n} renames in {month}, {files} files",
                  {
                    month: new Intl.DateTimeFormat(i18n.language, { month: "long" }).format(
                      section.date,
                    ),
                    files: section.operations.reduce((sum, op) => sum + videoFiles(op).length, 0),
                  },
                )}
              </span>
              <button
                type="button"
                class="key key-sm"
                onclick={() => (unfolded = [...unfolded, section.key])}
              >
                {t("web_show", "Show")}
              </button>
            </div>
          {/if}
        {/each}
      </div>
      <div class="flex-1"></div>
      <p class="px-1 pt-3.5 text-[13px] text-faint">
        {t("web_history_note", "The history is kept on the server. The last 100 renames are kept.")}
      </p>
    {:else}
      <h1 class="m-0 text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
        {t("web_processed", "Already processed")}<span class="text-muted">.</span>
      </h1>
      <p class="mt-3 text-[15px] leading-[1.45] text-muted">
        {tn(
          "web_processed_lead",
          processed?.length ?? 0,
          "Put away with a hard link or a copy, this file also stays in the downloads. The analyses leave it out while it does not change.",
          "Put away with a hard link or a copy, these {n} files also stay in the downloads. The analyses leave them out while they do not change.",
        )}
      </p>
      {@render filters()}
      {#if error}<p class="text-[14px] text-danger" role="alert">{error}</p>{/if}
      <div class="-mx-2.5 grid content-start gap-0.5">
        {#each processed ?? [] as file (file.path)}
          {@const isChosen = chosen.includes(file.path)}
          <div
            role="button"
            tabindex="0"
            class={[
              "grid h-[62px] cursor-pointer grid-cols-[36px_minmax(0,1fr)_auto_64px] items-center gap-x-4 rounded-xl px-3.5",
              isChosen ? "bg-accent-soft" : "hover:bg-raised/60",
            ]}
            onclick={(event) => clickFile(file, event)}
            onkeydown={(event) => event.key === " " && toggle(file.path)}
          >
            <Thumb
              poster={coverOf(file.path)}
              chosen={isChosen}
              marks={picking}
              label={t("web_choose_row", "Choose {title}", { title: name(file.path) })}
              onmark={() => {
                picking = true;
                toggle(file.path);
              }}
            />
            <div class="min-w-0">
              <div class="truncate font-mono text-[13.5px]">{name(file.path)}</div>
              <div class="mt-[3px] truncate text-[12.5px] text-faint">
                {t("web_put_as", "put away as")}
                <code class="font-mono text-[12px] text-muted">{name(file.target)}</code>
                · {modeOf(file) === "copy"
                  ? t("web_mode_copy_word", "copy")
                  : t("web_mode_link_word", "hard link")}
              </div>
            </div>
            <span class="text-right font-mono text-[12.5px] text-faint">{shortDay(file.date)}</span>
            <span class="text-right font-mono text-[12.5px] text-faint"
              >{sizeText(file.size, i18n.language)}</span
            >
          </div>
        {:else}
          <p class="px-3.5 py-6 text-[14px] text-muted">
            {t("web_processed_empty", "No file processed yet.")}
          </p>
        {/each}
      </div>
      <div class="flex-1"></div>
      <div class="pt-4">
        {#if chosen.length}
          <button type="button" class="key key-primary" onclick={analyzeAgain}>
            {t("web_analyze_again", "Analyze again")}<span class="legend">{chosen.length}</span>
          </button>
        {:else if processed?.length}
          <p class="text-[13px] text-muted">
            {t(
              "web_processed_hint",
              "Choose the files to take back: the mark of a thumbnail, or Cmd/Ctrl-click.",
            )}
          </p>
        {/if}
      </div>
    {/if}

    {#snippet scene()}
      {#if tab === "operations" && open}
        <div class="pt-0"></div>
        {@render fan(open, true)}
        <div
          class="-mt-1 h-5 w-[250px] rounded-[50%] bg-[radial-gradient(closest-side,var(--drop),transparent)]"
        ></div>
        <p class="label mt-3.5 text-center">{when(open.date)}</p>
        <p class="mt-1.5 text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
          {opTitle(open)}
        </p>
        <div class="mt-[18px] w-full"><Facts {facts} /></div>
        <div class="mt-4 grid w-full">
          {#each sceneFiles as file (file.index)}
            {@const back = file.undone}
            {@const left = report?.skipped.find((one) => one.target === file.target)}
            <div
              class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-t border-line py-[7px] first:border-0"
            >
              <div class="min-w-0">
                <div
                  class={[
                    "truncate font-mono text-[12.5px]",
                    back && "text-faint line-through decoration-line-strong",
                  ]}
                  title={file.target}
                >
                  {name(file.target)}
                </div>
                {#if left}
                  <div class="mt-0.5 truncate text-[12px] text-caution">
                    {reasonText(left.reason)}
                  </div>
                {:else}
                  <div
                    class={["mt-0.5 truncate text-[12px] text-faint", !file.follows && "font-mono"]}
                  >
                    {file.follows
                      ? t("web_subtitle_follows", "subtitle, follows its video")
                      : t("web_was", "was {name}", { name: name(file.source) })}
                  </div>
                {/if}
              </div>
              {#if left}
                <span class="text-right text-[12.5px] text-caution"
                  >{t("web_stayed", "stayed")}</span
                >
              {:else if back}
                {#if !file.follows}
                  <span class="text-[12.5px] text-muted"
                    >✓ {t("web_put_back_done", "Put back")}</span
                  >
                {/if}
              {:else if !file.follows && !open.undone}
                <button
                  type="button"
                  class="key key-sm size-[30px] p-0 text-muted"
                  title={t("history_undo_file", "Put this file back")}
                  aria-label={t("history_undo_file", "Put this file back")}
                  onclick={() => {
                    asking = { index: file.index };
                    report = null;
                  }}
                >
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 16 16"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="1.5"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"><path d="M3 8a5 5 0 1 0 1.5-3.5M3 3v2.5h2.5" /></svg
                  >
                </button>
              {/if}
            </div>
          {/each}
          {#if moreFiles}
            <p class="border-t border-line pt-[9px] text-[13px] text-faint">
              {tn("web_more_files", moreFiles, "and {n} other file", "and {n} other files")}
            </p>
          {/if}
        </div>

        {#if report}
          <p class="mt-[18px] self-stretch text-center text-[14px] leading-[1.45] text-muted">
            <b class="font-medium text-ink">
              {tn(
                "web_files_back",
                report.restored.length,
                "{n} file put back.",
                "{n} files put back.",
              )}
            </b>
            {#if report.skipped.length}
              <br /><span class="text-caution"
                >{tn(
                  "web_files_stayed",
                  report.skipped.length,
                  "{n} left where it is",
                  "{n} left where they are",
                )}</span
              >: {reasonText(report.skipped[0].reason)}.
            {/if}
          </p>
        {/if}
        {#if asking}
          <div
            class="mt-[22px] self-stretch rounded-xl bg-surface px-4 py-3.5 shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line)]"
          >
            <p class="mb-3 text-[14px] leading-[1.45] text-muted">
              {tn(
                "web_undo_ask",
                backCount(open, asking.index),
                "Put this file back where it was?",
                "Put these {n} files back where they were?",
              )}
            </p>
            <div class="flex gap-2.5">
              <button type="button" class="key key-primary" disabled={busy} onclick={runUndo}>
                {t("web_undo_yes", "Yes, undo")}
              </button>
              <button type="button" class="key" onclick={() => (asking = null)}>
                {t("web_keep", "Keep")}
              </button>
            </div>
          </div>
        {:else if open.undone && !report}
          <p class="mt-[18px] text-center text-[14px] text-muted">
            {t("web_op_undone", "Undone: the files are back where they were.")}
          </p>
        {:else if !open.undone}
          <div class="mt-4 flex justify-center">
            <button
              type="button"
              class="key"
              onclick={() => {
                asking = {};
                report = null;
              }}
            >
              {open.partly_undone
                ? t("web_undo_rest", "Undo the rest")
                : t("web_undo_this", "Undo this")}
            </button>
          </div>
        {/if}
      {:else if tab === "processed" && chosen.length}
        {@const covers = chosen.map((path) => coverOf(path)).filter((c): c is string => !!c)}
        <div class="mt-10"></div>
        {#if covers.length}
          <div
            class="relative h-[230px] shrink-0"
            style:width="{140 + (Math.min(covers.length, 4) - 1) * 60}px"
          >
            {#each covers.slice(0, 4) as cover, i (i)}
              <div
                class="absolute top-0 h-[210px] w-[140px] rounded-xl bg-raised bg-cover bg-center shadow-[0_30px_60px_var(--drop),inset_0_1px_0_rgb(255_255_255/0.25)]"
                style:left="{i * 60}px"
                style:z-index={10 - i}
                style:background-image="url(&quot;{bigPosterUrl(cover)}&quot;)"
              ></div>
            {/each}
          </div>
        {/if}
        <p class="mt-6 text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
          {tn("web_files_chosen", chosen.length, "{n} file chosen", "{n} files chosen")}
        </p>
        <p class="mt-[18px] max-w-[340px] text-center text-[14px] leading-[1.5] text-muted">
          {t(
            "web_processed_again_text",
            "The next analysis takes them back as if they had just arrived. What is already put away does not move.",
          )}
        </p>
      {:else if tab === "processed" && processed?.length}
        <p class="mt-16 text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
          {tn("web_files_left_out", processed.length, "{n} file left out", "{n} files left out")}
        </p>
        <p class="mt-1.5 text-center text-[15px] text-muted">
          {t("web_processed_have_place", "They already have their place.")}
        </p>
        <div class="mt-[26px] w-full"><Facts facts={processedFacts} /></div>
      {/if}
    {/snippet}
  </Split>
{/if}
