<script lang="ts">
  import { onMount } from "svelte";

  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import FolderList from "../components/FolderList.svelte";
  import KeyRow from "../components/KeyRow.svelte";
  import LinkProblems from "../components/LinkProblems.svelte";
  import Section from "../components/Section.svelte";
  import Toggle from "../components/Toggle.svelte";
  import { errorText } from "../lib/errors";
  import { parentFolder } from "../lib/format";
  import { loadTexts, t } from "../lib/i18n.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import {
    loadSettings,
    saveSettings,
    settings,
    type FileMode,
    type LinkCheck,
  } from "../lib/settings.svelte";
  import { loadWatch } from "../lib/watch.svelte";

  let error = $state("");
  let folderErrors = $state<Record<string, string>>({});
  // The formats being typed, saved when the field is left.
  let formats = $state<Record<string, string>>({});

  onMount(async () => {
    try {
      await loadSettings();
    } catch (exc) {
      error = errorText(exc);
    }
  });

  const data = $derived(settings.data);

  async function save(change: Parameters<typeof saveSettings>[0]): Promise<boolean> {
    error = "";
    try {
      await saveSettings(change);
      return true;
    } catch (exc) {
      error = errorText(exc);
      return false;
    }
  }

  async function saveFolders(role: string, paths: string[]): Promise<boolean> {
    folderErrors[role] = "";
    const before = new Set(problems.map(key));
    try {
      await saveSettings({ folders: { [role]: paths } });
    } catch (exc) {
      folderErrors[role] = errorText(exc);
      return false;
    }
    if (problems.some((check) => !before.has(key(check)))) {
      showProblems = true;
    }
    return true;
  }

  async function changeLanguage(language: string) {
    if (await save({ settings: { language } })) {
      await loadTexts(language);
    }
  }

  async function saveFormat(key: string) {
    const value = formats[key];
    if (value !== undefined && value !== data?.settings[key]) {
      // A refused format (empty) gives the field back its saved value.
      await save({ settings: { [key]: value } });
      delete formats[key];
    }
  }

  // Turning the automatic sorting on asks first: it renames on its own.
  let confirmAuto = $state(false);
  // The minutes being typed, saved when the field is left.
  let minutes = $state<string | null>(null);

  async function saveAuto(on: boolean) {
    if (await save({ settings: { auto_sort: on } })) {
      loadWatch().catch(() => {});
    }
  }

  async function saveMinutes() {
    const value = Number(minutes);
    if (minutes !== null && Number.isInteger(value) && value !== data?.settings.auto_sort_minutes) {
      if (await save({ settings: { auto_sort_minutes: value } })) {
        loadWatch().catch(() => {});
      }
    }
    // A refused value gives the field back its saved one.
    minutes = null;
  }

  /** The name of a language in that language: "fr" → "Français". */
  function languageName(code: string): string {
    const name = new Intl.DisplayNames([code], { type: "language" }).of(code) ?? code;
    return name.charAt(0).toLocaleUpperCase(code) + name.slice(1);
  }

  // The hard links that cannot be made: a change that adds one opens the
  // window that explains it.
  let showProblems = $state(false);
  const problems = $derived(
    data?.settings.file_mode === "link" ? data.link_checks.filter((check) => !check.ok) : [],
  );

  function key(check: LinkCheck): string {
    return `${check.source}|${check.destination}|${check.problem}`;
  }

  /** Save a change, then open the window if it brought a new problem. */
  async function saveAndCheck(change: Parameters<typeof saveSettings>[0]): Promise<boolean> {
    const before = new Set(problems.map(key));
    const saved = await save(change);
    if (saved && problems.some((check) => !before.has(key(check)))) {
      showProblems = true;
    }
    return saved;
  }

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

  const BEHAVIOR = [
    ["create_folders", () => t("create_missing_folders", "Create missing folders")],
    ["skip_duplicates", () => t("skip_duplicates", "Skip duplicates")],
    ["backup_before_rename", () => t("backup_before_rename", "Backup before rename")],
    ["subtitles_follow_video", () => t("subtitles_follow_video", "Move subtitles with videos")],
    ["download_posters", () => t("download_posters", "Download posters")],
  ] as const;

  const FORMATS = [
    ["movie_format", () => t("movies", "Movies"), "{title}, {year}, {quality}"],
    [
      "video_format",
      () => t("tv_series", "TV Series"),
      "{title}, {season}, {episode}, {episode_title}",
    ],
    ["music_format", () => t("music", "Music"), "{artist}, {album}, {track}, {title}, {year}"],
    [
      "book_format",
      () => t("books", "Books"),
      "{author}, {title}, {year}, {series}, {series_number}",
    ],
    ["game_format", () => t("games", "Games"), "{title}, {year}, {platform}, {tags}"],
  ] as const;

  const CATEGORIES = [
    ["video", "preferred_api_video", () => t("category_video", "Video (Movies & TV)")],
    ["music", "preferred_api_music", () => t("category_music", "Music")],
    ["books", "preferred_api_books", () => t("category_books", "Books")],
    ["games", "preferred_api_games", () => t("category_games", "Video Games")],
    ["images", null, () => t("web_category_images", "Images")],
  ] as const;
</script>

<div class="mx-auto flex max-w-3xl flex-col gap-8 pb-16">
  <h1 class="text-2xl font-bold">{t("settings", "Settings")}</h1>

  {#if error}
    <p
      class="sticky top-0 z-10 rounded-lg border border-error/30 bg-bg px-4 py-2 text-sm text-error shadow-sm"
      role="alert"
    >
      {error}
    </p>
  {/if}

  {#if data}
    <Section
      title={t("web_folders", "Folders")}
      text={t(
        "web_folders_text",
        "The paths as the server sees them: in Docker, the folders mounted in the container.",
      )}
    >
      <div class="divide-y divide-line">
        <FolderList
          label={t("source_folders", "Source Folders")}
          paths={data.folders.sources}
          example="/data/downloads"
          error={folderErrors.sources}
          onchange={(paths) => saveFolders("sources", paths)}
        />
        {#each MEDIA_PAGES as page (page.path)}
          <FolderList
            label={t(page.key, page.english)}
            paths={data.folders[page.mediaType!]}
            example={`/data/${page.mediaType}`}
            near={data.folders.sources.length ? parentFolder(data.folders.sources[0]) : undefined}
            error={folderErrors[page.mediaType!]}
            onchange={(paths) => saveFolders(page.mediaType!, paths)}
          />
        {/each}
      </div>
    </Section>

    <Section title={t("file_mode", "File mode")}>
      <div class="grid gap-2 p-3 sm:grid-cols-3" role="radiogroup">
        {#each FILE_MODES as mode (mode)}
          {@const current = data.settings.file_mode === mode}
          <button
            type="button"
            role="radio"
            aria-checked={current}
            class={[
              "flex flex-col gap-1 rounded-lg border p-3 text-left",
              current ? "border-accent bg-accent/10" : "border-line hover:bg-hover",
            ]}
            onclick={() => saveAndCheck({ settings: { file_mode: mode } })}
          >
            <span class="text-sm font-semibold">{modeName(mode)}</span>
            <span class="text-xs text-muted">{modeText(mode)}</span>
          </button>
        {/each}
      </div>
      {#if problems.length}
        <div
          class="flex items-center justify-between gap-4 border-t border-line px-4 py-3 text-sm text-error"
          role="alert"
        >
          <span>
            {t("web_link_problems", "Hard links will not work between some of your folders.")}
          </span>
          <button
            type="button"
            class="shrink-0 font-semibold underline"
            onclick={() => (showProblems = true)}
          >
            {t("web_see_details", "See the details")}
          </button>
        </div>
      {/if}
    </Section>

    <Section
      title={t("web_auto_sort", "Automatic sorting")}
      text={t(
        "web_auto_sort_text",
        "The server looks at the source folders on its own. Once downloaded, the new files are analyzed and the Ready ones renamed; the others wait in the tabs.",
      )}
    >
      <div class="divide-y divide-line">
        <Toggle
          label={t("web_auto_sort_switch", "Sort the new files automatically")}
          checked={Boolean(data.settings.auto_sort)}
          onchange={(checked) => (checked ? (confirmAuto = true) : saveAuto(false))}
        />
        <label class="flex items-center justify-between gap-4 px-4 py-3 text-sm">
          <span>{t("web_auto_sort_minutes", "Check the folders every (minutes)")}</span>
          <input
            type="number"
            min="1"
            max="1440"
            class="field w-24"
            value={minutes ?? data.settings.auto_sort_minutes}
            oninput={(event) => (minutes = event.currentTarget.value)}
            onchange={saveMinutes}
          />
        </label>
      </div>
    </Section>

    <Section title={t("behavior", "Behavior")}>
      <div class="divide-y divide-line">
        {#each BEHAVIOR as [key, label] (key)}
          <Toggle
            label={label()}
            checked={Boolean(data.settings[key])}
            onchange={(checked) => save({ settings: { [key]: checked } })}
          />
        {/each}
      </div>
    </Section>

    <Section title={t("file_formats", "Output Formats")}>
      <div class="divide-y divide-line">
        {#each FORMATS as [key, label, variables] (key)}
          <label class="flex flex-col gap-1.5 px-4 py-3 text-sm">
            <span class="font-semibold">{label()}</span>
            <input
              class="field font-mono text-xs"
              value={formats[key] ?? data.settings[key]}
              oninput={(event) => (formats[key] = event.currentTarget.value)}
              onchange={() => saveFormat(key)}
            />
            <span class="font-mono text-xs text-muted">{variables}</span>
          </label>
        {/each}
      </div>
    </Section>

    <Section
      title={t("api_keys", "API Keys")}
      text={t(
        "web_keys_text",
        "The free services work without a key. A key typed here is kept encrypted on the server, and never sent back.",
      )}
    >
      <div class="divide-y divide-line">
        {#each CATEGORIES as [mediaType, setting, label] (mediaType)}
          <div class="flex flex-col">
            <div class="flex items-center justify-between gap-4 bg-bg/50 px-4 py-2.5">
              <span class="text-sm font-semibold">{label()}</span>
              {#if setting && data.services[mediaType]}
                <label class="flex items-center gap-2 text-xs text-muted">
                  {t("preferred_api", "Preferred API")}
                  <select
                    class="field w-auto py-1 text-xs"
                    value={data.settings[setting]}
                    onchange={(event) =>
                      save({ settings: { [setting]: event.currentTarget.value } })}
                  >
                    {#each data.services[mediaType] as service (service.id)}
                      <option value={service.id}>{service.name}</option>
                    {/each}
                  </select>
                </label>
              {/if}
            </div>
            <div class="divide-y divide-line">
              {#each data.keys.filter((s) => s.media_type === mediaType) as service (service.service)}
                <KeyRow {service} onerror={(exc) => (error = errorText(exc))} />
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </Section>

    <Section title={t("language", "Language")}>
      <div class="flex items-center justify-between gap-4 px-4 py-3 text-sm">
        <span class="text-muted">
          {t("web_language_text", "The interface and the names of the folders (“Season”).")}
        </span>
        <select
          class="field w-auto"
          value={data.settings.language}
          onchange={(event) => changeLanguage(event.currentTarget.value)}
        >
          {#each data.languages as code (code)}
            <option value={code}>{languageName(code)}</option>
          {/each}
        </select>
      </div>
    </Section>
  {/if}
</div>

<ConfirmDialog
  bind:open={confirmAuto}
  text={t("web_auto_sort_confirm", "Turn on the automatic sorting?")}
  detail={t(
    "web_auto_sort_confirm_detail",
    "Every Ready row will be renamed on its own, those already in the tabs too, with the file mode “{mode}”. The history can undo it.",
    { mode: data ? modeName(data.settings.file_mode as FileMode) : "" },
  )}
  action={t("web_turn_on", "Turn on")}
  onconfirm={() => saveAuto(true)}
/>

<LinkProblems
  bind:open={showProblems}
  {problems}
  oncopy={() => save({ settings: { file_mode: "copy" } })}
/>
