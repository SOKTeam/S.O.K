<script lang="ts">
  import { onMount } from "svelte";

  import Icon from "../components/Icon.svelte";
  import { errorText, stopText, watchProblemText } from "../lib/errors";
  import { i18n, t } from "../lib/i18n.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { follow } from "../lib/router.svelte";
  import { analysis, confirmType, startScan, type Counts, type ToCheck } from "../lib/scan.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";
  import { loadWatch, watch } from "../lib/watch.svelte";

  let error = $state("");
  // The type picked for each file to check, before it is confirmed.
  let kinds = $state<Record<string, string>>({});
  // The file confirmed, while its row is searched.
  let confirming = $state("");

  onMount(() => {
    loadWatch().catch(() => {});
    if (!settings.data) loadSettings().catch(() => {});
  });

  const summary = $derived(analysis.summary);
  const auto = $derived(watch.status);
  const scan = $derived(summary?.scan ?? null);
  const sources = $derived(settings.data?.folders.sources ?? []);
  // The stop of its analysis shows below when it is the analysis shown.
  const autoProblems = $derived(
    (auto?.last_run?.errors ?? []).filter(
      (problem) => problem.media_type || auto?.last_run?.scan !== scan?.id,
    ),
  );
  const totals = $derived.by(() => {
    const sum: Counts = { total: 0, ok: 0, ambiguous: 0, missing: 0, pending: 0 };
    for (const page of MEDIA_PAGES) {
      const counts = summary?.counts[page.mediaType!];
      if (!counts) continue;
      for (const key of Object.keys(sum) as (keyof Counts)[]) sum[key] += counts[key];
    }
    return sum;
  });
  const hasProblems = $derived(
    Boolean(
      error ||
      scan?.error ||
      scan?.status === "interrupted" ||
      scan?.missing_sources.length ||
      autoProblems.length,
    ),
  );

  async function analyze() {
    error = "";
    try {
      await startScan();
    } catch (exc) {
      error = errorText(exc);
    }
  }

  async function confirm(item: ToCheck) {
    error = "";
    confirming = item.path;
    try {
      const stop = await confirmType(item.path, kinds[item.path] ?? item.kind);
      if (stop) error = stopText(stop);
    } catch (exc) {
      error = errorText(exc);
    } finally {
      confirming = "";
    }
  }

  function date(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
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

  const KINDS = [
    ["movie", () => t("movie", "Movie")],
    ["episode", () => t("tv_series", "TV Series")],
    ["album", () => t("albums", "Albums")],
    ["track", () => t("tracks", "Tracks")],
    ["book", () => t("book", "Book")],
    ["game", () => t("game", "Game")],
  ] as const;
</script>

{#snippet count(n: number, tone: string)}
  <td class={["px-4 py-2.5 text-right tabular-nums", n ? tone : "text-faint"]}>
    {n || "—"}
  </td>
{/snippet}

<div class="mx-auto flex max-w-5xl flex-col pb-16">
  <div class="flex items-center justify-between gap-4">
    <h1 class="text-3xl font-bold">{t("web_analysis", "Analysis")}</h1>
    <button class="button px-5 py-2" disabled={analysis.running} onclick={analyze}>
      {t("web_analyze", "Analyze")}
    </button>
  </div>

  <!-- Where the analysis looks, when it last ran, and the automatic sorting. -->
  <div class="mt-6 overflow-hidden rounded-xl border border-line bg-card">
    <div class="grid divide-line sm:grid-cols-[1.4fr_1fr_1fr] sm:divide-x">
      <div class="min-w-0 px-4.5 py-3.5">
        <p class="label">{t("source_folders", "Source Folders")}</p>
        {#if sources.length}
          {#each sources as source (source)}
            <!-- Cut at the start: the end of a path tells it apart. -->
            <p class="mt-1 truncate text-left font-mono text-sm [direction:rtl]" title={source}>
              <bdi>{source}</bdi>
            </p>
          {/each}
        {:else if settings.data}
          <a href="/settings" onclick={follow} class="link mt-1 inline-block">
            {t("web_add_source", "Add a source folder")}
          </a>
        {/if}
      </div>
      <div class="min-w-0 px-4.5 py-3.5">
        <p class="label">{t("web_last_analysis_label", "Last analysis")}</p>
        <p class="mt-1 truncate text-sm">
          {#if scan?.status === "running"}
            {@const progress = scan.progress}
            {progress?.phase === "search" && progress.total
              ? t("web_progress_search", "Searching… {done} / {total}", {
                  done: progress.done,
                  total: progress.total,
                })
              : t("web_progress_detect", "Sorting the files…")}
          {:else if scan}
            {date(scan.started)}
            {#if scan.auto}
              <span class="text-muted">· {t("web_automatic", "automatic")}</span>
            {/if}
          {:else}
            <span class="text-muted">{t("web_never", "Never")}</span>
          {/if}
        </p>
      </div>
      <div class="min-w-0 px-4.5 py-3.5">
        <p class="label">{t("web_auto_sort", "Automatic sorting")}</p>
        {#if auto?.enabled}
          <p
            class="mt-1 truncate text-sm"
            title={auto.last_check
              ? t("web_last_check", "Last check: {date}", { date: date(auto.last_check) })
              : undefined}
          >
            {t("web_auto_sort_every", "On, every {minutes} min", { minutes: auto.minutes })}
          </p>
          {#if auto.last_run}
            <p class="mt-0.5 truncate text-xs text-muted">
              {t("web_auto_sort_last", "Last: {date} · {n} renamed", {
                date: date(auto.last_run.date),
                n: auto.last_run.renamed,
              })}
            </p>
          {/if}
        {:else if auto}
          <p class="mt-1 text-sm">
            {t("web_auto_sort_disabled", "Off")} ·
            <a href="/settings" onclick={follow} class="link">{t("web_turn_on", "Turn on")}</a>
          </p>
        {/if}
      </div>
    </div>
    {#if scan?.status === "running"}
      {@const progress = scan.progress}
      <div class="h-1 bg-hover" role="progressbar" aria-label={t("web_analysis", "Analysis")}>
        <div
          class={[
            "h-full bg-accent transition-all",
            !(progress?.phase === "search" && progress.total) && "w-1/3 animate-pulse",
          ]}
          style:width={progress?.phase === "search" && progress.total
            ? `${(100 * progress.done) / progress.total}%`
            : undefined}
        ></div>
      </div>
    {/if}
  </div>

  {#if hasProblems}
    <div
      class="mt-3 divide-y divide-line rounded-xl border border-line bg-card text-sm"
      role="alert"
    >
      {#if error}
        <p class="px-4.5 py-3 text-error">{error}</p>
      {/if}
      {#if scan?.error}
        <div class="flex items-center justify-between gap-4 px-4.5 py-3">
          <div class="text-error">
            <p>{stopText(scan.error)}</p>
            {#each scan.error.others ?? [] as other (other.service)}
              <p class="mt-1">{stopText(other)}</p>
            {/each}
          </div>
          {#if scan.error.code === "missing_key" || scan.error.code === "key_refused"}
            <a href="/settings" onclick={follow} class="link shrink-0">
              {t("settings", "Settings")}
            </a>
          {/if}
        </div>
      {/if}
      {#if scan?.status === "interrupted"}
        <p class="px-4.5 py-3 text-warn">
          {t(
            "web_scan_interrupted",
            "The last analysis was cut by a restart of the server: analyze again.",
          )}
        </p>
      {/if}
      {#if scan?.missing_sources.length}
        <p class="px-4.5 py-3 text-warn">
          {t("web_missing_sources", "Source folders not found: {folders}", {
            folders: scan.missing_sources.join(", "),
          })}
        </p>
      {/if}
      {#each autoProblems as problem, i (i)}
        <p class="px-4.5 py-3 text-warn">{watchProblemText(problem)}</p>
      {/each}
    </div>
  {/if}

  {#if summary && !scan}
    <p class="mt-8 rounded-xl border border-dashed border-faint p-8 text-center text-sm text-muted">
      {t("web_no_analysis", "No analysis yet: analyze the source folders to fill the tabs.")}
    </p>
  {/if}

  {#if summary && scan}
    <p class="label mt-8 mb-2.5 px-1">{t("web_results", "Results")}</p>
    <div class="overflow-hidden rounded-xl border border-line bg-card">
      <table class="w-full text-sm">
        <thead>
          <tr class="label border-b border-line text-left">
            <th class="px-4 py-2.5 font-semibold">{t("web_type", "Type")}</th>
            <th class="w-28 px-4 py-2.5 text-right font-semibold">{t("files", "Files")}</th>
            <th class="w-28 px-4 py-2.5 text-right font-semibold">
              {t("web_ready_plural", "Ready")}
            </th>
            <th class="w-28 px-4 py-2.5 text-right font-semibold">
              {t("web_to_pick", "To pick")}
            </th>
            <th class="w-28 px-4 py-2.5 text-right font-semibold">
              {t("web_missing_plural", "Missing")}
            </th>
            <th class="w-24"></th>
          </tr>
        </thead>
        <tbody>
          {#each MEDIA_PAGES as page (page.path)}
            {@const counts = summary.counts[page.mediaType!]}
            <tr class="border-b border-line hover:bg-hover">
              <td class="px-4 py-2.5">
                <span class="flex items-center gap-2.5 font-medium">
                  <Icon name={page.icon} class="size-4.5 shrink-0 text-icon" />
                  {t(page.key, page.english)}
                </span>
                {#if counts.pending}
                  <span class="mt-0.5 block pl-7 text-xs text-muted">
                    {t("web_not_searched_count", "{n} not searched yet", { n: counts.pending })}
                  </span>
                {/if}
              </td>
              <td class="px-4 py-2.5 text-right tabular-nums">{counts.total || "—"}</td>
              {@render count(counts.ok, "font-semibold text-ok")}
              {@render count(counts.ambiguous, "font-semibold text-warn")}
              {@render count(counts.missing, "font-semibold text-error")}
              <td class="px-3 py-2 text-right">
                <a href={page.path} onclick={follow} class="button-outline px-3.5 py-1">
                  {t("web_open", "Open")}
                </a>
              </td>
            </tr>
          {/each}
        </tbody>
        <tfoot>
          <tr class="text-[13px] font-semibold text-muted">
            <td class="px-4 py-2.5">{t("web_total", "Total")}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{totals.total}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{totals.ok}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{totals.ambiguous}</td>
            <td class="px-4 py-2.5 text-right tabular-nums">{totals.missing}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
    </div>
    {#if scan.processed}
      <p class="mt-2.5 px-1 text-sm text-muted">
        {t("web_processed_hidden", "{n} files already processed are left out.", {
          n: scan.processed,
        })}
        <a href="/history/processed" onclick={follow} class="link">
          {t("web_show_processed", "Show them")}
        </a>
      </p>
    {/if}
  {/if}

  {#if summary?.to_check.length}
    <p class="label mt-8 px-1">{t("web_to_check", "Files to check")}</p>
    <p class="mt-1 mb-2.5 px-1 text-sm text-muted">
      {t("web_to_check_text", "Their type is a guess: confirm it, or pick another one.")}
    </p>
    <div class="divide-y divide-line rounded-xl border border-line bg-card">
      {#each summary.to_check as item (item.path)}
        <div class="flex flex-wrap items-center gap-3 px-4 py-3">
          <div class="min-w-0 flex-1">
            <p class="truncate font-mono text-sm" title={item.path}>{fileName(item.path)}</p>
            <p class="mt-0.5 text-[13px] text-muted">{reasonText(item.reason)}</p>
          </div>
          <select
            class="field w-auto py-1.5"
            value={kinds[item.path] ?? item.kind}
            onchange={(event) => (kinds[item.path] = event.currentTarget.value)}
          >
            {#each KINDS as [kind, label] (kind)}
              <option value={kind}>{label()}</option>
            {/each}
          </select>
          <button class="button-outline" disabled={confirming !== ""} onclick={() => confirm(item)}>
            {confirming === item.path
              ? t("searching", "Searching...")
              : t("web_confirm", "Confirm")}
          </button>
        </div>
      {/each}
    </div>
  {/if}
</div>
