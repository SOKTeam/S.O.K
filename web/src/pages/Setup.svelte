<script lang="ts">
  // The first launch assistant (/setup): one question at a time, the steps
  // in place of the navigation. 1 the account (only before it exists),
  // 2 where the downloads arrive, 3 where each type goes, 4 the file mode,
  // 5 the automatic sorting, then "Ready." and the first analysis. The
  // answers are words and sentences to fill in; the scene helps (the folder
  // browser, the preview of a name, the rhythm). Each answer is saved at
  // once; the app shows this page until a source and a destination are set.
  import { onMount, untrack } from "svelte";

  import Mark from "../components/layout/Mark.svelte";
  import SceneLight from "../components/layout/SceneLight.svelte";
  import Split from "../components/layout/Split.svelte";
  import FolderPicker from "../components/settings/FolderPicker.svelte";
  import NamePreview from "../components/settings/NamePreview.svelte";
  import SortDial from "../components/settings/SortDial.svelte";
  import Cube from "../components/nav/Cube.svelte";
  import { api } from "../lib/api";
  import { errorText, linkProblemText } from "../lib/errors";
  import { commonFolder, fillParts, parentFolder } from "../lib/format";
  import { i18n, t } from "../lib/i18n.svelte";
  import { setLight } from "../lib/light.svelte";
  import { screen } from "../lib/screen.svelte";
  import { MEDIA_PAGES } from "../lib/pages";
  import { startScan } from "../lib/scan.svelte";
  import { refreshSession, session } from "../lib/session.svelte";
  import {
    loadSettings,
    saveSettings,
    settings,
    type FileMode,
    type SettingsChange,
  } from "../lib/settings.svelte";

  let { step = $bindable(), onDone }: { step: number; onDone: () => void } = $props();

  let error = $state("");
  let busy = $state(false);
  // Step 1: the account.
  let username = $state("");
  let password = $state("");
  let again = $state("");
  // Step 3: the type whose folder the browser picks.
  let target = $state("movies");

  const data = $derived(settings.data);

  onMount(() => {
    if (session.current?.logged_in) loadSettings().catch((exc) => (error = errorText(exc)));
    return () => setLight(null);
  });

  // The first type without a folder, when step 3 opens.
  $effect(() => {
    if (step === 3 && data) {
      untrack(() => {
        target =
          MEDIA_PAGES.find((page) => !data.folders[page.mediaType!].length)?.mediaType ?? "movies";
      });
    }
  });

  $effect(() => {
    if (step === 1) setLight("251, 96, 72");
    else if (step === 4) setLight("150, 170, 80");
    else if (step === 5 && data?.settings.auto_sort) setLight("251, 96, 72");
    else setLight(null);
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

  function go(to: number) {
    error = "";
    step = to;
  }

  // ------------------------------------------------------------ Steps

  const STEPS = $derived([
    t("web_setup_step_account", "Account"),
    t("web_setup_step_downloads", "Downloads"),
    t("web_setup_step_library", "Library"),
    t("file_mode", "File mode"),
    t("web_auto_sort", "Automatic sorting"),
  ]);

  // A step done can be opened again, but not the account.
  const canOpen = (index: number) => index + 1 < step && index > 0;

  async function createAccount(event: SubmitEvent) {
    event.preventDefault();
    if (password !== again) {
      error = t("web_error_password_mismatch", "The two passwords are not the same.");
      return;
    }
    busy = true;
    error = "";
    try {
      // The language of the page, the browser's, becomes the one of the settings.
      await api("/api/setup", {
        method: "POST",
        body: { username, password, language: i18n.language },
      });
      await refreshSession();
      await loadSettings();
      go(2);
    } catch (exc) {
      error = errorText(exc);
    } finally {
      busy = false;
    }
  }

  // ------------------------------------------------------------ Folders

  const sources = $derived(data?.folders.sources ?? []);
  const destinations = $derived(
    MEDIA_PAGES.flatMap((page) => data?.folders[page.mediaType!] ?? []),
  );

  /** Where the browser opens: next to the folders already chosen. */
  const start = $derived.by(() => {
    if (step === 2) return sources.length ? parentFolder(sources[sources.length - 1]) : undefined;
    const known = data?.folders[target]?.[0] ?? destinations[0];
    return known ? parentFolder(known) : sources[0] ? parentFolder(sources[0]) : undefined;
  });

  // Under 1000px, the folder browser is a sheet opened by a path.
  let browsing = $state(false);
  function browse(type?: string) {
    if (type) target = type;
    browsing = true;
  }

  function pick(path: string) {
    browsing = false;
    if (!data) return;
    if (step === 2) {
      if (!sources.includes(path)) save({ folders: { sources: [...sources, path] } });
      return;
    }
    // The chosen folder becomes the first (default) one of the type.
    const rest = data.folders[target].slice(1).filter((p) => p !== path);
    save({ folders: { [target]: [path, ...rest] } }).then((saved) => {
      if (!saved) return;
      const next = MEDIA_PAGES.find((page) => !data.folders[page.mediaType!].length);
      if (next) target = next.mediaType!;
    });
  }

  const pageName = (type: string) => {
    const page = MEDIA_PAGES.find((p) => p.mediaType === type)!;
    return t(page.key, page.english);
  };

  // The words of the rows of step 3, for the grammar of each language.
  const ROW: Record<string, () => [string, string, string]> = {
    movies: () => [
      t("web_setup_movies", "Movies"),
      t("web_setup_go_movies", "go to"),
      t("web_setup_stay_movies", "stay where they are"),
    ],
    tv: () => [
      t("web_setup_tv", "TV shows"),
      t("web_setup_go_tv", "go to"),
      t("web_setup_stay_tv", "stay where they are"),
    ],
    music: () => [
      t("web_setup_music", "Music"),
      t("web_setup_go_music", "goes to"),
      t("web_setup_stay_music", "stays where it is"),
    ],
    books: () => [
      t("web_setup_books", "Books"),
      t("web_setup_go_books", "go to"),
      t("web_setup_stay_books", "stay where they are"),
    ],
    games: () => [
      t("web_setup_games", "Games"),
      t("web_setup_go_games", "go to"),
      t("web_setup_stay_games", "stay where they are"),
    ],
  };

  // ------------------------------------------------------------ Mode and sorting

  const mode = $derived((data?.settings.file_mode ?? "link") as FileMode);
  const minutes = $derived(Number(data?.settings.auto_sort_minutes ?? 15));
  const problems = $derived(
    mode === "link" ? (data?.link_checks ?? []).filter((check) => !check.ok) : [],
  );

  const MODES: FileMode[] = ["link", "copy", "move"];
  const modeName = (value: FileMode) =>
    ({
      link: t("file_mode_link", "Hard link"),
      copy: t("file_mode_copy", "Copy"),
      move: t("file_mode_move", "Move"),
    })[value];
  const modeText = (value: FileMode) =>
    ({
      link: t(
        "web_setup_link_text",
        "The original stays in the downloads: torrents keep seeding, without using more space.",
      ),
      copy: t(
        "web_setup_copy_text",
        "The original stays, and a copy is put away: the space is taken twice.",
      ),
      move: t("web_setup_move_text", "The file leaves the downloads: its torrent stops seeding."),
    })[value];

  // ------------------------------------------------------------ Ready

  const summary = $derived.by(() => {
    const how = {
      link: t("web_setup_as_link", "as hard links"),
      copy: t("web_setup_as_copy", "as copies"),
      move: t("web_setup_as_move", "moved"),
    }[mode];
    const to = commonFolder(destinations);
    return fillParts(
      t("web_setup_summary", "The files of {from} will go to {to}, {how}.", { how }),
      { from: sources.join(", "), to: to === "/" ? destinations.join(", ") : to },
    );
  });

  async function finish() {
    busy = true;
    try {
      await startScan();
    } catch (exc) {
      // The analysis can be started again from the home page.
      console.warn(errorText(exc));
    } finally {
      busy = false;
    }
    onDone();
  }
</script>

{#snippet path(text: string, current: boolean, onclick: () => void)}
  <button
    type="button"
    class={[
      "cursor-pointer bg-[length:6px_1.5px] bg-bottom bg-repeat-x pb-0.5 text-left font-mono tracking-[-0.02em]",
      current
        ? "bg-[linear-gradient(90deg,var(--color-accent)_50%,transparent_0)] text-accent-text"
        : "bg-[linear-gradient(90deg,var(--color-line-strong)_50%,transparent_0)] text-ink hover:text-accent-text",
    ]}
    {onclick}>{text}</button
  >
{/snippet}

{#snippet keys(label: string, ok: boolean, onclick: () => void, back: boolean)}
  <div class="mt-10 flex items-center gap-[22px]">
    <button type="button" class="key key-primary h-[46px] px-5" disabled={!ok || busy} {onclick}>
      {label}<span class="legend">→</span>
    </button>
    {#if back}
      <button
        type="button"
        class="cursor-pointer text-[14px] font-semibold text-faint hover:text-ink"
        onclick={() => go(step - 1)}
      >
        {t("web_back", "Back")}
      </button>
    {/if}
  </div>
{/snippet}

{#snippet question(text: string, end: string)}
  <h1 class="m-0 text-[56px] leading-[1.04] font-[650] tracking-[-0.045em]">
    {text}<span class="text-muted">{end}</span>
  </h1>
{/snippet}

{#snippet lead(text: string)}
  <p class="mt-[22px] max-w-[560px] text-[16px] leading-[1.5] text-muted">{text}</p>
{/snippet}

{#snippet field(
  label: string,
  type: string,
  value: string,
  set: (v: string) => void,
  auto: "username" | "new-password",
  hint?: string,
)}
  <label
    class="grid gap-1.5 pb-2.5 shadow-[inset_0_-1px_0_var(--color-line-strong)] focus-within:shadow-[inset_0_-2px_0_var(--color-accent)]"
  >
    <span class="text-[13px] text-faint">{label}</span>
    <input
      class="bg-transparent text-[24px] font-medium tracking-[-0.02em] text-ink outline-none"
      {type}
      {value}
      oninput={(event) => set(event.currentTarget.value)}
      autocomplete={auto}
      required
      minlength={type === "password" ? 8 : undefined}
    />
    {#if hint}<small class="text-[12.5px] text-faint">{hint}</small>{/if}
  </label>
{/snippet}

<SceneLight strength={0.5} />
<div class="relative mx-auto flex h-full max-w-[1760px] flex-col">
  <nav
    class="flex h-[76px] shrink-0 items-center overflow-x-auto px-9 max-[999px]:px-8 max-[699px]:h-[52px] max-[699px]:[mask-image:linear-gradient(90deg,#000_80%,transparent)] max-[699px]:px-5"
    aria-label={t("web_setup_steps", "Steps")}
  >
    <Mark />
    {#each STEPS as name, index (index)}
      {@const done = index + 1 < step}
      {@const on = index + 1 === step}
      <button
        type="button"
        disabled={!canOpen(index)}
        aria-current={on ? "step" : undefined}
        class={[
          "mr-6 shrink-0 text-[22px] leading-[30px] font-semibold tracking-[-0.035em] whitespace-nowrap max-[699px]:mr-4 max-[699px]:text-[18px]",
          on ? "text-ink" : done ? "text-muted" : "text-faint",
          canOpen(index) ? "cursor-pointer hover:text-ink" : "cursor-default",
        ]}
        onclick={() => go(index + 1)}
      >
        {name}<sup
          class={[
            "ml-[3px] align-[12px] font-mono text-[11px] font-medium tracking-normal",
            done ? "text-accent-text" : on ? "text-ink" : "text-faint",
          ]}>{done ? "✓" : `0${index + 1}`}</sup
        >
      </button>
    {/each}
  </nav>
  <main class="min-h-0 flex-1">
    <Split open={browsing && (step === 2 || step === 3)} onclose={() => (browsing = false)} sheet>
      <div class="my-auto w-full max-w-[760px] py-8 pb-12 lg:ml-[84px]">
        {#if step === 1}
          {@render question(t("web_setup_title", "Welcome"), ".")}
          {@render lead(
            t(
              "web_setup_account_text",
              "Create the account that protects this server. It is the only one, to come in from any device.",
            ),
          )}
          <form class="mt-[30px] grid max-w-[460px] gap-[22px]" onsubmit={createAccount}>
            {@render field(
              t("web_setup_name", "Name"),
              "text",
              username,
              (v) => (username = v),
              "username",
            )}
            {@render field(
              t("web_password", "Password"),
              "password",
              password,
              (v) => (password = v),
              "new-password",
              t("web_setup_password_hint", "8 characters or more"),
            )}
            {@render field(
              t("web_setup_again", "Once again"),
              "password",
              again,
              (v) => (again = v),
              "new-password",
            )}
            {#if error}<p class="text-[13.5px] text-caution" role="alert">{error}</p>{/if}
            <div class="mt-[18px]">
              <button
                class="key key-primary h-[46px] px-5"
                disabled={busy || !username.trim() || password.length < 8 || !again}
              >
                {t("web_create_account", "Create the account")}<span class="legend">→</span>
              </button>
            </div>
          </form>
        {:else if !data}
          {#if error}<p class="text-[14px] text-danger" role="alert">{error}</p>{/if}
        {:else if step === 2}
          {@render question(t("web_setup_downloads_q", "Your files arrive in"), "…")}
          <div class="mt-[22px] grid gap-2.5 text-[30px] leading-[1.3]">
            {#each sources as source (source)}
              <div class="flex items-baseline gap-[18px]">
                <span class="font-mono tracking-[-0.02em] text-ink">{source}</span>
                <button
                  type="button"
                  class="cursor-pointer text-[13px] text-faint hover:text-ink"
                  onclick={() =>
                    save({ folders: { sources: sources.filter((p) => p !== source) } })}
                >
                  {t("web_setup_remove", "remove")}
                </button>
              </div>
            {/each}
            <div>
              {@render path(
                sources.length
                  ? t("web_setup_other_folder", "+ another folder")
                  : t("web_setup_pick_folder", "pick a folder"),
                true,
                () => browse(),
              )}
            </div>
          </div>
          {@render lead(
            t(
              "web_setup_downloads_text",
              "Where your torrent or Usenet client puts what it downloads. In Docker, the folders mounted in the container.",
            ),
          )}
          {#if error}<p class="mt-3 text-[13.5px] text-caution" role="alert">{error}</p>{/if}
          {@render keys(t("web_continue", "Continue"), sources.length > 0, () => go(3), false)}
        {:else if step === 3}
          {@render question(
            t("web_setup_library_q", "And where do they go"),
            t("web_question_end", "?"),
          )}
          <div class="mt-[26px] grid gap-1.5">
            {#each MEDIA_PAGES as page (page.path)}
              {@const type = page.mediaType!}
              {@const [name, verb, stay] = ROW[type]()}
              {@const folder = data.folders[type][0]}
              <div
                class="grid grid-cols-[150px_auto] items-baseline gap-x-4 text-[22px] font-semibold tracking-[-0.02em] sm:grid-cols-[170px_96px_auto]"
              >
                <span>{name}</span>
                {#if folder}
                  <span class="hidden text-[15px] font-normal tracking-normal text-faint sm:inline"
                    >{verb}</span
                  >
                  <span class="min-w-0 truncate text-[22px] font-normal">
                    {@render path(folder, target === type, () => browse(type))}
                  </span>
                {:else}
                  <button
                    type="button"
                    class={[
                      "col-span-1 cursor-pointer text-left text-[15px] font-normal tracking-normal sm:col-span-2",
                      target === type ? "text-accent-text" : "text-faint hover:text-muted",
                    ]}
                    onclick={() => browse(type)}
                  >
                    {stay}
                  </button>
                {/if}
              </div>
            {/each}
          </div>
          {@render lead(
            t(
              "web_setup_library_text",
              "Click a folder to change it. What you do not have can stay without a folder.",
            ),
          )}
          {#if error}<p class="mt-3 text-[13.5px] text-caution" role="alert">{error}</p>{/if}
          {@render keys(
            t("web_continue", "Continue"),
            destinations.length > 0,
            () => go(4),
            sources.length > 0,
          )}
        {:else if step === 4}
          {@render question(t("web_setup_mode_q", "And the original"), t("web_question_end", "?"))}
          <div
            class="mt-[26px] flex flex-wrap gap-x-9 gap-y-4 text-[40px] leading-[1.1] font-semibold tracking-[-0.035em]"
            role="radiogroup"
          >
            {#each MODES as value (value)}
              <button
                type="button"
                role="radio"
                aria-checked={mode === value}
                class={[
                  "relative cursor-pointer",
                  mode === value
                    ? "text-ink after:absolute after:inset-x-0 after:-bottom-2.5 after:h-[3px] after:rounded-sm after:bg-accent"
                    : "text-faint hover:text-muted",
                ]}
                onclick={() => mode !== value && save({ settings: { file_mode: value } })}
              >
                {modeName(value)}
              </button>
            {/each}
          </div>
          <p class="mt-[30px] max-w-[560px] text-[16px] leading-[1.5] text-muted">
            {modeText(mode)}
            {#if mode === "link"}
              <br />
              {#if problems.length}
                {#each problems as problem (problem.source + problem.destination)}
                  <span class="text-caution"
                    >{linkProblemText(
                      problem.problem ?? "",
                      problem.source,
                      problem.destination,
                    )}</span
                  ><br />
                {/each}
              {:else}
                <span class="text-ink"
                  ><span class="text-accent-text">✓</span>
                  {t("web_links_ok", "Hard links work between your folders.")}</span
                >
              {/if}
            {/if}
          </p>
          {@render keys(t("web_continue", "Continue"), true, () => go(5), true)}
        {:else if step === 5}
          {@render question(t("web_setup_auto_q", "Sort on its own"), t("web_question_end", "?"))}
          <div
            class="mt-[26px] flex flex-wrap gap-x-9 gap-y-4 text-[40px] leading-[1.1] font-semibold tracking-[-0.035em]"
            role="radiogroup"
          >
            {#each [false, true] as on (on)}
              {@const chosen = Boolean(data.settings.auto_sort) === on}
              <button
                type="button"
                role="radio"
                aria-checked={chosen}
                class={[
                  "relative cursor-pointer",
                  chosen
                    ? "text-ink after:absolute after:inset-x-0 after:-bottom-2.5 after:h-[3px] after:rounded-sm after:bg-accent"
                    : "text-faint hover:text-muted",
                ]}
                onclick={() => !chosen && save({ settings: { auto_sort: on } })}
              >
                {on
                  ? t("web_setup_every", "Every {n} min", { n: minutes })
                  : t("web_setup_no", "No")}
              </button>
            {/each}
          </div>
          <p class="mt-[30px] max-w-[560px] text-[16px] leading-[1.5] text-muted">
            {data.settings.auto_sort
              ? t(
                  "web_setup_auto_on",
                  "The server looks at your downloads and sorts what it recognizes. Each sorting can be undone from the History.",
                )
              : t(
                  "web_setup_auto_off",
                  "You start the analysis and sort yourself. You can turn it on later in the Settings.",
                )}
          </p>
          {@render keys(t("web_continue", "Continue"), true, () => go(6), true)}
        {:else}
          {@render question(t("web_setup_ready", "Ready"), ".")}
          <p
            class="mt-[26px] max-w-[680px] text-[26px] leading-[1.5] font-medium tracking-[-0.02em]"
          >
            {#each summary as part, i (i)}{#if part.value}<span
                  class="font-mono text-[23px] font-normal">{part.text}</span
                >{:else}{part.text}{/if}{/each}
            {data.settings.auto_sort
              ? t("web_setup_ready_auto", "The automatic sorting looks every {n} minutes.", {
                  n: minutes,
                })
              : t("web_setup_ready_hand", "You sort by hand.")}
          </p>
          {@render lead(
            t(
              "web_setup_ready_text",
              "Everything can be changed in the Settings, with the notifications and the keys of the services too.",
            ),
          )}
          {@render keys(
            t("web_setup_first_analysis", "Start the first analysis"),
            true,
            finish,
            true,
          )}
        {/if}
      </div>

      {#snippet scene()}
        {#if data && (step === 2 || step === 3)}
          {#key `${step}-${target}`}
            <FolderPicker
              title={t("web_folder_for", "A folder for {role}", {
                role: step === 2 ? t("web_setup_step_downloads", "Downloads") : pageName(target),
              })}
              {start}
              onpick={pick}
              oncancel={screen.narrow ? () => (browsing = false) : undefined}
            />
          {/key}
        {:else if data && step === 4}
          <NamePreview
            label={t("web_preview", "Preview")}
            type="movies"
            model={String(data.settings.movie_format)}
            destination={data.folders.movies[0] ?? ""}
            source={sources[0] ?? ""}
            {mode}
          />
        {:else if data && step === 5}
          <p class="label mb-[26px] self-stretch">{t("web_preview", "Preview")}</p>
          <SortDial
            enabled={Boolean(data.settings.auto_sort)}
            {minutes}
            lastCheck={null}
            now={new Date()}
          />
        {:else if data && step === 6}
          <div class="relative mt-[110px] h-[200px] w-[270px]" aria-hidden="true">
            {#each [0, 1, 2] as i (i)}
              <div
                class="absolute top-3.5 h-[165px] w-[110px] rounded-xl bg-linear-135 from-key to-surface shadow-[inset_0_0_0_1px_var(--color-line),0_20px_40px_rgb(0_0_0/0.3)]"
                style:left={`${i * 80}px`}
                style:transform={`rotate(${(i - 1) * 8}deg) translateY(${i === 1 ? 0 : 14}px)`}
                style:z-index={i === 1 ? 3 : 1}
              ></div>
            {/each}
          </div>
          <p class="mt-[22px] max-w-[360px] text-center text-[14px] leading-[1.5] text-muted">
            {#each fillParts( t("web_setup_ready_scene", "The first analysis will fill these places with what it finds in {folder}."), { folder: sources[0] ?? "" } ) as part, i (i)}{#if part.value}<code
                  class="font-mono text-[13px] text-ink">{part.text}</code
                >{:else}{part.text}{/if}{/each}
          </p>
        {:else}
          <div class="my-auto flex flex-col items-center pb-10 text-ink" aria-hidden="true">
            <div class="drop-shadow-[0_30px_40px_var(--drop)]"><Cube size={170} /></div>
            <div
              class="mt-[26px] h-[22px] w-[230px] rounded-[50%] bg-[radial-gradient(closest-side,var(--drop),transparent)]"
            ></div>
            <p class="label mt-[34px]">S.O.K Server</p>
          </div>
        {/if}
      {/snippet}
    </Split>
  </main>
</div>
