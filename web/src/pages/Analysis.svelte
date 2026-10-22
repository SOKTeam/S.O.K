<script lang="ts">
  import Icon from "../components/Icon.svelte";
  import { errorText, stopText } from "../lib/errors";
  import { i18n, t } from "../lib/i18n.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { follow } from "../lib/router.svelte";
  import { analysis, confirmType, startScan, type ToCheck } from "../lib/scan.svelte";

  let error = $state("");
  // The type picked for each file to check, before it is confirmed.
  let kinds = $state<Record<string, string>>({});

  const summary = $derived(analysis.summary);
  const scan = $derived(summary?.scan ?? null);

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
    try {
      await confirmType(item.path, kinds[item.path] ?? item.kind);
    } catch (exc) {
      error = errorText(exc);
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

<div class="mx-auto flex max-w-5xl flex-col gap-8 pb-16">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold">{t("web_analysis", "Analysis")}</h1>
      {#if scan && scan.status !== "running"}
        <p class="mt-1 text-sm text-muted">
          {t("web_last_analysis", "Last analysis: {date}", { date: date(scan.started) })}
        </p>
      {/if}
    </div>
    <button class="button" disabled={analysis.running} onclick={analyze}>
      {t("web_analyze", "Analyze")}
    </button>
  </div>

  {#if error}
    <p class="text-sm text-error" role="alert">{error}</p>
  {/if}

  {#if summary && !scan}
    <p class="rounded-xl border border-dashed border-line p-8 text-center text-sm text-muted">
      {t("web_no_analysis", "No analysis yet: analyze the source folders to fill the tabs.")}
    </p>
  {/if}

  {#if scan?.status === "running"}
    {@const progress = scan.progress}
    <div class="rounded-xl border border-line bg-card p-4" role="status">
      <p class="text-sm font-semibold">
        {#if progress?.phase === "search" && progress.total}
          {t("web_progress_search", "Searching… {done} / {total}", {
            done: progress.done,
            total: progress.total,
          })}
        {:else}
          {t("web_progress_detect", "Sorting the files…")}
        {/if}
      </p>
      <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-hover">
        <div
          class={[
            "h-full rounded-full bg-accent transition-all",
            !(progress?.phase === "search" && progress.total) && "w-1/3 animate-pulse",
          ]}
          style:width={progress?.phase === "search" && progress.total
            ? `${(100 * progress.done) / progress.total}%`
            : undefined}
        ></div>
      </div>
    </div>
  {/if}

  {#if scan?.error}
    <div class="rounded-xl border border-error/30 bg-error/5 p-4 text-sm text-error" role="alert">
      <p>{stopText(scan.error)}</p>
      {#each scan.error.others ?? [] as other (other.service)}
        <p class="mt-1">{stopText(other)}</p>
      {/each}
      {#if scan.error.code === "missing_key" || scan.error.code === "key_refused"}
        <a href="/settings" onclick={follow} class="mt-2 inline-block font-semibold underline">
          {t("settings", "Settings")}
        </a>
      {/if}
    </div>
  {/if}

  {#if scan?.status === "interrupted"}
    <p class="text-sm text-warn">
      {t(
        "web_scan_interrupted",
        "The last analysis was cut by a restart of the server: analyze again.",
      )}
    </p>
  {/if}

  {#if scan?.missing_sources.length}
    <p class="text-sm text-warn">
      {t("web_missing_sources", "Source folders not found: {folders}", {
        folders: scan.missing_sources.join(", "),
      })}
    </p>
  {/if}

  {#if summary && scan}
    <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {#each MEDIA_PAGES as page (page.path)}
        {@const counts = summary.counts[page.mediaType!]}
        <a
          href={page.path}
          onclick={follow}
          class="flex flex-col gap-3 rounded-xl border border-line bg-card p-4 hover:border-accent/50"
        >
          <span class="flex items-center gap-2 font-semibold">
            <Icon name={page.icon} class="size-4.5 text-accent" />
            {t(page.key, page.english)}
            <span class="ml-auto text-2xl font-bold tabular-nums">{counts.total}</span>
          </span>
          <span class="flex flex-wrap gap-x-3 gap-y-1 text-xs">
            <span class="text-ok">{t("status_ready", "Ready")} {counts.ok}</span>
            <span class="text-warn">{t("status_ambiguous", "Pick one")} {counts.ambiguous}</span>
            <span class="text-error">{t("status_missing", "Missing")} {counts.missing}</span>
            {#if counts.pending}
              <span class="text-muted"
                >{t("web_status_pending", "Not searched")} {counts.pending}</span
              >
            {/if}
          </span>
        </a>
      {/each}
    </div>
    {#if scan.processed}
      <p class="text-sm text-muted">
        {t("web_processed_hidden", "{n} files already processed are left out.", {
          n: scan.processed,
        })}
      </p>
    {/if}
  {/if}

  {#if summary?.to_check.length}
    <section>
      <h2 class="text-lg font-semibold">{t("web_to_check", "Files to check")}</h2>
      <p class="mt-1 text-sm text-muted">
        {t("web_to_check_text", "Their type is a guess: confirm it, or pick another one.")}
      </p>
      <div class="mt-3 divide-y divide-line rounded-xl border border-line bg-card">
        {#each summary.to_check as item (item.path)}
          <div class="flex flex-wrap items-center gap-3 px-4 py-3">
            <div class="min-w-0 flex-1">
              <p class="truncate font-mono text-xs" title={item.path}>{fileName(item.path)}</p>
              <p class="mt-0.5 text-xs text-muted">{reasonText(item.reason)}</p>
            </div>
            <select
              class="field w-auto py-1 text-xs"
              value={kinds[item.path] ?? item.kind}
              onchange={(event) => (kinds[item.path] = event.currentTarget.value)}
            >
              {#each KINDS as [kind, label] (kind)}
                <option value={kind}>{label()}</option>
              {/each}
            </select>
            <button
              class="rounded-lg border border-line px-3 py-1 text-xs font-semibold hover:bg-hover"
              onclick={() => confirm(item)}
            >
              {t("web_confirm", "Confirm")}
            </button>
          </div>
        {/each}
      </div>
    </section>
  {/if}
</div>
