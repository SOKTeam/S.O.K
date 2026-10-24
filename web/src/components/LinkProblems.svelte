<script lang="ts">
  import { linkFixText, linkProblemText } from "../lib/errors";
  import { t } from "../lib/i18n.svelte";
  import type { LinkCheck } from "../lib/settings.svelte";

  // The hard links that cannot be made between the folders of the settings:
  // for each one, the problem, why, and what to change.
  let {
    open = $bindable(false),
    problems,
    oncopy,
  }: {
    open?: boolean;
    problems: LinkCheck[];
    /** Use the Copy mode instead. */
    oncopy: () => void;
  } = $props();

  let dialog = $state<HTMLDialogElement>();

  $effect(() => {
    if (open && !dialog?.open) dialog?.showModal();
    if (!open && dialog?.open) dialog?.close();
  });
</script>

<dialog
  bind:this={dialog}
  onclose={() => (open = false)}
  class="m-auto max-h-[80vh] w-full max-w-lg flex-col rounded-2xl border border-line bg-card p-0 text-fg shadow-xl backdrop:bg-black/40 open:flex"
>
  <div class="border-b border-line px-6 py-4">
    <p class="font-semibold">{t("web_link_problem_title", "Hard links will not work")}</p>
    <p class="mt-1 text-sm text-muted">
      {t(
        "web_link_problem_text",
        "Files cannot be renamed with a hard link between these folders: the rename would stop before moving anything.",
      )}
    </p>
  </div>
  <ul class="min-h-0 flex-1 divide-y divide-line overflow-y-auto">
    {#each problems as problem (problem.source + problem.destination)}
      <li class="flex flex-col gap-2 px-6 py-4 text-sm">
        <p class="font-mono text-xs">
          {problem.source} <span class="text-faint">→</span>
          {problem.destination}
        </p>
        <p class="text-error">
          {linkProblemText(problem.problem ?? "", problem.source, problem.destination)}
        </p>
        <p>
          <span class="font-semibold">{t("web_link_fix", "To fix it:")}</span>
          {linkFixText(problem.problem ?? "")}
        </p>
      </li>
    {/each}
  </ul>
  <div class="flex justify-end gap-2 border-t border-line px-6 py-3">
    <button
      type="button"
      class="button-outline"
      onclick={() => {
        open = false;
        oncopy();
      }}
    >
      {t("web_link_use_copy", "Use Copy instead")}
    </button>
    <button type="button" class="button" onclick={() => (open = false)}>
      {t("web_understood", "Got it")}
    </button>
  </div>
</dialog>
