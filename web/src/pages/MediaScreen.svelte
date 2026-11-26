<script lang="ts">
  // The screen of a media type (Movies first): what waits on the left, with
  // its filters and the selection; on the right the scene of the open row,
  // the results to pick, the covers chosen, or the end of a rename.
  import { onMount, untrack } from "svelte";

  import Split from "../components/layout/Split.svelte";
  import { longpress } from "../lib/longpress";
  import { screen } from "../lib/screen.svelte";
  import Gauge from "../components/media/Gauge.svelte";
  import Thumb from "../components/media/Thumb.svelte";
  import Facts, { type Fact } from "../components/scene/Facts.svelte";
  import Fan from "../components/scene/Fan.svelte";
  import { ApiError } from "../lib/api";
  import { posterColor } from "../lib/color";
  import { sizeText } from "../lib/disks";
  import { errorText, searchErrorText } from "../lib/errors";
  import { i18n, t, tn } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";
  import type { Page } from "../lib/pages";
  import { decoded, follow, hold, href } from "../lib/router.svelte";
  import {
    bigPosterUrl,
    changeRow,
    episodeCode,
    episodeTitle,
    seasonsOf,
    trackOf,
    formatOf,
    platformOf,
    loadRows,
    matchOf,
    posterUrl,
    searchRow,
    titleOf,
    type Row,
  } from "../lib/rows";
  import { undo } from "../lib/history";
  import { renames, startRename } from "../lib/renames.svelte";
  import { analysis, refreshSummary, startScan, type RowStatus } from "../lib/scan.svelte";
  import { loadSettings, settings } from "../lib/settings.svelte";
  import { loadWatch, watch } from "../lib/watch.svelte";
  import { SITE_URL } from "../lib/site";

  let { page }: { page: Page } = $props();

  let rows = $state<Row[] | null>(null);
  let filter = $state<RowStatus | "all">("all");
  let error = $state("");
  // The row open on the scene, and what the scene shows.
  let openId = $state<number | null>(null);
  // Under 1000px, whether the scene is over the list.
  let sceneOpen = $state(false);
  let view = $state<"scene" | "pick">("scene");
  // The selection: its mode, the rows chosen, the row of a Shift range.
  let picking = $state(false);
  let chosen = $state<number[]>([]);
  let anchor = $state<number | null>(null);
  // The pick panel: the text searched, a search running, its message.
  let query = $state("");
  let searching = $state(false);
  let searchMessage = $state("");
  // The result of a rename closed by the user, and its undo.
  let dismissed = $state<number | null>(null);
  let askUndo = $state(false);
  let undone = $state<number | null>(null);

  const mediaType = $derived(page.mediaType!);

  onMount(() => {
    if (!settings.data) loadSettings().catch(() => {});
    loadWatch().catch(() => {});
    const leave = (event: KeyboardEvent) => {
      if (event.key === "Escape" && picking) endPicking();
    };
    window.addEventListener("keydown", leave);
    return () => {
      window.removeEventListener("keydown", leave);
      setLight(null);
    };
  });

  // Read again at each analysis, and when the media type changes.
  $effect(() => {
    void analysis.changes;
    const wanted = mediaType;
    const release = hold();
    loadRows(wanted)
      .then((found) => {
        if (wanted !== mediaType) return release();
        rows = found;
        untrack(() => {
          if (openId === null || !found.some((row) => row.id === openId)) {
            // The first Ready row; else the first one, on its results.
            const first = found.find((row) => row.status === "ok") ?? found[0];
            openId = first?.id ?? null;
            view = first && first.status !== "ok" ? "pick" : "scene";
            query = first ? (first.query ?? titleOf(first)) : "";
          }
        });
        const lit = found.find((row) => row.id === openId);
        decoded([
          ...found.slice(0, 16).map((row) => posterUrl(matchOf(row)?.poster ?? null)),
          bigPosterUrl(lit ? (matchOf(lit)?.poster ?? null) : null),
        ]).then(release);
      })
      .catch((exc) => {
        error = errorText(exc);
        release();
      });
  });

  $effect(() => {
    void mediaType;
    untrack(() => {
      // No rows of the type before: they would be drawn in this one's layout.
      rows = null;
      filter = "all";
      endPicking();
      openId = null;
    });
  });

  const shown = $derived(
    rows === null ? [] : filter === "all" ? rows : rows.filter((row) => row.status === filter),
  );
  const ready = $derived(rows?.filter((row) => row.status === "ok") ?? []);
  const open = $derived(rows?.find((row) => row.id === openId) ?? null);
  const selection = $derived(ready.filter((row) => chosen.includes(row.id)));
  const destinations = $derived(settings.data?.folders[mediaType] ?? []);
  const mode = $derived(settings.data?.settings.file_mode as string | undefined);
  const rename = $derived(
    renames.current?.media_type === mediaType && renames.current.id !== dismissed
      ? renames.current
      : null,
  );
  const renaming = $derived(rename?.status === "running");
  const scan = $derived(analysis.summary?.scan ?? null);

  // A series counts its episodes; the other rows count one.
  const episodic = $derived(mediaType === "tv");
  // Music: a grid of covers, an album or a track per tile, counted in tracks.
  const music = $derived(mediaType === "music");
  const books = $derived(mediaType === "books");
  const games = $derived(mediaType === "games");
  // The consoles the games are recognized on, for the empty screen.
  const CONSOLES = [
    "NES",
    "SNES",
    "N64",
    "GameCube",
    "Wii",
    "Game Boy",
    "GBA",
    "DS",
    "Switch",
    "PlayStation",
    "PS2",
    "PSP",
    "Mega Drive",
    "Dreamcast",
  ];

  async function analyze() {
    error = "";
    try {
      await startScan();
    } catch (exc) {
      error = errorText(exc);
    }
  }

  function units(list: Row[]): number {
    return episodic || music ? list.reduce((sum, row) => sum + row.files.length, 0) : list.length;
  }

  /** The key of "Which … is it?": per kind for music (album or track). */
  const whichKey = $derived(open && music ? `web_which_${open.kind}` : `web_which_${mediaType}`);

  // The tracks of an album shown on the scene, before "+ N tracks".
  const TRACKS_SHOWN = 6;

  function count(status: RowStatus): number {
    return units(rows?.filter((row) => row.status === status) ?? []);
  }

  // The episodes of the open series: all of them, or the first ones.
  let allEpisodes = $state(false);
  // The episodes of the open series folded away (a click on its row again).
  let folded = $state(false);
  const EPISODES_SHOWN = 4;

  // ------------------------------------------------------------- Light

  const lit = $derived.by(() => {
    if (selection.length) return matchOf(selection[0])?.poster ?? null;
    return open ? (matchOf(open)?.poster ?? null) : null;
  });

  $effect(() => {
    const url = bigPosterUrl(lit);
    if (!url) {
      setLight(null);
      return;
    }
    posterColor(url).then((color) => setLight(color ?? "251, 96, 72"));
  });

  // --------------------------------------------------------- Selection

  function endPicking() {
    picking = false;
    chosen = [];
    anchor = null;
  }

  function toggle(row: Row) {
    if (row.status !== "ok") return;
    chosen = chosen.includes(row.id) ? chosen.filter((id) => id !== row.id) : [...chosen, row.id];
    anchor = row.id;
    if (!chosen.length) endPicking();
  }

  /** The Ready rows shown between the anchor and a row, both included. */
  function range(row: Row) {
    const ids = shown.map((one) => one.id);
    const from = ids.indexOf(anchor ?? openId ?? row.id);
    const to = ids.indexOf(row.id);
    const [a, b] = from < to ? [from, to] : [to, from];
    const inRange = shown
      .slice(Math.max(0, a), b + 1)
      .filter((one) => one.status === "ok")
      .map((one) => one.id);
    chosen = [...new Set([...chosen, ...inRange])];
  }

  function mark(row: Row) {
    if (!picking) {
      picking = true;
      chosen = [];
    }
    toggle(row);
  }

  function click(row: Row, event: MouseEvent) {
    if (picking) {
      if (event.shiftKey) range(row);
      else toggle(row);
      return;
    }
    if (event.metaKey || event.ctrlKey) {
      picking = true;
      chosen = [open, row]
        .filter((one): one is Row => one?.status === "ok")
        .map((one) => one.id)
        .filter((id, i, all) => all.indexOf(id) === i);
      anchor = row.id;
      if (!chosen.length) endPicking();
      return;
    }
    if (event.shiftKey && row.status === "ok") {
      picking = true;
      range(row);
      return;
    }
    openRow(row);
  }

  function openRow(row: Row) {
    if (row.id !== openId) {
      allEpisodes = false;
      folded = false;
    } else if (episodic && !screen.narrow) {
      // The open series again: fold or unfold its episodes. Narrow, a click
      // opens the scene over the list, so the fold is the word under them.
      folded = !folded;
    }
    openId = row.id;
    anchor = row.id;
    searchMessage = "";
    query = row.query ?? titleOf(row);
    view = row.status === "ok" ? "scene" : "pick";
    sceneOpen = true;
  }

  /** "That's not it": the results and the search, for the open row. */
  function openPicker(row: Row) {
    searchMessage = "";
    query = row.query ?? titleOf(row);
    view = "pick";
  }

  // ------------------------------------------------------ Changes

  function replace(changed: Row) {
    if (rows) rows = rows.map((row) => (row.id === changed.id ? changed : row));
    refreshSummary().catch(() => {});
  }

  async function pick(index: number) {
    if (!open) return;
    error = "";
    try {
      replace(await changeRow(open.id, { selected: index }));
      view = "scene";
    } catch (exc) {
      error = errorText(exc);
    }
  }

  async function search(event: SubmitEvent) {
    event.preventDefault();
    if (!open || !query.trim()) return;
    searching = true;
    searchMessage = "";
    try {
      const found = await searchRow(open.id, query.trim());
      replace(found);
      if (!found.candidates.length) {
        searchMessage = t("web_pick_nothing", "Nothing found for “{query}”.", {
          query: query.trim(),
        });
      }
    } catch (exc) {
      searchMessage =
        exc instanceof ApiError && exc.status === 409 ? searchErrorText(exc) : errorText(exc);
    } finally {
      searching = false;
    }
  }

  async function choose(index: number) {
    if (!open) return;
    try {
      replace(await changeRow(open.id, { destination: index }));
    } catch (exc) {
      error = errorText(exc);
    }
  }

  async function undoRename() {
    const operation = rename?.result?.operation;
    if (!operation || !rename) return;
    error = "";
    try {
      await undo(operation);
      undone = rename.id;
      askUndo = false;
      await refreshSummary();
    } catch (exc) {
      error = errorText(exc);
    }
  }

  async function renameNow() {
    error = "";
    dismissed = null;
    try {
      await startRename(mediaType, selection.length ? selection.map((row) => row.id) : undefined);
      endPicking();
      sceneOpen = true;
    } catch (exc) {
      error = errorText(exc);
    }
  }

  // --------------------------------------------------------- Texts

  function time(value: string): string {
    return new Intl.DateTimeFormat(i18n.language, { timeStyle: "short" }).format(new Date(value));
  }

  function size(bytes: number | undefined): string {
    return bytes ? sizeText(bytes, i18n.language) : "";
  }

  function modeWord(): string {
    switch (mode) {
      case "link":
        return t("web_mode_link_word", "hard link");
      case "copy":
        return t("web_mode_copy_word", "copy");
      default:
        return t("web_mode_move_word", "moved");
    }
  }

  /** The service that found the matches of this media type. */
  function service(): string {
    const category = { movies: "video", tv: "video" }[mediaType] ?? mediaType;
    const id = settings.data?.settings[`preferred_api_${category}`] as string | undefined;
    return settings.data?.services[category]?.find((one) => one.id === id)?.name ?? "";
  }

  /** "Season 1 · 7 episodes", "Seasons 1–2 · 12 episodes". */
  function seasonLine(row: Row): string {
    const seasons = seasonsOf(row);
    const episodes = tn("web_n_episodes", row.files.length, "{n} episode", "{n} episodes");
    if (!seasons.length) return episodes;
    const season =
      seasons.length === 1
        ? t("web_season_n", "Season {n}", { n: seasons[0] })
        : t("web_seasons_range", "Seasons {from}–{to}", {
            from: seasons[0],
            to: seasons[seasons.length - 1],
          });
    return `${season} · ${episodes}`;
  }

  /** The folder a row goes to: its destination, and the folders of its new
   * name ("…/Breaking Bad/Season 1/"). */
  function targetOf(row: Row): string {
    const name = row.files[0]?.new_name;
    if (!name) return "";
    const folder = folderOf(row);
    if (!episodic && !(music && row.kind === "album")) return `${folder}/${name}`;
    const parts = name.split("/").slice(0, -1);
    return `${folder}/${parts.join("/")}/`;
  }

  function folderOf(row: Row): string {
    return destinations[row.destination < destinations.length ? row.destination : 0] ?? "";
  }

  function was(row: Row): string {
    const first = row.files[0]?.name ?? "";
    return row.files.length > 1
      ? tn("web_was_more", row.files.length - 1, "was {name} +{n}", "was {name} +{n}", {
          name: first,
        })
      : t("web_was", "was {name}", { name: first });
  }

  const sources = $derived(settings.data?.folders.sources ?? []);
  const sourcesText = $derived(
    new Intl.ListFormat(i18n.language, { type: "conjunction" }).format(sources),
  );

  const facts = $derived.by<Fact[]>(() => {
    if (!open) return [];
    const list: Fact[] = [];
    const match = matchOf(open);
    if (books) {
      if (match?.publisher) {
        list.push({ label: t("web_fact_publisher", "Publisher"), value: match.publisher });
      }
      const format = formatOf(open.files[0]);
      list.push({
        label: t("web_fact_format", "Format"),
        value: [format, size(open.size)].filter(Boolean).join(" · "),
      });
      if (match?.isbn) list.push({ label: "ISBN", value: match.isbn });
    } else {
      if (open.quality) list.push({ label: t("web_fact_quality", "Quality"), value: open.quality });
      if (open.size) list.push({ label: t("web_fact_size", "Size"), value: size(open.size) });
      if (open.files.length > 1) {
        list.push({ label: t("web_fact_files", "Files"), value: String(open.files.length) });
      }
      list.push({ label: t("web_mode", "Mode"), value: modeWord() });
    }
    if (service())
      list.push({ label: t("web_fact_found_via", "Recognized via"), value: service() });
    return list;
  });

  const selectionFacts = $derived.by<Fact[]>(() => {
    const total = selection.reduce((sum, row) => sum + (row.size ?? 0), 0);
    return [
      ...(total ? [{ label: t("web_fact_size", "Size"), value: size(total) }] : []),
      { label: t("web_mode", "Mode"), value: modeWord() },
      { label: t("web_to", "To"), value: destinations[0] ?? "—" },
    ];
  });

  const left = $derived([
    ...(rename?.result?.skipped ?? []).map((one) => ({ file: one.file, why: one.reason })),
    ...(rename?.result?.errors ?? []).map((one) => ({ file: one.file, why: one.error })),
  ]);

  /** "Hard link to /media/Movies. The files also stay in /downloads…" */
  const modeNote = $derived.by(() => {
    const folder = destinations[0];
    if (!folder)
      return t("web_no_destination", "No destination folder yet: choose one in Settings.");
    switch (mode) {
      case "link":
        return t(
          "web_note_link",
          "Hard link to {folder}. The files also stay in {sources} to keep seeding.",
          { folder, sources: sourcesText },
        );
      case "copy":
        return t("web_note_copy", "Copy to {folder}. The originals stay in {sources}.", {
          folder,
          sources: sourcesText,
        });
      default:
        return t("web_note_move", "Moved to {folder}: the files leave {sources}.", {
          folder,
          sources: sourcesText,
        });
    }
  });

  const FILTERS = $derived<[RowStatus | "all", string][]>([
    ["all", t("web_all", "All")],
    ["ok", t("web_ready_plural", "Ready")],
    ["ambiguous", t("web_to_pick", "To pick")],
    ["missing", t("web_not_found_plural", "Not found")],
  ]);
</script>

{#snippet status(row: Row)}
  {#if row.status === "ok"}
    <Gauge notches={5} />
  {:else if row.status === "ambiguous"}
    <span class="flex items-center gap-2.5 text-[12.5px] text-accent-text">
      {t("web_status_to_pick", "to pick")}
      <Gauge notches={2} />
    </span>
  {:else if row.status === "missing"}
    <span class="flex items-center gap-2.5 text-[12.5px] text-caution">
      {t("web_status_not_found", "not found")}
      <Gauge notches={0} />
    </span>
  {:else}
    <span class="text-[12.5px] text-faint">{t("web_status_pending", "not searched yet")}</span>
  {/if}
{/snippet}

{#if rows !== null && !rows.length && !rename}
  <!-- Nothing to sort: the empty screen, centered. -->
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
      {t(`web_title_no_${mediaType}`, "No movie to sort")}<span class="text-muted">.</span>
    </h1>
    <p class="mt-3 max-w-[640px] text-[16px] leading-[1.45] text-muted">
      {t(
        `web_empty_${mediaType}`,
        "The movies of {sources} show here after an analysis. S.O.K finds their title, year and poster, then puts each one in its place.",
        { sources: sourcesText },
      )}
    </p>
    {#if error}<p class="mt-3 text-[14px] text-danger" role="alert">{error}</p>{/if}
    <div class="mt-[26px] flex justify-center gap-2.5">
      {#if analysis.running}
        <button type="button" class="key" disabled>{t("web_analyzing", "Analyzing…")}</button>
      {:else}
        <button type="button" class="key key-primary" onclick={analyze}>
          {t("web_analyze", "Analyze")}
        </button>
      {/if}
      <a class="key" href="{SITE_URL}/guide" target="_blank" rel="noopener">
        {t("web_how_it_works", "How it works")}
      </a>
    </div>
    {#if games}
      <p class="label mt-[34px]">
        {tn("web_n_consoles", CONSOLES.length, "{n} console recognized", "{n} consoles recognized")}
      </p>
      <div class="mt-3 flex max-w-[560px] flex-wrap justify-center gap-1.5">
        {#each CONSOLES as name (name)}
          <span class="tag px-[7px] py-[3px]">{name}</span>
        {/each}
      </div>
    {/if}
  </div>
{:else}
  <Split open={sceneOpen} onclose={() => (sceneOpen = false)}>
    <div class="mb-2 text-[11px] leading-4 font-semibold tracking-[0.08em] text-faint uppercase">
      {#if scan?.finished}
        {t("web_analyzed_at", "Analyzed at {time}", { time: time(scan.finished) })}
      {/if}
      {#if watch.status?.enabled}
        · {t("web_auto_every", "automatic sorting every {minutes} min", {
          minutes: watch.status.minutes,
        })}
      {/if}
    </div>
    <h1 class="m-0 text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
      {#if renaming}
        {t("web_title_renaming", "Putting away")}<span class="text-muted">…</span>
      {:else if rows?.length}
        {tn(`web_title_${mediaType}`, units(rows), "{n} movie", "{n} movies")}
        <span class="text-muted">{t("web_title_to_sort", "to sort.")}</span>
      {:else}
        {t(`web_title_no_${mediaType}`, "No movie to sort")}<span class="text-muted">.</span>
      {/if}
    </h1>
    <p class="mt-3 text-[15px] leading-[1.45] text-muted">
      {#if renaming && rename?.progress?.total}
        {t("web_putting_away_progress", "Putting away… {done} / {total}", {
          done: rename.progress.done,
          total: rename.progress.total,
        })}
      {:else if rows?.length}
        {#if episodic}
          {tn("web_in_series", rows.length, "In {n} series.", "In {n} series.")}
        {:else if music}
          {tn(
            "web_in_albums",
            rows.filter((row) => row.kind === "album").length,
            "In {n} album.",
            "In {n} albums.",
          )}
          {#if rows.some((row) => row.kind === "track")}
            {tn(
              "web_single_tracks",
              rows.filter((row) => row.kind === "track").length,
              "And {n} single track.",
              "And {n} single tracks.",
            )}
          {/if}
        {:else}
          {t("web_found_in", "Found in {sources}.", { sources: sourcesText })}
        {/if}
        {#if count("ok")}<b class="font-medium text-ink"
            >{tn("web_n_ready", count("ok"), "{n} recognized", "{n} recognized")}</b
          >{/if}{#if count("ambiguous")}{count("ok") ? ", " : ""}{tn(
            "web_n_wait_you",
            count("ambiguous"),
            "{n} waits for you",
            "{n} wait for you",
          )}{/if}{#if count("missing")}{count("ok") || count("ambiguous") ? ", " : ""}{tn(
            "web_n_not_found",
            count("missing"),
            "{n} not found",
            "{n} not found",
          )}{/if}.
      {:else}
        {t("web_empty_media", "The files of {sources} show here after an analysis.", {
          sources: sourcesText,
        })}
      {/if}
    </p>
    {#if error}<p class="mt-3 text-[14px] text-danger" role="alert">{error}</p>{/if}

    {#if rows?.length}
      <div
        class="mt-[22px] mb-2.5 flex items-baseline gap-5 text-[14px] font-semibold whitespace-nowrap text-faint max-[699px]:gap-4"
      >
        {#each FILTERS as [value, label] (value)}
          {@const n = value === "all" ? units(rows) : count(value)}
          <button
            type="button"
            class={["cursor-pointer", filter === value ? "text-ink" : "hover:text-muted"]}
            aria-pressed={filter === value}
            onclick={() => (filter = value)}
          >
            {label}<small class="ml-1 font-mono text-[11.5px] font-medium">{n}</small>
          </button>
        {/each}
        {#if picking}
          <button
            type="button"
            class="key key-sm -my-2 ml-auto max-[699px]:hidden"
            onclick={endPicking}
          >
            {t("web_done", "Done")}
          </button>
        {/if}
      </div>

      {#if music}
        <!-- The music: a grid of covers. -->
        <div
          class="-mx-2.5 grid grid-cols-4 content-start gap-1 pt-0.5 max-[999px]:grid-cols-3 max-[699px]:grid-cols-2"
        >
          {#each shown as row (row.id)}
            {@const isChosen = chosen.includes(row.id)}
            {@const match = matchOf(row)}
            <div
              role="button"
              tabindex="0"
              aria-current={row.id === openId && !picking ? "true" : undefined}
              class={[
                "min-w-0 cursor-pointer rounded-[14px] p-2.5 transition-colors",
                isChosen
                  ? "bg-accent-soft"
                  : row.id === openId && !picking
                    ? "bg-raised shadow-[inset_0_1px_0_var(--color-hi)]"
                    : "hover:bg-raised/60",
              ]}
              onclick={(event) => click(row, event)}
              onkeydown={(event) => event.key === "Enter" && openRow(row)}
              use:longpress={() => row.status === "ok" && mark(row)}
            >
              <Thumb
                tile
                poster={match?.poster ?? null}
                chosen={isChosen}
                marks={picking}
                selectable={row.status === "ok"}
                label={t("web_choose_row", "Choose {title}", { title: titleOf(row) })}
                onmark={() => mark(row)}
              />
              <div
                class={[
                  "mt-2.5 truncate text-[14.5px] font-semibold",
                  row.status === "missing" && "text-caution",
                ]}
              >
                {row.status === "missing" ? t("web_unknown_title", "Unknown title") : titleOf(row)}
              </div>
              <div class="mt-0.5 truncate text-[12.5px] text-muted">
                {#if row.status === "ok"}
                  {match?.by ?? ""}{#if match?.year}{match?.by ? " · " : ""}<span
                      class="font-mono text-[12px] text-faint">{match.year}</span
                    >{/if}
                {:else if row.status === "ambiguous"}
                  <span class="text-accent-text">{t("web_status_to_pick", "to pick")}</span>
                {:else}
                  {tn("web_n_tracks", row.files.length, "{n} track", "{n} tracks")}
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="-mx-2.5 grid content-start gap-0.5">
          {#each shown as row (row.id)}
            {@const isChosen = chosen.includes(row.id)}
            {@const match = matchOf(row)}
            <div
              role="button"
              aria-current={row.id === openId && !picking ? "true" : undefined}
              aria-expanded={episodic ? row.id === openId && !picking && !folded : undefined}
              class={[
                "relative grid h-[66px] cursor-pointer grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-x-3.5 rounded-xl px-3.5 transition-colors",
                isChosen
                  ? "bg-accent-soft"
                  : row.id === openId && !picking
                    ? "bg-raised shadow-[inset_0_1px_0_var(--color-hi)]"
                    : "hover:bg-raised/60",
              ]}
              onclick={(event) => click(row, event)}
              onkeydown={(event) => event.key === "Enter" && openRow(row)}
              use:longpress={() => row.status === "ok" && mark(row)}
              tabindex="0"
            >
              <Thumb
                book={books}
                poster={match?.poster ?? null}
                chosen={isChosen}
                marks={picking}
                selectable={row.status === "ok"}
                label={t("web_choose_row", "Choose {title}", { title: titleOf(row) })}
                onmark={() => mark(row)}
              />
              <div class="min-w-0">
                <div
                  class={[
                    "truncate text-[16px] font-semibold tracking-[-0.01em]",
                    row.status === "missing" && "text-caution",
                  ]}
                >
                  {row.status === "missing"
                    ? t("web_unknown_title", "Unknown title")
                    : titleOf(row)}
                  {#if books}
                    {#if match?.by}<span class="ml-2 text-[14px] font-normal text-muted"
                        >{match.by}</span
                      >{/if}{#if formatOf(row.files[0])}<span class="tag ml-2"
                        >{formatOf(row.files[0])}</span
                      >{/if}
                  {:else if games && platformOf(row)}<span class="tag ml-2">{platformOf(row)}</span>
                  {:else if match?.year}<small
                      class="ml-2 font-mono text-[12.5px] font-normal text-faint"
                      >{match.year}</small
                    >{/if}
                </div>
                {#if episodic}
                  <div class="mt-[3px] truncate text-[13px] text-faint">{seasonLine(row)}</div>
                {:else}
                  <div class="mt-[3px] truncate font-mono text-[12px] text-faint">{was(row)}</div>
                {/if}
              </div>
              {@render status(row)}
            </div>
            {#if episodic && row.id === openId && !picking && !folded}
              <!-- The episodes of the open series, under its row. -->
              <div class="mt-0.5 mb-2 ml-16 grid">
                {#each allEpisodes ? row.files : row.files.slice(0, EPISODES_SHOWN) as file (file.path)}
                  <div
                    class="grid grid-cols-[62px_minmax(0,1fr)] gap-3 border-t border-line py-[7px]"
                  >
                    <span class="font-mono text-[12.5px] text-faint"
                      >{episodeCode(file) ?? "—"}</span
                    >
                    <div class="min-w-0">
                      <div class="truncate text-[14px]">{episodeTitle(file) ?? "—"}</div>
                      <div class="mt-0.5 truncate font-mono text-[11.5px] text-faint">
                        {t("web_was", "was {name}", { name: file.name })}
                      </div>
                    </div>
                  </div>
                {/each}
                <div
                  class="flex items-baseline justify-between gap-4 border-t border-line py-[7px]"
                >
                  {#if !allEpisodes && row.files.length > EPISODES_SHOWN}
                    <button
                      type="button"
                      class="cursor-pointer text-left text-[13px] text-muted hover:text-ink"
                      onclick={() => (allEpisodes = true)}
                    >
                      {tn(
                        "web_more_episodes",
                        row.files.length - EPISODES_SHOWN,
                        "+ {n} other episode",
                        "+ {n} other episodes",
                      )}
                    </button>
                  {:else}
                    <span></span>
                  {/if}
                  <button
                    type="button"
                    class="cursor-pointer text-[13px] text-faint hover:text-ink"
                    onclick={() => (folded = true)}
                  >
                    {t("web_hide_episodes", "Hide the episodes")}
                  </button>
                </div>
              </div>
            {/if}
          {:else}
            <p class="px-3.5 py-6 text-[14px] text-muted">
              {t("web_no_rows_filter", "No row with this status.")}
            </p>
          {/each}
        </div>
      {/if}
    {/if}

    <div class="flex-1"></div>
    {#if screen.phone && picking}
      <!-- The selection of a phone: a bar at the bottom. -->
      <div class="dock">
        <div
          class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3.5 gap-y-2.5 rounded-[18px] bg-surface p-3 shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line),0_20px_50px_var(--drop)]"
        >
          <div
            class="relative h-[54px]"
            style:width={`${36 + Math.max(0, Math.min(selection.length, 3) - 1) * 20}px`}
          >
            {#each selection.slice(0, 3) as row, i (row.id)}
              <img
                src={posterUrl(matchOf(row)?.poster ?? null) ?? ""}
                alt=""
                class="absolute top-0 h-[54px] w-9 rounded-[4px] bg-key object-cover shadow-[0_4px_10px_rgb(0_0_0/0.4),inset_0_0_0_1px_rgb(255_255_255/0.1)]"
                style:left={`${i * 20}px`}
                style:z-index={5 - i}
              />
            {/each}
          </div>
          <div class="min-w-0 text-[15px] font-semibold">
            {tn(
              `web_chosen_${mediaType}`,
              selection.length,
              "{n} movie chosen",
              "{n} movies chosen",
            )}
            <small class="mt-0.5 block text-[12px] font-normal text-muted">
              {t("web_touch_to_toggle", "Touch a row to add or remove it.")}
            </small>
          </div>
          <div class="col-span-2 flex gap-2">
            <button type="button" class="key" onclick={endPicking}>{t("web_done", "Done")}</button>
            <button
              type="button"
              class="key key-primary flex-1"
              disabled={!selection.length || renames.running}
              onclick={renameNow}
            >
              {t("web_rename_selection", "Put away the selection")}<span class="legend"
                >{selection.length}</span
              >
            </button>
          </div>
        </div>
      </div>
    {:else}
      <div class="dock flex flex-wrap items-center gap-2.5 pt-4">
        {#if renaming}
          <button type="button" class="key" disabled
            >{t("web_putting_away", "Putting away…")}</button
          >
        {:else if selection.length}
          <button type="button" class="key key-primary" onclick={renameNow}>
            {t("web_rename_selection", "Put away the selection")}<span class="legend"
              >{selection.length}</span
            >
          </button>
        {:else if rows?.length}
          <button
            type="button"
            class="key key-primary"
            disabled={!ready.length || renames.running}
            onclick={renameNow}
          >
            {t(`web_rename_all_${mediaType}`, "Put away the movies")}<span class="legend"
              >{units(ready)}</span
            >
          </button>
        {/if}
      </div>
    {/if}
    {#if rows?.length}
      <p class="mt-3 text-[13px] text-muted max-[699px]:pb-4">
        {#if books && count("missing")}
          {tn(
            "web_books_missing_stay",
            count("missing"),
            "The book not recognized stays where it is.",
            "The {n} books not recognized stay where they are.",
          )}
        {/if}
        {modeNote}
      </p>
    {/if}

    {#snippet scene()}
      {#if rename && !renaming && rename.status !== "running"}
        <!-- The end of a rename. -->
        <div class="flex w-full flex-1 flex-col">
          <p class="label">{t("web_rename_over", "Put away")}</p>
          <p class="mt-2 text-[30px] leading-[34px] font-[650] tracking-[-0.035em]">
            {#if rename.status === "failed"}
              {t("web_rename_failed_short", "The rename failed")}<span class="text-muted">.</span>
            {:else}
              {tn(
                "web_files_put_away",
                rename.result?.renamed ?? 0,
                "{n} file put away",
                "{n} files put away",
              )}<span class="text-muted">.</span>
            {/if}
          </p>
          {#if rename.status === "failed"}
            <p class="mt-3 text-[14px] text-danger">
              {rename.error?.message ?? rename.error?.code}
            </p>
          {/if}
          {#if rename.result?.subtitles}
            <p class="mt-2 text-[14px] text-muted">
              {tn(
                "web_with_subtitles",
                rename.result.subtitles,
                "With {n} subtitle.",
                "With {n} subtitles.",
              )}
            </p>
          {/if}
          {#if left.length}
            <p class="label mt-6 mb-2">
              {tn("web_left_in_place", left.length, "{n} left in place", "{n} left in place")}
            </p>
            {#each left as item (item.file)}
              <div class="border-t border-line py-2">
                <p class="truncate font-mono text-[12.5px]">{item.file.split("/").pop()}</p>
                <p class="mt-0.5 text-[12.5px] text-caution">{item.why}</p>
              </div>
            {/each}
          {/if}
          {#if undone === rename.id}
            <p class="mt-6 text-[14px] text-muted">
              {t(
                "web_rename_undone",
                "Undone: the files are back where they were. The next analysis shows them here again.",
              )}
            </p>
          {:else if askUndo}
            <p class="mt-6 text-[14px] text-muted">
              {tn(
                "web_undo_ask",
                rename.result?.renamed ?? 0,
                "Put this file back where it was?",
                "Put these {n} files back where they were?",
              )}
            </p>
            <div class="mt-3 flex gap-2.5">
              <button type="button" class="key key-sm key-primary" onclick={undoRename}>
                {t("web_undo_yes", "Yes, undo")}
              </button>
              <button type="button" class="key key-sm" onclick={() => (askUndo = false)}>
                {t("web_keep", "Keep")}
              </button>
            </div>
          {/if}
          {#if !askUndo}
            <div class="mt-6 flex flex-wrap gap-2.5">
              {#if rename.result?.operation && undone !== rename.id}
                <button type="button" class="key key-sm" onclick={() => (askUndo = true)}>
                  {t("web_undo_this", "Undo this")}
                </button>
              {/if}
              {#if rename.result?.renamed}
                <a href={href("/history")} onclick={follow} class="key key-sm">
                  {t("web_see_history_short", "See the history")}
                </a>
              {/if}
              <button type="button" class="key key-sm" onclick={() => (dismissed = rename.id)}>
                {t("web_close", "Close")}
              </button>
            </div>
          {/if}
        </div>
      {:else if selection.length}
        <!-- The covers chosen. -->
        <div class="mt-3.5"></div>
        <Fan posters={selection.map((row) => matchOf(row)?.poster ?? "").filter(Boolean)} />
        <p class="mt-6 text-center text-[30px] leading-[34px] font-[650] tracking-[-0.035em]">
          {tn(`web_chosen_${mediaType}`, selection.length, "{n} movie chosen", "{n} movies chosen")}
        </p>
        <div class="mt-[26px] w-full"><Facts facts={selectionFacts} /></div>
      {:else if open && view === "pick"}
        <!-- What is it? The results, and a search. -->
        <div class="flex w-full flex-1 flex-col self-stretch">
          <p class="text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
            {t(whichKey, "Which movie is it?")}
          </p>
          <p class="mt-2 truncate font-mono text-[12.5px] text-faint">{was(open)}</p>
          <form class="mt-[18px]" onsubmit={search}>
            <input
              class="field h-[42px] border-accent text-[15px]"
              bind:value={query}
              aria-label={t("web_search_title", "Search a title")}
            />
          </form>
          {#if searching}
            <p class="mt-4 text-[14px] text-muted">{t("searching", "Searching...")}</p>
          {:else if searchMessage}
            <p class="mt-4 text-[14px] text-muted">{searchMessage}</p>
          {:else if !open.candidates.length}
            <p class="mt-4 text-[14px] text-muted">
              {t(
                "web_pick_none",
                "Nothing found for “{query}”. Search another title, or leave the file where it is.",
                { query: open.query ?? "" },
              )}
            </p>
          {/if}
          <div class="-mx-2.5 mt-4 grid gap-0.5">
            {#each open.candidates as candidate, index (index)}
              <button
                type="button"
                class={[
                  "grid cursor-pointer grid-cols-[34px_minmax(0,1fr)_auto] items-center gap-3.5 rounded-[9px] px-2.5 py-2 text-left hover:bg-raised",
                  index === open.selected && "bg-raised",
                ]}
                onclick={() => pick(index)}
              >
                <Thumb poster={candidate.poster} selectable={false} label="" />
                <span class="min-w-0">
                  <span class="block truncate text-[15px] font-semibold">{candidate.title}</span>
                  <span class="mt-[3px] block font-mono text-[12px] text-muted">
                    {[candidate.year, candidate.by].filter(Boolean).join(" · ")}
                  </span>
                  {#if candidate.overview}
                    <span class="mt-1 line-clamp-2 text-[12.5px] leading-[1.4] text-faint"
                      >{candidate.overview}</span
                    >
                  {/if}
                </span>
                {#if index === open.selected}
                  <span class="h-[18px] w-0.5 rounded-[1px] bg-accent"></span>
                {/if}
              </button>
            {/each}
          </div>
          <div class="flex-1"></div>
          {#if open.status === "ok"}
            <div class="flex justify-center pt-4">
              <button type="button" class="key key-sm" onclick={() => (view = "scene")}>
                {t("web_cancel", "Cancel")}
              </button>
            </div>
          {/if}
        </div>
      {:else if open}
        <!-- The scene of the open row. -->
        {@const match = matchOf(open)}
        {@const poster = bigPosterUrl(match?.poster ?? null)}
        <div
          class={[
            "shrink-0 rounded-xl bg-raised bg-cover bg-center shadow-[0_30px_60px_var(--drop),inset_0_1px_0_rgb(255_255_255/0.25)]",
            music ? "size-[240px]" : "h-[285px] w-[190px]",
            books && "rounded-[3px_8px_8px_3px]",
          ]}
          style:background-image={poster ? `url("${poster}")` : undefined}
        ></div>
        <div
          class={[
            "mt-[18px] h-5 rounded-[50%] bg-[radial-gradient(closest-side,var(--drop),transparent)]",
            music ? "w-[210px]" : "w-[170px]",
          ]}
        ></div>
        {#if episodic}
          <p class="mt-[22px] text-center text-[15px] text-muted">
            {[t("web_series", "Series"), match?.year].filter(Boolean).join(" · ")}
          </p>
          <p class="mt-1 text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
            {titleOf(open)}
          </p>
          <p class="mt-2.5 text-center text-[14px] text-muted">
            {seasonLine(open)} · {tn(
              "web_titles_found",
              open.files.filter((file) => episodeTitle(file)).length,
              "{n} title found",
              "{n} titles found",
            )}
          </p>
          <div class="mt-[18px] grid w-full grid-cols-7 gap-1.5">
            {#each open.files as file (file.path)}
              {@const code = episodeCode(file)}
              <span
                class={[
                  "rounded-[7px] bg-raised py-[7px] text-center font-mono text-[12px] shadow-[inset_0_1px_0_var(--color-hi)]",
                  !episodeTitle(file) && "text-faint",
                ]}
                title={episodeTitle(file) ?? file.name}
              >
                {code ? (seasonsOf(open).length > 1 ? code : code.slice(3)) : "?"}
              </span>
            {/each}
          </div>
        {:else if music}
          <p class="mt-[26px] text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
            {titleOf(open)}
          </p>
          <p class="mt-1.5 text-center text-[15px] text-muted">
            {[
              match?.by,
              match?.year,
              tn("web_n_tracks", open.files.length, "{n} track", "{n} tracks"),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <div class="mt-[18px] grid w-full">
            {#each open.files.slice(0, TRACKS_SHOWN) as file (file.path)}
              {@const track = trackOf(file)}
              <div
                class="grid grid-cols-[30px_minmax(0,1fr)] gap-2 border-t border-line py-[7px] text-[14px]"
              >
                <span class="font-mono text-[12.5px] text-faint">{track.number ?? "·"}</span>
                <span class="truncate">{track.title}</span>
              </div>
            {/each}
            {#if open.files.length > TRACKS_SHOWN}
              <div class="border-t border-line py-[7px] text-[13px] text-muted">
                {tn(
                  "web_more_tracks",
                  open.files.length - TRACKS_SHOWN,
                  "+ {n} track",
                  "+ {n} tracks",
                )}
              </div>
            {/if}
          </div>
        {:else}
          <p class="mt-[26px] text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
            {titleOf(open)}
          </p>
          {#if match?.year || match?.by}
            <p class="mt-1.5 text-center text-[15px] text-muted">
              {[match?.year, match?.by].filter(Boolean).join(" · ")}
            </p>
          {/if}
          <div class="mt-[26px] w-full"><Facts {facts} /></div>
        {/if}
        {#if open.files[0]?.new_name && folderOf(open)}
          <div class="mt-[22px] w-full">
            <p class="text-[13px] text-muted">{t("web_will_go_here", "Will be put here")}</p>
            <p class="mt-1.5 font-mono text-[13px] leading-[1.4] break-all">
              {targetOf(open)}
            </p>
            {#if destinations.length > 1}
              <div class="mt-2.5 flex flex-wrap gap-3.5 font-mono text-[13px] text-faint">
                {#each destinations as folder, index (folder)}
                  {@const on =
                    index === (open.destination < destinations.length ? open.destination : 0)}
                  <button
                    type="button"
                    class={[
                      "flex cursor-pointer items-center",
                      on ? "text-ink" : "hover:text-muted",
                    ]}
                    aria-pressed={on}
                    onclick={() => choose(index)}
                  >
                    {#if on}<span class="mr-[7px] size-1.5 rounded-full bg-accent"></span>{/if}
                    {folder}
                  </button>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
        <div class="mt-6 flex gap-2.5">
          <button type="button" class="key key-sm" onclick={() => openPicker(open)}>
            {t("web_not_it", "That's not it")}
          </button>
        </div>
      {/if}
    {/snippet}
  </Split>
{/if}
