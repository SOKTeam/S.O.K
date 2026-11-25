<script lang="ts">
  // The Analysis, home of the server: what waits, by media type, the files
  // whose type is a guess, the last rename with its undo; on the scene, the
  // covers waiting, the source folders and the room on the disks.
  import { onMount } from "svelte";

  import Split from "../components/layout/Split.svelte";
  import Facts, { type Fact } from "../components/scene/Facts.svelte";
  import Fan from "../components/scene/Fan.svelte";
  import { posterColor } from "../lib/color";
  import { loadDisks, sizeText, type Disks } from "../lib/disks";
  import { errorText, stopText, watchProblemText } from "../lib/errors";
  import { loadHistory, undo, type Operation } from "../lib/history";
  import { i18n, t, tn } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { follow, href } from "../lib/router.svelte";
  import { posterUrl } from "../lib/rows";
  import { analysis, confirmType, startScan, type ToCheck } from "../lib/scan.svelte";
  import { session } from "../lib/session.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";
  import { loadWatch, watch } from "../lib/watch.svelte";

  let error = $state("");
  // The file confirmed, while its row is searched.
  let confirming = $state("");
  let disks = $state<Disks | null>(null);
  let last = $state<Operation | null>(null);
  let asking = $state(false);
  let undoing = $state(false);

  const summary = $derived(analysis.summary);
  const scan = $derived(summary?.scan ?? null);
  const running = $derived(scan?.status === "running");
  const auto = $derived(watch.status);
  const sources = $derived(settings.data?.folders.sources ?? []);
  const waiting = $derived(MEDIA_PAGES.filter((page) => summary?.counts[page.mediaType!]?.total));
  const total = $derived(
    MEDIA_PAGES.reduce((sum, page) => sum + (summary?.counts[page.mediaType!]?.total ?? 0), 0),
  );
  const covers = $derived(
    MEDIA_PAGES.flatMap((page) => summary?.covers?.[page.mediaType!]?.slice(0, 1) ?? []).slice(
      0,
      3,
    ),
  );
  // The stop of the automatic sorting shows unless it is the one of the
  // analysis shown.
  const autoProblems = $derived(
    (auto?.last_run?.errors ?? []).filter(
      (problem) => problem.media_type || auto?.last_run?.scan !== scan?.id,
    ),
  );

  onMount(() => {
    loadWatch().catch(() => {});
    if (!settings.data) loadSettings().catch(() => {});
    return () => setLight(null);
  });

  // The disks and the last rename, read again after each analysis.
  $effect(() => {
    if (running) return;
    void scan?.id;
    loadDisks()
      .then((found) => (disks = found))
      .catch(() => {});
    loadHistory()
      .then((operations) => (last = operations.find((op) => !op.undone) ?? null))
      .catch(() => {});
  });

  // The light takes the color of the first cover.
  $effect(() => {
    const url = posterUrl(covers[0] ?? null);
    if (!url) {
      setLight(null);
      return;
    }
    posterColor(url).then((color) => setLight(color ?? "251, 96, 72"));
  });

  async function analyze() {
    error = "";
    try {
      await startScan();
    } catch (exc) {
      error = errorText(exc);
    }
  }

  async function confirm(item: ToCheck, kind: string) {
    error = "";
    confirming = item.path;
    try {
      const stop = await confirmType(item.path, kind);
      if (stop) error = stopText(stop);
    } catch (exc) {
      error = errorText(exc);
    } finally {
      confirming = "";
    }
  }

  async function undoLast() {
    if (!last) return;
    undoing = true;
    error = "";
    try {
      await undo(last.id);
      last = null;
      asking = false;
    } catch (exc) {
      error = errorText(exc);
    } finally {
      undoing = false;
    }
  }

  function time(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, { timeStyle: "short" }).format(new Date(value));
  }

  /** "Aujourd'hui à 09:30", "Hier à 21:42", "19 nov. à 03:15". */
  function when(value: string): string {
    const date = new Date(value);
    const today = new Date();
    const days = Math.round(
      (new Date(today.toDateString()).getTime() - new Date(date.toDateString()).getTime()) /
        86400000,
    );
    if (days === 0) return t("web_today_at", "Today at {time}", { time: time(value) });
    if (days === 1) return t("web_yesterday_at", "Yesterday at {time}", { time: time(value) });
    const day = new Intl.DateTimeFormat(i18n.language, { day: "numeric", month: "short" }).format(
      date,
    );
    return t("web_day_at", "{day} at {time}", { day, time: time(value) });
  }

  /** The destination folder of an operation: the folder of its type. */
  function destinationOf(operation: Operation): string {
    const target = operation.files.find((file) => !file.follows)?.target ?? "";
    const folders = settings.data?.folders[operation.media_type] ?? [];
    return (
      folders.find((folder) => target.startsWith(`${folder.replace(/\/$/, "")}/`)) ??
      target.split("/").slice(0, -1).join("/")
    );
  }

  function videos(operation: Operation): number {
    return operation.files.filter((file) => !file.follows && !file.undone).length;
  }

  function fileName(path: string): string {
    return path.split("/").pop() ?? path;
  }

  function reasonText(reason: string): string {
    switch (reason) {
      case "episode number without season":
        return t("drop_reason_weak_episode", "Episode number without a season");
      case "season folder without episode number":
        return t("drop_reason_season_folder", "In a season folder, without an episode number");
      case "video next to episodes":
        return t("drop_reason_among_episodes", "Video among episodes: a bonus?");
      case "disc image":
        return t("drop_reason_disc_image", "Disc image: a game or a video disc?");
      default:
        return reason;
    }
  }

  const KIND_NAMES: Record<string, () => string> = {
    movie: () => t("movie", "Movie"),
    episode: () => t("web_kind_episode", "Episode"),
    album: () => t("web_kind_album", "Album"),
    track: () => t("web_kind_track", "Track"),
    book: () => t("book", "Book"),
    game: () => t("game", "Game"),
  };

  /** The types offered for a file to check: its guess first, then the
   * other one its reason hesitates with. */
  function kindsOf(item: ToCheck): string[] {
    const other: Record<string, string> = {
      "disc image": item.kind === "game" ? "movie" : "game",
      "video next to episodes": item.kind === "episode" ? "movie" : "episode",
      "episode number without season": item.kind === "episode" ? "movie" : "episode",
      "season folder without episode number": item.kind === "episode" ? "movie" : "episode",
    };
    return other[item.reason] ? [item.kind, other[item.reason]] : [item.kind];
  }

  /** "6 recognized, 2 to pick, 1 not found", the parts that are not 0. */
  function detail(mediaType: string): { text: string; tone: string }[] {
    const counts = summary!.counts[mediaType];
    const parts = [];
    if (counts.ok) {
      parts.push({
        text: tn("web_n_ready", counts.ok, "{n} recognized", "{n} recognized"),
        tone: "",
      });
    }
    if (counts.ambiguous) {
      parts.push({
        text: tn("web_n_to_pick", counts.ambiguous, "{n} to pick", "{n} to pick"),
        tone: "text-accent-text",
      });
    }
    if (counts.missing) {
      parts.push({
        text: tn("web_n_not_found", counts.missing, "{n} not found", "{n} not found"),
        tone: "text-caution",
      });
    }
    if (counts.pending) {
      parts.push({
        text: tn(
          "web_n_not_searched",
          counts.pending,
          "{n} not searched yet",
          "{n} not searched yet",
        ),
        tone: "text-faint",
      });
    }
    return parts;
  }

  const sourceFacts = $derived<Fact[]>(
    (summary?.sources ?? []).map((source) => ({
      label: source.path,
      value: source.missing
        ? t("web_folder_missing", "not found")
        : tn("web_n_files", source.files, "{n} file", "{n} files"),
      tone: source.missing ? "caution" : undefined,
    })),
  );

  const room = $derived.by(() => {
    const disk = disks?.disks[0];
    if (!disk) return "";
    const free = t("web_free_on", "{size} free on {path}", {
      size: sizeText(disk.free, i18n.language),
      path: disk.path,
    });
    if (!disks!.movie_size) return `${free}.`;
    const n = Math.floor(disk.free / disks!.movie_size);
    return tn(
      "web_room_movies",
      n,
      "{free}: room for about {n} movie.",
      "{free}: room for about {n} movies.",
      {
        free,
      },
    );
  });

  const sourcesText = $derived(
    sources.length
      ? new Intl.ListFormat(i18n.language, { type: "conjunction" }).format(sources)
      : "",
  );
</script>

{#snippet lead()}
  {#if running}
    {@const progress = scan?.progress}
    {#if progress?.phase === "search" && progress.total}
      {t("web_lead_searching", "Searching the titles… {done} / {total}.", {
        done: progress.done,
        total: progress.total,
      })}
    {:else}
      {t("web_progress_detect", "Sorting the files…")}
    {/if}
    {t("web_lead_keeps_going", "You can change pages, the analysis goes on.")}
  {:else if !sources.length}
    {t("web_lead_no_source", "No source folder yet: choose one in Settings.")}
  {:else if auto?.enabled}
    {t(
      "web_lead_auto",
      "In {sources}. The automatic sorting puts away what is ready every {minutes} min.",
      {
        sources: sourcesText,
        minutes: auto.minutes,
      },
    )}
  {:else}
    {t("web_lead_manual", "In {sources}. Analyze to see what waits.", { sources: sourcesText })}
  {/if}
{/snippet}

<Split>
  <div class="mb-2 text-[11px] leading-4 font-semibold tracking-[0.08em] text-faint uppercase">
    {#if session.current?.username}
      {t("web_hello", "Hello {name}", { name: session.current.username })}
    {/if}
    {#if scan?.finished}
      · {t("web_last_analysis_at", "last analysis at {time}", { time: time(scan.finished) })}
    {/if}
  </div>
  <h1 class="m-0 text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
    {#if running}
      {t("web_title_running", "Analysis in progress")}<span class="text-muted">.</span>
    {:else if total}
      {tn("web_title_files", total, "{n} file", "{n} files")}
      <span class="text-muted">{t("web_title_to_sort", "to sort.")}</span>
    {:else}
      {t("web_title_nothing", "Nothing to sort")}<span class="text-muted">.</span>
    {/if}
  </h1>
  <p class="mt-3 text-[15px] leading-[1.45] text-muted">{@render lead()}</p>
  {#if running}
    {@const progress = scan?.progress}
    <div
      class="mt-4 h-[3px] w-[420px] max-w-full overflow-hidden rounded-sm bg-line-strong"
      role="progressbar"
      aria-label={t("web_title_running", "Analysis in progress")}
    >
      <div
        class={[
          "h-full rounded-sm bg-accent transition-[width]",
          !(progress?.phase === "search" && progress.total) && "w-1/3 animate-pulse",
        ]}
        style:width={progress?.phase === "search" && progress.total
          ? `${(100 * progress.done) / progress.total}%`
          : undefined}
      ></div>
    </div>
  {/if}

  <!-- What went wrong, in plain words. -->
  {#if error || scan?.error || scan?.status === "interrupted" || autoProblems.length}
    <div class="mt-4 grid gap-1 text-[14px]" role="alert">
      {#if error}<p class="text-danger">{error}</p>{/if}
      {#if scan?.error}
        <p class="text-caution">
          {stopText(scan.error)}
          {#each scan.error.others ?? [] as other (other.service)}
            {stopText(other)}
          {/each}
          {#if scan.error.code === "missing_key" || scan.error.code === "key_refused"}
            <a href={href("/settings/sources")} onclick={follow} class="link ml-1">
              {t("settings", "Settings")}
            </a>
          {/if}
        </p>
      {/if}
      {#if scan?.status === "interrupted"}
        <p class="text-caution">
          {t(
            "web_scan_interrupted",
            "The last analysis was cut by a restart of the server: analyze again.",
          )}
        </p>
      {/if}
      {#each autoProblems as problem, i (i)}
        <p class="text-caution">{watchProblemText(problem)}</p>
      {/each}
    </div>
  {/if}

  {#if waiting.length}
    <div class="-mx-2.5 mt-[26px] grid gap-0.5">
      {#each waiting as page (page.path)}
        {@const counts = summary!.counts[page.mediaType!]}
        {@const pageCovers = summary!.covers?.[page.mediaType!] ?? []}
        <div
          class="grid grid-cols-[92px_minmax(0,1fr)_auto] items-center gap-[18px] rounded-xl px-3.5 py-3 hover:bg-raised/60"
        >
          <div class="relative h-[54px]">
            {#each pageCovers.length ? pageCovers : [null] as cover, i (i)}
              {@const url = posterUrl(cover)}
              <div
                class={[
                  "absolute rounded bg-raised bg-cover bg-center shadow-[0_4px_10px_rgb(0_0_0/0.35),inset_0_0_0_1px_rgb(255_255_255/0.1)]",
                  page.mediaType === "music" ? "top-[5px] size-11" : "top-0 h-[54px] w-9",
                ]}
                style:left="{i * 22}px"
                style:z-index={5 - i}
                style:background-image={url ? `url("${url}")` : undefined}
              ></div>
            {/each}
          </div>
          <div class="min-w-0">
            <div class="text-[19px] font-semibold tracking-[-0.02em]">
              {t(page.key, page.english)}<small
                class="ml-1.5 font-mono text-[13px] font-medium text-faint">{counts.total}</small
              >
            </div>
            <div class="mt-[3px] text-[13.5px] text-muted">
              {#each detail(page.mediaType!) as part, i (i)}{i ? ", " : ""}<span class={part.tone}
                  >{part.text}</span
                >{/each}
            </div>
          </div>
          <a href={href(page.path)} onclick={follow} class="key key-sm">{t("web_see", "See")}</a>
        </div>
      {/each}
    </div>
  {/if}

  {#if summary?.to_check.length && !running}
    <p class="label mt-[26px] mb-2">
      {t("web_to_check_count", "To check · {n}", { n: summary.to_check.length })}
    </p>
    {#each summary.to_check as item (item.path)}
      <div
        class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-t border-line py-2.5"
      >
        <div class="min-w-0">
          <p class="truncate font-mono text-[13px]" title={item.path}>{fileName(item.path)}</p>
          <p class="mt-[3px] text-[13px] text-muted">{reasonText(item.reason)}</p>
        </div>
        <div class="flex gap-1.5">
          {#each kindsOf(item) as kind (kind)}
            <button
              type="button"
              class="key key-sm"
              disabled={confirming !== ""}
              onclick={() => confirm(item, kind)}
            >
              {confirming === item.path && kind === kindsOf(item)[0]
                ? t("searching", "Searching...")
                : (KIND_NAMES[kind]?.() ?? kind)}
            </button>
          {/each}
        </div>
      </div>
    {/each}
  {/if}

  {#if last && !running}
    <div
      class="mt-[22px] flex flex-wrap items-center gap-x-4 gap-y-2 rounded-xl bg-surface px-4 py-3.5 text-[14px] text-muted shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line)]"
    >
      {#if asking}
        <span class="flex-1">
          {tn(
            "web_undo_ask",
            videos(last),
            "Put this file back where it was?",
            "Put these {n} files back where they were?",
          )}
        </span>
        <button type="button" class="key key-sm key-primary" disabled={undoing} onclick={undoLast}>
          {t("web_undo_yes", "Yes, undo")}
        </button>
        <button type="button" class="key key-sm" onclick={() => (asking = false)}>
          {t("web_keep", "Keep")}
        </button>
      {:else}
        <span class="flex-1">
          <b class="font-medium text-ink">
            {last.auto
              ? tn(
                  "web_last_auto",
                  videos(last),
                  "{when}, the automatic sorting put away {n} file",
                  "{when}, the automatic sorting put away {n} files",
                  { when: when(last.date) },
                )
              : tn(
                  "web_last_manual",
                  videos(last),
                  "{when}, you put away {n} file",
                  "{when}, you put away {n} files",
                  { when: when(last.date) },
                )}
          </b>
          {t("web_last_to", "to")}
          <code class="font-mono text-[13px]">{destinationOf(last)}</code>.
        </span>
        <button type="button" class="key key-sm" onclick={() => (asking = true)}>
          {t("web_undo_this", "Undo this")}
        </button>
      {/if}
    </div>
  {/if}

  <div class="flex-1"></div>
  <div class="flex flex-wrap items-center gap-3.5 pt-4">
    {#if running}
      <button type="button" class="key" disabled>{t("web_analyzing", "Analyzing…")}</button>
    {:else}
      <button type="button" class="key key-primary" disabled={!sources.length} onclick={analyze}>
        {t("web_analyze", "Analyze")}
      </button>
    {/if}
    {#if scan?.processed}
      <span class="text-[13.5px] text-muted">
        {tn(
          "web_processed_left",
          scan.processed,
          "{n} file already processed is left out.",
          "{n} files already processed are left out.",
        )}
      </span>
      <a href={href("/history/processed")} onclick={follow} class="key key-sm">
        {t("web_show_them", "Show them")}
      </a>
    {/if}
  </div>

  {#snippet scene()}
    {#if covers.length}
      <Fan posters={covers} />
    {:else}
      <div class="relative mt-2.5 h-[200px] w-[270px] shrink-0" aria-hidden="true">
        {#each [0, 1, 2] as i (i)}
          <div
            class="absolute top-3.5 h-[165px] w-[110px] rounded-xl bg-linear-135 from-key to-surface shadow-[inset_0_0_0_1px_var(--color-line),0_20px_40px_rgb(0_0_0/0.3)]"
            style:left="{i * 80}px"
            style:transform="rotate({(i - 1) * 8}deg) translateY({i === 1 ? 0 : 14}px)"
            style:z-index={i === 1 ? 3 : 1}
          ></div>
        {/each}
      </div>
    {/if}
    {#if sourceFacts.length}
      <p class="label mt-[30px] mb-3">{t("web_sources", "Sources")}</p>
      <Facts facts={sourceFacts} />
    {/if}
    {#if disks?.disks.length}
      <p class="label mt-[30px] mb-3">{t("web_your_disks", "Your disks")}</p>
      {#each disks.disks.slice(0, 3) as disk (disk.path)}
        <div class="w-full">
          <div class="flex justify-between gap-3 text-[14px] text-muted">
            <span class="truncate">{disk.path}</span>
            <span class="shrink-0 font-mono text-[13px] text-ink">
              {t("web_used_of", "{used} of {total}", {
                used: sizeText(disk.total - disk.free, i18n.language),
                total: sizeText(disk.total, i18n.language),
              })}
            </span>
          </div>
          <div class="mt-[9px] mb-4 h-1 overflow-hidden rounded-sm bg-line-strong">
            <div
              class="h-full rounded-sm bg-ink"
              style:width="{disk.total ? (100 * (disk.total - disk.free)) / disk.total : 0}%"
            ></div>
          </div>
        </div>
      {/each}
      {#if room}<p class="self-start text-[13.5px] text-muted">{room}</p>{/if}
    {/if}
  {/snippet}
</Split>
