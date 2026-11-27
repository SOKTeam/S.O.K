<script lang="ts">
  // The Settings: one page that scrolls, as the Settings of the desktop app.
  // A block per part (Folders, Behavior, Automatic sorting, Notifications,
  // File names, Sources, Appearance, Account, About), its title at the left,
  // dotted lines at the right; a line of a service opens in place. The scene
  // is a live preview that follows the block read: the name of an example
  // file, the rhythm of the automatic sorting, the message sent, the account.
  // Each block has its address (/settings/auto…), which the page follows.
  import { onMount, tick, untrack } from "svelte";

  import Split from "../components/layout/Split.svelte";
  import Choice from "../components/settings/Choice.svelte";
  import FolderPicker from "../components/settings/FolderPicker.svelte";
  import FolderRole from "../components/settings/FolderRole.svelte";
  import NamePreview from "../components/settings/NamePreview.svelte";
  import KeyLine from "../components/settings/KeyLine.svelte";
  import Line from "../components/settings/Line.svelte";
  import NotifyLine from "../components/settings/NotifyLine.svelte";
  import OpenBox from "../components/settings/OpenBox.svelte";
  import SortDial from "../components/settings/SortDial.svelte";
  import Switch from "../components/settings/Switch.svelte";
  import { errorText, linkFixText, linkProblemText } from "../lib/errors";
  import { parentFolder, splitName } from "../lib/format";
  import { loadHistory, type Operation } from "../lib/history";
  import { loadTexts, t, tn } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";
  import {
    EXAMPLE_COLORS,
    EXAMPLE_LIGHTS,
    EXAMPLES,
    FORMAT_KEYS,
    previewPath,
  } from "../lib/namePreview";
  import { MEDIA_PAGES } from "../lib/pages";
  import { replace, router } from "../lib/router.svelte";
  import { logOut, session } from "../lib/session.svelte";
  import {
    loadSettings,
    saveSettings,
    settings,
    type FileMode,
    type LinkCheck,
    type SettingsChange,
  } from "../lib/settings.svelte";
  import { chooseTheme, theme, THEME_CHOICES, type ThemeChoice } from "../lib/theme.svelte";
  import { loadWatch, watch } from "../lib/watch.svelte";

  const DOCS_URL = "https://sokteam.github.io/S.O.K/";

  let error = $state("");
  let folderErrors = $state<Record<string, string>>({});
  // The one line open: "key:tmdb", "notify:discord", "format:movies"…
  let openLine = $state<string | null>(null);
  // The role whose folder is picked in the scene: "sources", "movies"…
  let browsing = $state<string | null>(null);
  // The models being typed, saved with their key.
  let models = $state<Record<string, string>>({});
  // Turning the automatic sorting on asks first, in place.
  let askAuto = $state(false);
  let minutes = $state<string | null>(null);
  // The hard link problems read with "Got it": a new one shows again.
  let dismissed = $state<string[]>([]);
  let operations = $state<Operation[]>([]);
  let now = $state(new Date());
  let pane = $state<HTMLElement>();

  const data = $derived(settings.data);

  onMount(() => {
    loadSettings().catch((exc) => (error = errorText(exc)));
    if (!watch.status) loadWatch().catch(() => {});
    loadHistory()
      .then((found) => (operations = found))
      .catch(() => {});
    const clock = setInterval(() => (now = new Date()), 20_000);
    return () => {
      clearInterval(clock);
      setLight(null);
    };
  });

  async function save(change: SettingsChange): Promise<boolean> {
    error = "";
    try {
      await saveSettings(change);
      return true;
    } catch (exc) {
      error = errorText(exc);
      return false;
    }
  }

  const onerror = (exc: unknown) => (error = errorText(exc));

  function toggle(line: string) {
    openLine = openLine === line ? null : line;
  }

  // ------------------------------------------------------------ Blocks

  type Block =
    | "folders"
    | "behavior"
    | "auto"
    | "notifications"
    | "names"
    | "sources"
    | "appearance"
    | "account"
    | "about";

  const BLOCKS: Block[] = [
    "folders",
    "behavior",
    "auto",
    "notifications",
    "names",
    "sources",
    "appearance",
    "account",
    "about",
  ];
  // The addresses of the tabs of before 1.6.
  const OLD: Record<string, Block> = { rename: "behavior", keys: "sources", look: "appearance" };

  function blockOf(path: string): Block {
    const name = path.replace(/^\/settings\/?/, "");
    return OLD[name] ?? (BLOCKS.includes(name as Block) ? (name as Block) : "folders");
  }

  const addressOf = (block: Block) => (block === "folders" ? "/settings" : `/settings/${block}`);

  let block = $state<Block>(untrack(() => blockOf(router.path)));
  // The address the page set itself while scrolling: not a move to make.
  let followed = "";
  // The block asked for by an address: at the end of the page several blocks
  // fit on the screen, so the one asked for stays the block read.
  let aimed: Block | null = null;

  /** The block read: the last one whose top is above the reading line. */
  function follow() {
    if (!pane) return;
    const top = pane.getBoundingClientRect().top;
    // The last blocks never reach the top: over the last half screen of
    // scrolling, the reading line slides down so each one gets its turn.
    const remaining = pane.scrollHeight - pane.clientHeight - pane.scrollTop;
    const atEnd = remaining <= 2;
    const reach = pane.clientHeight / 2;
    const slide = remaining >= reach ? 0 : 1 - remaining / reach;
    const line = top + 110 + slide * (pane.clientHeight - 190);
    let found: Block = "folders";
    for (const element of pane.querySelectorAll<HTMLElement>("[data-block]")) {
      if (element.getBoundingClientRect().top <= line) found = element.dataset.block as Block;
    }
    if (!atEnd) aimed = null;
    else if (aimed) found = aimed;
    if (found !== block) {
      block = found;
      followed = addressOf(found);
      replace(followed);
    }
  }

  async function scrollTo(target: Block) {
    await tick();
    const element = pane?.querySelector<HTMLElement>(`[data-block="${target}"]`);
    if (!pane || !element) return;
    pane.scrollTop =
      target === "folders"
        ? 0
        : element.getBoundingClientRect().top -
          pane.getBoundingClientRect().top +
          pane.scrollTop -
          20;
    block = target;
    aimed = target;
  }

  // An address given (a link, the start): go to its block once it is there.
  $effect(() => {
    const path = router.path;
    const ready = Boolean(data);
    untrack(() => {
      if (!ready || path === followed) return;
      followed = path;
      scrollTo(blockOf(path));
    });
  });

  // ------------------------------------------------------------ Folders

  const ROLES = $derived([
    { role: "sources", label: t("web_watched", "Watched") },
    ...MEDIA_PAGES.map((page) => ({ role: page.mediaType!, label: t(page.key, page.english) })),
  ]);

  async function saveFolders(role: string, paths: string[]) {
    folderErrors[role] = "";
    try {
      await saveSettings({ folders: { [role]: paths } });
    } catch (exc) {
      folderErrors[role] = errorText(exc);
    }
  }

  /** Where the browser opens: next to the last folder of the role. */
  function startOf(role: string): string | undefined {
    const paths = data?.folders[role] ?? [];
    if (paths.length) return parentFolder(paths[paths.length - 1]);
    const sources = data?.folders.sources ?? [];
    return sources.length ? parentFolder(sources[0]) : undefined;
  }

  function pickFolder(path: string) {
    const role = browsing;
    browsing = null;
    if (!role || !data) return;
    const paths = data.folders[role];
    if (!paths.includes(path)) saveFolders(role, [...paths, path]);
  }

  // ------------------------------------------------------------ Behavior

  const FILE_MODES: FileMode[] = ["link", "copy", "move"];

  function modeName(mode: FileMode): string {
    switch (mode) {
      case "link":
        return t("file_mode_link", "Hard link");
      case "copy":
        return t("file_mode_copy", "Copy");
      case "move":
        return t("file_mode_move", "Move");
    }
  }

  function modeText(mode: FileMode): string {
    switch (mode) {
      case "link":
        return t(
          "file_mode_hint",
          "A hard link leaves the original in place, so torrents keep seeding, without using more space. The destination must be on the same drive.",
        );
      case "copy":
        return t(
          "web_file_mode_copy_hint",
          "The original stays in place and a copy is renamed: it takes the space twice.",
        );
      case "move":
        return t(
          "web_file_mode_move_hint",
          "The file leaves the downloads: a torrent of it stops seeding.",
        );
    }
  }

  const mode = $derived((data?.settings.file_mode ?? "link") as FileMode);

  const keyOf = (check: LinkCheck) => `${check.source}|${check.destination}|${check.problem}`;
  const problems = $derived(
    mode === "link" ? (data?.link_checks ?? []).filter((check) => !check.ok) : [],
  );
  const shownProblems = $derived(problems.filter((check) => !dismissed.includes(keyOf(check))));

  const BEHAVIOR = [
    ["create_folders", () => t("create_missing_folders", "Create missing folders")],
    ["download_posters", () => t("download_posters", "Download posters")],
    ["backup_before_rename", () => t("backup_before_rename", "Backup before rename")],
    ["skip_duplicates", () => t("skip_duplicates", "Skip duplicates")],
    ["subtitles_follow_video", () => t("subtitles_follow_video", "Move subtitles with videos")],
  ] as const;

  // ------------------------------------------------------------ Automatic sorting

  async function saveAuto(on: boolean) {
    askAuto = false;
    if (await save({ settings: { auto_sort: on } })) loadWatch().catch(() => {});
  }

  // The free room kept on each disk, while typed.
  let margin = $state<string | null>(null);

  async function saveMargin() {
    const value = Number(margin);
    if (
      margin !== null &&
      Number.isInteger(value) &&
      value !== data?.settings.free_space_margin_gb
    ) {
      await save({ settings: { free_space_margin_gb: value } });
    }
    // A refused value gives the field back its saved one.
    margin = null;
  }

  async function saveMinutes() {
    const value = Number(minutes);
    if (minutes !== null && Number.isInteger(value) && value !== data?.settings.auto_sort_minutes) {
      if (await save({ settings: { auto_sort_minutes: value } })) loadWatch().catch(() => {});
    }
    // A refused value gives the field back its saved one.
    minutes = null;
  }

  // ------------------------------------------------------------ Names

  const VARIABLES: Record<string, string> = {
    movies: "{title} {year} {quality}",
    tv: "{title} {season} {episode} {episode_title} {season_num} {episode_num}",
    music: "{artist} {album} {track} {title} {year} /",
    books: "{author} {title} {year} {series} {series_number}",
    games: "{title} {year} {platform} {tags}",
  };

  const modelOf = (type: string) => models[type] ?? String(data?.settings[FORMAT_KEYS[type]] ?? "");

  async function saveModel(type: string) {
    const value = models[type];
    if (value === undefined) return;
    // A refused model (empty) gives the field back its saved one.
    if (await save({ settings: { [FORMAT_KEYS[type]]: value } })) {
      delete models[type];
      openLine = null;
    }
  }

  // ------------------------------------------------------------ Sources

  const CATEGORIES = [
    ["video", "preferred_api_video", () => t("web_sources_video", "Movies and TV shows")],
    ["music", "preferred_api_music", () => t("music", "Music")],
    ["books", "preferred_api_books", () => t("books", "Books")],
    ["games", "preferred_api_games", () => t("games", "Games")],
    ["images", null, () => t("web_sources_images", "Posters and covers")],
  ] as const;

  /** The services of a category, those with a key and the free ones. */
  function servicesOf(mediaType: string) {
    const listed = data?.services[mediaType] ?? [];
    const keyed = (data?.keys ?? []).filter((service) => service.media_type === mediaType);
    const ids = [...listed.map((s) => s.id), ...keyed.map((s) => s.service)];
    return [...new Set(ids)].map((id) => ({
      id,
      name: listed.find((s) => s.id === id)?.name ?? keyed.find((s) => s.service === id)!.name,
      keys: keyed.find((s) => s.service === id) ?? null,
    }));
  }

  // ------------------------------------------------------------ Appearance

  function themeName(choice: ThemeChoice): string {
    switch (choice) {
      case "system":
        return t("web_theme_system", "System");
      case "light":
        return t("web_theme_light", "Light");
      case "dark":
        return t("web_theme_dark", "Dark");
    }
  }

  /** The name of a language in that language: "fr" → "Français". */
  function languageName(code: string): string {
    const name = new Intl.DisplayNames([code], { type: "language" }).of(code) ?? code;
    return name.charAt(0).toLocaleUpperCase(code) + name.slice(1);
  }

  async function changeLanguage(language: string) {
    if (await save({ settings: { language } })) await loadTexts(language);
  }

  // ------------------------------------------------------------ The scene

  type Scene = "browse" | "file" | "auto" | "notify" | "account";
  const SCENES: Partial<Record<Block, Scene>> = {
    auto: "auto",
    notifications: "notify",
    account: "account",
    about: "account",
  };
  const view = $derived<Scene>(browsing ? "browse" : (SCENES[block] ?? "file"));

  // The example of the preview: the type whose model or folders are open.
  const example = $derived.by(() => {
    const open = openLine?.startsWith("format:") ? openLine.slice(7) : null;
    if (open) return open;
    return block === "folders" && browsing && browsing !== "sources" ? browsing : "movies";
  });

  // The preview of the File names block, under 1000px.
  const small = $derived(
    data
      ? previewPath(
          example,
          modelOf(example),
          data.folders[example]?.[0] ?? "",
          t("season", "Season"),
        )
      : null,
  );
  $effect(() => {
    if (view === "file") setLight(EXAMPLE_LIGHTS[example]);
    else if (view === "auto") setLight(data?.settings.auto_sort ? "251, 96, 72" : null);
    else if (view === "notify") setLight("88, 101, 242");
    else setLight(null);
  });

  const clock = (date: string | Date) =>
    new Date(date).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });

  /** What a rename was about: a series, an album, or the file renamed. */
  function titleOf(op: Operation): string {
    const target = op.files.find((file) => !file.follows)?.target ?? "";
    const parts = target.split("/").filter(Boolean);
    if (op.media_type === "tv") return parts[parts.length - 3] ?? "";
    if (op.media_type === "music") return parts[parts.length - 2] ?? "";
    return splitName(target).name.replace(/\.[^.]+$/, "");
  }

  const videos = (op: Operation) => op.files.filter((file) => !file.follows);

  // The last automatic renames, for the rhythm.
  const runs = $derived(operations.filter((op) => op.auto).slice(0, 3));

  const pageName = (mediaType: string) => {
    const page = MEDIA_PAGES.find((p) => p.mediaType === mediaType);
    return page ? t(page.key, page.english) : mediaType;
  };

  // The message Discord gets after a rename, as notify.py writes it: of the
  // last rename, or of the example movie.
  const message = $derived.by(() => {
    const op = operations[0];
    if (!op) {
      return {
        type: pageName("movies"),
        auto: false,
        count: 1,
        names: [`${EXAMPLES.movies.title} (${EXAMPLES.movies.year}).mkv`],
        date: null as string | null,
      };
    }
    const files = op.files.map((file) => splitName(file.target).name);
    return {
      type: pageName(op.media_type),
      auto: op.auto,
      count: files.length,
      names: files,
      date: op.date,
    };
  });

  // The apps told after each rename, and what they do.
  const told = $derived.by(() => {
    const notify = data?.notifications;
    if (!notify) return [];
    return [
      notify.discord.set && ["Discord", t("web_told_discord", "a message")],
      notify.jellyfin.url &&
        notify.jellyfin.set && ["Jellyfin", t("web_told_refresh", "refreshes the libraries")],
      notify.plex.url &&
        notify.plex.set && ["Plex", t("web_told_refresh", "refreshes the libraries")],
      notify.webhook.set && [
        t("web_notify_webhook", "Webhook"),
        t("web_told_webhook", "the sorting as JSON"),
      ],
      notify.script && [t("web_notify_script", "Script"), t("web_told_script", "runs its command")],
    ].filter(Boolean) as [string, string][];
  });
</script>

{#snippet head(title: string, text?: string)}
  <h2 class="m-0 text-[18px] leading-6 font-[650] tracking-[-0.025em]">
    {title}
    {#if text}
      <small
        class="mt-1.5 block max-w-[180px] text-[13px] leading-[1.45] font-normal tracking-normal text-faint"
      >
        {text}
      </small>
    {/if}
  </h2>
{/snippet}

{#snippet group(title: string)}
  <p class="mt-[18px] mb-1 text-[14px] font-semibold text-muted first:mt-0">{title}</p>
{/snippet}

{#snippet hint(text: string)}
  <p class="mt-0.5 mb-2 max-w-[600px] text-[13px] leading-[1.5] text-faint">{text}</p>
{/snippet}

<Split bind:pane onscroll={follow} open={browsing !== null} onclose={() => (browsing = null)} sheet>
  <h1 class="m-0 mb-[18px] text-[50px] leading-[1.04] font-[650] tracking-[-0.04em]">
    {t("settings", "Settings")}<span class="text-muted">.</span>
  </h1>

  {#if error}
    <p
      class="sticky top-0 z-10 mb-2 rounded-[10px] bg-surface px-4 py-2.5 text-[14px] text-danger shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line)]"
      role="alert"
    >
      {error}
    </p>
  {/if}

  {#if data}
    <div class="pb-12">
      <!-- Folders -->
      <section
        data-block="folders"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(
          t("web_folders", "Folders"),
          t(
            "web_folders_text",
            "The paths as the server sees them: in Docker, the folders mounted in the container.",
          ),
        )}
        <div>
          {@render group(t("web_sources_group", "Sources"))}
          {#each ROLES as { role, label }, index (role)}
            {#if index === 1}{@render group(t("web_destinations", "Destinations"))}{/if}
            <FolderRole
              {label}
              paths={data.folders[role]}
              browsing={browsing === role}
              error={folderErrors[role]}
              onbrowse={() => (browsing = browsing === role ? null : role)}
              onremove={(path) =>
                saveFolders(
                  role,
                  data.folders[role].filter((p) => p !== path),
                )}
            />
          {/each}
        </div>
      </section>

      <!-- Behavior -->
      <section
        data-block="behavior"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(t("behavior", "Behavior"))}
        <div>
          <Line label={t("file_mode", "File mode")}>
            <Choice
              label={t("file_mode", "File mode")}
              options={FILE_MODES.map((value) => ({ value, label: modeName(value) }))}
              value={mode}
              onchoose={(value) => save({ settings: { file_mode: value } })}
            />
          </Line>
          {@render hint(modeText(mode))}
          {#each shownProblems as problem (keyOf(problem))}
            <div
              class="mt-2 mb-1 rounded-[10px] bg-[color-mix(in_srgb,var(--color-caution)_10%,transparent)] px-3.5 py-3 text-[13.5px] leading-[1.5] text-muted shadow-[inset_0_0_0_1px_color-mix(in_srgb,var(--color-caution)_30%,transparent)]"
              role="alert"
            >
              <b class="font-semibold text-caution">
                {t("web_links_fail_to", "Hard links will not work to {folder}.", {
                  folder: problem.destination,
                })}
              </b>
              {linkProblemText(problem.problem ?? "", problem.source, problem.destination)}
              {t("web_link_fix", "To fix it:")}
              {linkFixText(problem.problem ?? "")}
              <div class="mt-2.5 flex gap-2">
                <button
                  type="button"
                  class="key key-sm"
                  onclick={() => save({ settings: { file_mode: "copy" } })}
                >
                  {t("web_use_copy", "Use Copy")}
                </button>
                <button
                  type="button"
                  class="key key-sm"
                  onclick={() => (dismissed = [...dismissed, keyOf(problem)])}
                >
                  {t("web_understood", "Got it")}
                </button>
              </div>
            </div>
          {/each}
          {#if mode === "link" && !problems.length && data.link_checks.length}
            <p class="mb-2 text-[13px] text-muted">
              ✓ {t("web_links_ok", "Hard links work between your folders.")}
            </p>
          {/if}
          <div class="mt-1">
            {#each BEHAVIOR as [key, label] (key)}
              <Switch
                label={label()}
                checked={Boolean(data.settings[key])}
                onchange={(checked) => save({ settings: { [key]: checked } })}
              />
            {/each}
          </div>
          <Line label={t("web_free_space_keep", "Keep free on each disk")}>
            <label
              class="flex h-7 items-center gap-1 rounded-[7px] bg-raised px-2.5 font-mono text-[13px] text-ink shadow-[inset_0_0_0_1px_var(--color-line-strong)] focus-within:shadow-[inset_0_0_0_1px_var(--color-accent)]"
            >
              <input
                type="number"
                min="0"
                max="10000"
                class="w-12 [appearance:textfield] bg-transparent text-right outline-none [&::-webkit-inner-spin-button]:appearance-none"
                value={margin ?? data.settings.free_space_margin_gb ?? 1}
                oninput={(event) => (margin = event.currentTarget.value)}
                onchange={saveMargin}
                aria-label={t("web_free_space_keep_gb", "Keep free on each disk (GB)")}
              />
              {t("web_gb", "GB")}
            </label>
          </Line>
          {@render hint(
            t(
              "web_free_space_hint",
              "Before sorting, the server checks that the disks receiving copies keep this room. A hard link, or a move on the same disk, takes none.",
            ),
          )}
        </div>
      </section>

      <!-- Automatic sorting -->
      <section
        data-block="auto"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(
          t("web_auto_sort", "Automatic sorting"),
          t("web_auto_sort_short", "The server looks at the source folders on its own."),
        )}
        <div>
          <Switch
            label={t("web_auto_sort_switch", "Sort the new files automatically")}
            checked={Boolean(data.settings.auto_sort) || askAuto}
            onchange={(checked) => (checked ? (askAuto = true) : saveAuto(false))}
          />
          {#if askAuto}
            <OpenBox
              text={t(
                "web_auto_sort_confirm_detail",
                "Every ready file will be sorted on its own, those already waiting on their screens too, with the file mode “{mode}”. The history can undo it.",
                { mode: modeName(mode) },
              )}
            >
              <div class="flex gap-2">
                <button type="button" class="key key-sm" onclick={() => saveAuto(true)}>
                  {t("web_turn_on", "Turn on")}
                </button>
                <button type="button" class="key key-sm" onclick={() => (askAuto = false)}>
                  {t("web_cancel", "Cancel")}
                </button>
              </div>
            </OpenBox>
          {/if}
          {@render hint(
            t(
              "web_auto_sort_hint",
              "Once downloaded, the new files are analyzed and those that are ready are sorted. The others wait on their screen.",
            ),
          )}
          <Line label={t("web_auto_sort_look_every", "Look at the folders every")}>
            <label
              class="flex h-7 items-center gap-1 rounded-[7px] bg-raised px-2.5 font-mono text-[13px] text-ink shadow-[inset_0_0_0_1px_var(--color-line-strong)] focus-within:shadow-[inset_0_0_0_1px_var(--color-accent)]"
            >
              <input
                type="number"
                min="1"
                max="1440"
                class="w-10 [appearance:textfield] bg-transparent text-right outline-none [&::-webkit-inner-spin-button]:appearance-none"
                value={minutes ?? data.settings.auto_sort_minutes}
                oninput={(event) => (minutes = event.currentTarget.value)}
                onchange={saveMinutes}
                aria-label={t("web_auto_sort_minutes", "Check the folders every (minutes)")}
              />
              min
            </label>
          </Line>
        </div>
      </section>

      <!-- Notifications -->
      <section
        data-block="notifications"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(
          t("web_notifications", "Notifications"),
          t(
            "web_notifications_text",
            "After each rename, by hand or automatic, S.O.K Server can tell your other apps.",
          ),
        )}
        <div>
          <NotifyLine
            target="discord"
            name="Discord"
            text={t(
              "web_notify_discord_text",
              "A message in a channel. Webhook address: settings of the channel → Integrations → Webhooks.",
            )}
            set={data.notifications.discord.set}
            fields={[
              {
                key: "discord_url",
                secret: true,
                set: data.notifications.discord.set,
                example: "https://discord.com/api/webhooks/…",
              },
            ]}
            open={openLine === "notify:discord"}
            ontoggle={() => toggle("notify:discord")}
            {onerror}
          />
          <NotifyLine
            target="jellyfin"
            name="Jellyfin"
            text={t(
              "web_notify_jellyfin_text",
              "Refreshes the libraries. API key: Dashboard → API Keys.",
            )}
            set={Boolean(data.notifications.jellyfin.url) && data.notifications.jellyfin.set}
            fields={[
              {
                key: "jellyfin_url",
                secret: false,
                value: data.notifications.jellyfin.url,
                set: Boolean(data.notifications.jellyfin.url),
                example: "http://jellyfin:8096",
              },
              {
                key: "jellyfin_key",
                secret: true,
                set: data.notifications.jellyfin.set,
                example: t("web_your_key", "Your API key…"),
              },
            ]}
            open={openLine === "notify:jellyfin"}
            ontoggle={() => toggle("notify:jellyfin")}
            {onerror}
          />
          <NotifyLine
            target="plex"
            name="Plex"
            text={t("web_notify_plex_text", "Refreshes the libraries, with your Plex token.")}
            set={Boolean(data.notifications.plex.url) && data.notifications.plex.set}
            fields={[
              {
                key: "plex_url",
                secret: false,
                value: data.notifications.plex.url,
                set: Boolean(data.notifications.plex.url),
                example: "http://plex:32400",
              },
              {
                key: "plex_token",
                secret: true,
                set: data.notifications.plex.set,
                example: "X-Plex-Token",
              },
            ]}
            open={openLine === "notify:plex"}
            ontoggle={() => toggle("notify:plex")}
            {onerror}
          />
          <NotifyLine
            target="webhook"
            name={t("web_notify_webhook", "Webhook")}
            text={t(
              "web_notify_webhook_text",
              "The rename as JSON, for Home Assistant, n8n and other tools.",
            )}
            set={data.notifications.webhook.set}
            fields={[
              {
                key: "webhook_url",
                secret: true,
                set: data.notifications.webhook.set,
                example: "https://…",
              },
            ]}
            open={openLine === "notify:webhook"}
            ontoggle={() => toggle("notify:webhook")}
            {onerror}
          />
          <NotifyLine
            target="script"
            name={t("web_notify_script", "Script")}
            text={data.notifications.script
              ? t(
                  "web_notify_script_set",
                  "Set by the SOK_AFTER_RENAME variable: it runs after each rename, with the rename as JSON on its input.",
                )
              : t(
                  "web_notify_script_text",
                  "A command run after each rename, with the rename as JSON on its input. For safety, only the SOK_AFTER_RENAME variable of the container sets it.",
                )}
            set={data.notifications.script}
            fields={[]}
            open={openLine === "notify:script"}
            ontoggle={() => toggle("notify:script")}
            {onerror}
          />
        </div>
      </section>

      <!-- File names -->
      <section
        data-block="names"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(t("web_file_names", "File names"))}
        <div>
          <!-- Under 1000px the scene is gone: the preview is a card here. -->
          <div
            class="mb-3 grid grid-cols-[54px_minmax(0,1fr)] items-center gap-3 rounded-xl bg-surface p-2.5 shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line)] min-[1000px]:hidden"
          >
            <div
              class="h-20 w-[54px] rounded-md"
              style:background={`linear-gradient(170deg, ${EXAMPLE_COLORS[example][0]}, ${EXAMPLE_COLORS[example][1]})`}
              aria-hidden="true"
            ></div>
            <div class="min-w-0 font-mono text-[11.5px] leading-[1.4] break-all">
              <p class="text-faint">{EXAMPLES[example].before}</p>
              <p class="mt-1.5 text-ink">
                {#if small}{#each small as piece, i (i)}<span
                      class={piece.filled ? "text-accent-text" : ""}>{piece.text}</span
                    >{/each}{:else}<span class="font-sans text-faint"
                    >{t("web_preview_none", "No name with this model.")}</span
                  >{/if}
              </p>
            </div>
          </div>
          {#each MEDIA_PAGES as page (page.path)}
            {@const type = page.mediaType!}
            {@const line = `format:${type}`}
            <Line
              label={t(page.key, page.english)}
              value={String(data.settings[FORMAT_KEYS[type]])}
              open={openLine === line}
              onclick={() => toggle(line)}
            />
            {#if openLine === line}
              <OpenBox>
                <form
                  onsubmit={(event) => {
                    event.preventDefault();
                    saveModel(type);
                  }}
                >
                  <!-- svelte-ignore a11y_autofocus -->
                  <input
                    class="field h-[38px] font-mono text-[13px]"
                    value={modelOf(type)}
                    oninput={(event) => (models[type] = event.currentTarget.value)}
                    aria-label={t(page.key, page.english)}
                    spellcheck="false"
                    autocomplete="off"
                    autofocus
                  />
                </form>
                <p class="mt-2 text-[12px] leading-[1.5] text-faint">
                  <code class="font-mono">{VARIABLES[type]}</code>
                  {#if type === "music"}· {t("web_slash_folder", "a / makes a folder")}{/if}
                </p>
                <div class="mt-2.5 flex gap-2">
                  <button
                    type="button"
                    class="key key-sm"
                    disabled={models[type] === undefined ||
                      models[type] === data.settings[FORMAT_KEYS[type]]}
                    onclick={() => saveModel(type)}
                  >
                    {t("web_save", "Save")}
                  </button>
                  <button
                    type="button"
                    class="key key-sm"
                    onclick={() => {
                      delete models[type];
                      openLine = null;
                    }}
                  >
                    {t("web_cancel", "Cancel")}
                  </button>
                </div>
              </OpenBox>
            {/if}
          {/each}
        </div>
      </section>

      <!-- Sources -->
      <section
        data-block="sources"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(
          t("web_sources", "Sources"),
          t("web_sources_text", "The services where S.O.K looks for the titles."),
        )}
        <div>
          {#each CATEGORIES as [mediaType, setting, label] (mediaType)}
            {@const services = servicesOf(mediaType)}
            {#if services.length}
              {@render group(label())}
              {#if setting && (data.services[mediaType]?.length ?? 0) > 1}
                <Line label={t("web_searched_first", "Searched first")}>
                  <Choice
                    label={t("web_searched_first", "Searched first")}
                    options={data.services[mediaType].map((s) => ({ value: s.id, label: s.name }))}
                    value={String(data.settings[setting])}
                    onchoose={(value) => save({ settings: { [setting]: value } })}
                  />
                </Line>
              {/if}
              {#each services as service (service.id)}
                {#if service.keys}
                  <KeyLine
                    service={service.keys}
                    open={openLine === `key:${service.id}`}
                    ontoggle={() => toggle(`key:${service.id}`)}
                    onerror={(exc) => (error = errorText(exc))}
                  />
                {:else}
                  <Line label={service.name} value={t("web_free", "Free")} tone="muted" />
                {/if}
              {/each}
            {/if}
          {/each}
          <p class="mt-2.5 text-[13px] leading-[1.5] text-faint">
            {t(
              "web_sources_private",
              "Only the names searched are sent. Your files stay on your server.",
            )}
          </p>
        </div>
      </section>

      <!-- Appearance -->
      <section
        data-block="appearance"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(t("appearance", "Appearance"))}
        <div>
          <Line label={t("web_theme", "Theme")}>
            <Choice
              label={t("web_theme", "Theme")}
              options={THEME_CHOICES.map((value) => ({ value, label: themeName(value) }))}
              value={theme.choice}
              onchoose={chooseTheme}
            />
          </Line>
          {@render hint(t("web_theme_here", "Kept in this browser."))}
          <Line label={t("language", "Language")}>
            <select
              class="cursor-pointer appearance-none bg-transparent pr-4 text-right text-[13.5px] text-ink outline-none [background:linear-gradient(45deg,transparent_50%,currentColor_50%)_right_4px_center/5px_5px_no-repeat,linear-gradient(-45deg,transparent_50%,currentColor_50%)_right_0_center/5px_5px_no-repeat]"
              value={data.settings.language}
              onchange={(event) => changeLanguage(event.currentTarget.value)}
              aria-label={t("language", "Language")}
            >
              {#each data.languages as code (code)}
                <option value={code}>{languageName(code)}</option>
              {/each}
            </select>
          </Line>
          {@render hint(
            t("web_language_text", "The interface and the names of the folders (“Season”)."),
          )}
        </div>
      </section>

      <!-- Account -->
      <section
        data-block="account"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(t("web_account", "Account"))}
        <div>
          {#if session.current?.auth === "none"}
            <Line
              label={t("web_login", "Login")}
              value={t("web_login_off", "Turned off (SOK_AUTH=none)")}
              tone="caution"
            />
          {:else}
            <Line
              label={t("web_logged_in_as", "Logged in as")}
              value={session.current?.username ?? ""}
              tone="ui"
            />
            <div class="mt-2.5">
              <button type="button" class="key key-sm" onclick={logOut}
                >{t("web_log_out", "Log out")}</button
              >
            </div>
          {/if}
        </div>
      </section>

      <!-- About -->
      <section
        data-block="about"
        class="grid grid-cols-[200px_minmax(0,1fr)] gap-x-6 border-t border-line py-6 max-[699px]:grid-cols-1 max-[699px]:gap-y-3 max-[699px]:py-[18px]"
      >
        {@render head(t("about", "About"))}
        <div>
          <Line label={t("version", "Version")} value={data.about.version} />
          <Line label={t("web_data", "Data")} value={data.about.data} />
          <div class="mt-2.5">
            <a class="key key-sm" href={DOCS_URL} target="_blank" rel="noreferrer">
              {t("web_documentation", "Documentation")} ↗
            </a>
          </div>
        </div>
      </section>
    </div>
  {/if}

  {#snippet scene()}
    {#if !data}
      <div></div>
    {:else if view === "browse" && browsing}
      <FolderPicker
        title={t("web_folder_for", "A folder for {role}", {
          role: ROLES.find((r) => r.role === browsing)?.label ?? "",
        })}
        start={startOf(browsing)}
        onpick={pickFolder}
        oncancel={() => (browsing = null)}
      />
    {:else if view === "file"}
      <NamePreview
        label={t("web_live_preview", "Live preview")}
        type={example}
        model={modelOf(example)}
        destination={data.folders[example]?.[0] ?? ""}
        source={data.folders.sources[0] ?? ""}
        {mode}
      />
    {:else if view === "auto"}
      {@const status = watch.status}
      <p class="label mb-[26px] self-stretch">{t("web_live_preview", "Live preview")}</p>
      <SortDial
        enabled={Boolean(data.settings.auto_sort)}
        minutes={Number(data.settings.auto_sort_minutes)}
        lastCheck={status?.last_check ? new Date(status.last_check) : null}
        {now}
      />
      <div class="mt-[30px] grid self-stretch">
        {#if status?.last_check}
          <div
            class="grid grid-cols-[54px_minmax(0,1fr)] items-baseline gap-3 py-[9px] text-[13.5px] text-muted"
          >
            <span class="font-mono text-[13px] text-faint">{clock(status.last_check)}</span>
            <span>{t("web_sort_last_look", "Last look at the folders")}</span>
          </div>
        {/if}
        {#each runs as op (op.id)}
          <div
            class="grid grid-cols-[54px_minmax(0,1fr)_auto] items-baseline gap-3 border-t border-line py-[9px] text-[13.5px] text-muted"
          >
            <span class="font-mono text-[13px] text-faint">{clock(op.date)}</span>
            <span class="min-w-0 truncate">
              <b class="font-medium text-ink"
                >{tn(
                  "web_files_sorted",
                  videos(op).length,
                  "{n} file sorted",
                  "{n} files sorted",
                )}</b
              >{#if titleOf(op)}, {titleOf(op)}{/if}
            </span>
            <span class="font-mono text-[12.5px] text-faint">auto</span>
          </div>
        {/each}
        {#if !runs.length && !status?.last_check}
          <p class="text-center text-[13.5px] text-muted">
            {t("web_sort_no_run", "No automatic sorting yet.")}
          </p>
        {/if}
      </div>
    {:else if view === "notify"}
      <p class="label mb-[26px] self-stretch">{t("web_live_preview", "Live preview")} · Discord</p>
      <div
        class="grid grid-cols-[40px_minmax(0,1fr)] gap-3.5 self-stretch rounded-xl bg-surface px-[18px] py-4 shadow-[inset_0_1px_0_var(--color-hi),0_0_0_1px_var(--color-line),0_30px_60px_var(--drop)]"
      >
        <div
          class="flex size-10 items-center justify-center rounded-full bg-key text-ink"
          aria-hidden="true"
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 512 508"
            fill="none"
            stroke="currentColor"
            stroke-width="40"
            stroke-linejoin="round"
            stroke-linecap="round"
            ><path d="M124 121 256 62 442 146 256 229 70 146 70 360 256 446 442 360 442 146" /><path
              d="M256 284V446"
              class="stroke-accent"
            /></svg
          >
        </div>
        <div class="min-w-0">
          <p class="text-[14px] font-semibold">
            S.O.K Server{#if message.date}<small
                class="ml-2 font-mono text-[11px] font-normal text-faint"
                >{clock(message.date)}</small
              >{/if}
          </p>
          <div class="mt-1 text-[14px] leading-[1.5] text-muted">
            <p><b class="font-semibold text-ink">S.O.K Server</b> · {message.type}</p>
            <p>
              {message.auto
                ? t("notify_auto_renamed", "Files sorted automatically: {n}", { n: message.count })
                : t("notify_renamed", "Files renamed: {n}", { n: message.count })}
            </p>
            {#each message.names.slice(0, 3) as name, i (i)}
              <p class="truncate font-mono text-[12.5px] text-ink">• {name}</p>
            {/each}
            {#if message.names.length > 3}
              <p>{t("notify_more", "…and {n} more", { n: message.names.length - 3 })}</p>
            {/if}
          </div>
        </div>
      </div>
      <p class="label mt-[30px] mb-2 self-stretch">
        {t("web_after_each_rename", "After each sorting")}
      </p>
      <div class="grid self-stretch">
        {#each told as [name, does] (name)}
          <Line label={name} value={does} tone="muted" />
        {:else}
          <p class="text-[13.5px] text-muted">{t("web_told_nobody", "No app is told yet.")}</p>
        {/each}
      </div>
    {:else}
      {@const name = session.current?.username ?? ""}
      <p class="label mb-[26px] self-stretch">{t("web_your_account", "Your account")}</p>
      <div
        class="flex size-24 items-center justify-center rounded-full bg-linear-[165deg] from-key to-surface text-[38px] font-[650] tracking-[-0.03em] shadow-[inset_0_0_0_1px_var(--color-line-strong),0_30px_60px_var(--drop)]"
        aria-hidden="true"
      >
        {name ? name.charAt(0).toLocaleUpperCase() : "·"}
      </div>
      <p class="mt-[22px] text-center text-[30px] leading-[1.1] font-[650] tracking-[-0.035em]">
        {name || "S.O.K Server"}
      </p>
      <p class="mt-1.5 text-center text-[14px] text-muted">
        {session.current?.auth === "none"
          ? t("web_login_off", "Turned off (SOK_AUTH=none)")
          : t("web_only_account", "Only account of this server")}
      </p>
      <div class="mt-[22px] grid self-stretch">
        <Line label={t("web_address", "Address")} value={location.host} />
        <Line label={t("web_data", "Data")} value={data.about.data} />
        <Line label={t("version", "Version")} value={data.about.version} />
      </div>
    {/if}
  {/snippet}
</Split>
