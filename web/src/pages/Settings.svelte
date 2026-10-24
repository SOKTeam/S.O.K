<script lang="ts">
  import { onMount } from "svelte";

  import ConfirmDialog from "../components/ConfirmDialog.svelte";
  import FolderList from "../components/FolderList.svelte";
  import KeyRow from "../components/KeyRow.svelte";
  import LinkProblems from "../components/LinkProblems.svelte";
  import NotifyRow from "../components/NotifyRow.svelte";
  import Section from "../components/Section.svelte";
  import Tabs from "../components/Tabs.svelte";
  import Toggle from "../components/Toggle.svelte";
  import { SERVICE_COLUMNS } from "../lib/columns";
  import { errorText } from "../lib/errors";
  import { parentFolder } from "../lib/format";
  import { loadTexts, t } from "../lib/i18n.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { navigate, router } from "../lib/router.svelte";
  import {
    loadSettings,
    saveSettings,
    settings,
    type FileMode,
    type LinkCheck,
  } from "../lib/settings.svelte";
  import { chooseTheme, theme, THEME_CHOICES, type ThemeChoice } from "../lib/theme.svelte";
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

  // The parts of the settings, each at its address: /settings/auto…
  const TABS = $derived([
    { value: "folders", label: t("web_folders", "Folders") },
    { value: "auto", label: t("web_automation", "Automation") },
    { value: "rename", label: t("web_renaming", "Renaming") },
    { value: "keys", label: t("api_keys", "API Keys") },
    { value: "look", label: t("appearance", "Appearance") },
  ]);
  const tab = $derived(
    TABS.find((item) => router.path === `/settings/${item.value}`)?.value ?? "folders",
  );

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

  function themeName(choice: ThemeChoice): string {
    switch (choice) {
      case "system":
        return t("web_theme_system", "System");
      case "light":
        return t("web_theme_light", "Light");
      case "orange":
        return t("web_theme_orange", "Orange");
      case "dark":
        return t("web_theme_dark", "Dark");
    }
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

<div class="mx-auto flex max-w-5xl flex-col pb-16">
  <h1 class="text-3xl font-bold">{t("settings", "Settings")}</h1>
  <div class="mt-5">
    <Tabs tabs={TABS} current={tab} onselect={(value) => navigate(`/settings/${value}`)} />
  </div>

  {#if error}
    <p
      class="sticky top-0 z-10 mt-4 rounded-lg border border-line bg-card px-4 py-2 text-sm text-error shadow-sm"
      role="alert"
    >
      {error}
    </p>
  {/if}

  {#if data}
    <div class="mt-7 flex flex-col gap-8">
      {#if tab === "folders"}
        <Section
          title={t("web_folders", "Folders")}
          text={t(
            "web_folders_text",
            "The paths as the server sees them: in Docker, the folders mounted in the container.",
          )}
        >
          <FolderList
            label={t("source_folders", "Source Folders")}
            icon="folder"
            paths={data.folders.sources}
            example="/data/downloads"
            error={folderErrors.sources}
            onchange={(paths) => saveFolders("sources", paths)}
          />
          {#each MEDIA_PAGES as page (page.path)}
            <FolderList
              label={t(page.key, page.english)}
              icon={page.icon}
              paths={data.folders[page.mediaType!]}
              example={`/data/${page.mediaType}`}
              near={data.folders.sources.length ? parentFolder(data.folders.sources[0]) : undefined}
              error={folderErrors[page.mediaType!]}
              onchange={(paths) => saveFolders(page.mediaType!, paths)}
            />
          {/each}
        </Section>

        <Section title={t("file_mode", "File mode")}>
          <div class="divide-y divide-line" role="radiogroup">
            {#each FILE_MODES as mode (mode)}
              {@const current = data.settings.file_mode === mode}
              <button
                type="button"
                role="radio"
                aria-checked={current}
                class="flex w-full items-start gap-3.5 px-4 py-3 text-left text-sm hover:bg-hover"
                onclick={() => saveAndCheck({ settings: { file_mode: mode } })}
              >
                <span
                  class={[
                    "relative mt-0.5 size-5 shrink-0 rounded-full border-2",
                    current ? "border-accent" : "border-faint",
                  ]}
                >
                  {#if current}
                    <span class="absolute inset-[3px] rounded-full bg-accent"></span>
                  {/if}
                </span>
                <span>
                  <span class="font-medium">{modeName(mode)}</span>
                  <span class="mt-0.5 block text-[13px] text-muted">{modeText(mode)}</span>
                  {#if mode === "link" && current && !problems.length && data.link_checks.length}
                    <span class="mt-0.5 block text-[13px] text-muted">
                      {t("web_links_ok", "Hard links work between your folders.")}
                    </span>
                  {/if}
                </span>
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
              <button type="button" class="link shrink-0" onclick={() => (showProblems = true)}>
                {t("web_see_details", "See the details")}
              </button>
            </div>
          {/if}
        </Section>
      {:else if tab === "auto"}
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
              text={data.settings.auto_sort
                ? t("web_notify_set", "On")
                : t("web_auto_sort_disabled", "Off")}
              checked={Boolean(data.settings.auto_sort)}
              onchange={(checked) => (checked ? (confirmAuto = true) : saveAuto(false))}
            />
            <label class="flex min-h-12 items-center justify-between gap-4 px-4 py-2.5 text-sm">
              <span class="font-medium">
                {t("web_auto_sort_minutes", "Check the folders every (minutes)")}
              </span>
              <input
                type="number"
                min="1"
                max="1440"
                class="field w-20 py-1.5 text-center"
                value={minutes ?? data.settings.auto_sort_minutes}
                oninput={(event) => (minutes = event.currentTarget.value)}
                onchange={saveMinutes}
              />
            </label>
          </div>
        </Section>

        <Section
          title={t("web_notifications", "Notifications")}
          text={t(
            "web_notifications_text",
            "After each rename, by hand or automatic, S.O.K Server can tell your other apps.",
          )}
        >
          {@const notify = data.notifications}
          <div class={[SERVICE_COLUMNS, "label border-b border-line py-2.5"]}>
            <span>{t("web_service", "Service")}</span>
            <span>{t("web_address", "Address")}</span>
            <span>{t("web_state", "Status")}</span>
            <span></span>
          </div>
          <NotifyRow
            target="discord"
            name="Discord"
            text={t(
              "web_notify_discord_text",
              "A message in a channel. Webhook address: settings of the channel → Integrations → Webhooks.",
            )}
            set={notify.discord.set}
            fields={[
              {
                key: "discord_url",
                secret: true,
                set: notify.discord.set,
                example: "https://discord.com/api/webhooks/…",
              },
            ]}
            onerror={(exc) => (error = errorText(exc))}
          />
          <NotifyRow
            target="jellyfin"
            name="Jellyfin"
            text={t(
              "web_notify_jellyfin_text",
              "Refreshes the libraries. API key: Dashboard → API Keys.",
            )}
            set={Boolean(notify.jellyfin.url) && notify.jellyfin.set}
            fields={[
              {
                key: "jellyfin_url",
                secret: false,
                value: notify.jellyfin.url,
                set: Boolean(notify.jellyfin.url),
                example: "http://jellyfin:8096",
              },
              {
                key: "jellyfin_key",
                secret: true,
                set: notify.jellyfin.set,
                example: t("your_api_key", "Your API key..."),
              },
            ]}
            onerror={(exc) => (error = errorText(exc))}
          />
          <NotifyRow
            target="plex"
            name="Plex"
            text={t("web_notify_plex_text", "Refreshes the libraries, with your Plex token.")}
            set={Boolean(notify.plex.url) && notify.plex.set}
            fields={[
              {
                key: "plex_url",
                secret: false,
                value: notify.plex.url,
                set: Boolean(notify.plex.url),
                example: "http://plex:32400",
              },
              {
                key: "plex_token",
                secret: true,
                set: notify.plex.set,
                example: "X-Plex-Token",
              },
            ]}
            onerror={(exc) => (error = errorText(exc))}
          />
          <NotifyRow
            target="webhook"
            name={t("web_notify_webhook", "Webhook")}
            text={t(
              "web_notify_webhook_text",
              "The rename as JSON, for Home Assistant, n8n and other tools.",
            )}
            set={notify.webhook.set}
            fields={[
              {
                key: "webhook_url",
                secret: true,
                set: notify.webhook.set,
                example: "https://…",
              },
            ]}
            onerror={(exc) => (error = errorText(exc))}
          />
          <NotifyRow
            target="script"
            name={t("web_notify_script", "Script")}
            text={notify.script
              ? t(
                  "web_notify_script_set",
                  "Set by the SOK_AFTER_RENAME variable: it runs after each rename, with the rename as JSON on its input.",
                )
              : t(
                  "web_notify_script_text",
                  "A command run after each rename, with the rename as JSON on its input. For safety, only the SOK_AFTER_RENAME variable of the container sets it.",
                )}
            set={notify.script}
            fields={[]}
            onerror={(exc) => (error = errorText(exc))}
          />
        </Section>
      {:else if tab === "rename"}
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
          <div
            class="label grid grid-cols-[11rem_minmax(0,1fr)] gap-x-4 border-b border-line px-4 py-2.5"
          >
            <span>{t("web_type", "Type")}</span>
            <span>{t("web_format", "Format")}</span>
          </div>
          <div class="divide-y divide-line">
            {#each FORMATS as [key, label, variables] (key)}
              <label
                class="grid grid-cols-[11rem_minmax(0,1fr)] items-center gap-x-4 px-4 py-3 text-sm"
              >
                <span class="font-medium">{label()}</span>
                <span class="flex min-w-0 flex-col gap-1">
                  <input
                    class="field py-1.5 font-mono text-xs"
                    value={formats[key] ?? data.settings[key]}
                    oninput={(event) => (formats[key] = event.currentTarget.value)}
                    onchange={() => saveFormat(key)}
                  />
                  <span class="font-mono text-xs text-muted">{variables}</span>
                </span>
              </label>
            {/each}
          </div>
        </Section>
      {:else if tab === "keys"}
        <Section
          title={t("api_keys", "API Keys")}
          text={t(
            "web_keys_text",
            "The free services work without a key. A key typed here is kept encrypted on the server, and never sent back.",
          )}
        >
          <div class={[SERVICE_COLUMNS, "label border-b border-line py-2.5"]}>
            <span>{t("web_service", "Service")}</span>
            <span>{t("web_key", "Key")}</span>
            <span>{t("web_state", "Status")}</span>
            <span></span>
          </div>
          {#each CATEGORIES as [mediaType, setting, label] (mediaType)}
            {@const keys = data.keys.filter((s) => s.media_type === mediaType)}
            <div
              class="flex items-center justify-between gap-4 border-b border-line px-4 pt-3.5 pb-2"
            >
              <span class="label">{label()}</span>
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
            {#each keys as service (service.service)}
              <KeyRow {service} onerror={(exc) => (error = errorText(exc))} />
            {/each}
          {/each}
        </Section>
      {:else}
        <Section title={t("appearance", "Appearance")}>
          <div class="divide-y divide-line">
            <div class="flex min-h-12 items-center justify-between gap-4 px-4 py-2.5 text-sm">
              <span>
                <span class="font-medium">{t("language", "Language")}</span>
                <span class="mt-0.5 block text-[13px] text-muted">
                  {t("web_language_text", "The interface and the names of the folders (“Season”).")}
                </span>
              </span>
              <select
                class="field w-auto py-1.5"
                value={data.settings.language}
                onchange={(event) => changeLanguage(event.currentTarget.value)}
              >
                {#each data.languages as code (code)}
                  <option value={code}>{languageName(code)}</option>
                {/each}
              </select>
            </div>
            <div class="flex min-h-12 items-center justify-between gap-4 px-4 py-2.5 text-sm">
              <span>
                <span class="font-medium">{t("web_theme", "Theme")}</span>
                <span class="mt-0.5 block text-[13px] text-muted">
                  {t(
                    "web_theme_text",
                    "In this browser. System: dark or light like the device; the light theme is white on a Mac, orange elsewhere.",
                  )}
                </span>
              </span>
              <div
                class="inline-flex shrink-0 rounded-full border border-line bg-input p-0.5"
                role="radiogroup"
                aria-label={t("web_theme", "Theme")}
              >
                {#each THEME_CHOICES as choice (choice)}
                  <button
                    type="button"
                    role="radio"
                    aria-checked={theme.choice === choice}
                    class={[
                      "rounded-full px-3 py-1 text-sm",
                      theme.choice === choice
                        ? "bg-accent font-semibold text-accent-fg"
                        : "text-muted hover:text-fg",
                    ]}
                    onclick={() => chooseTheme(choice)}
                  >
                    {themeName(choice)}
                  </button>
                {/each}
              </div>
            </div>
          </div>
        </Section>
      {/if}
    </div>
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
