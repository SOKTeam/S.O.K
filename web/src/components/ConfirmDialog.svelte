<script lang="ts">
  import { t } from "../lib/i18n.svelte";

  // A question before an action: the action runs on "yes".
  let {
    open = $bindable(false),
    text,
    detail = "",
    action,
    onconfirm,
  }: {
    open?: boolean;
    text: string;
    detail?: string;
    /** The text of the button that confirms. */
    action: string;
    onconfirm: () => void;
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
  class="m-auto w-full max-w-md rounded-xl border border-line bg-card p-6 text-fg shadow-xl backdrop:bg-black/40"
>
  <p class="font-semibold">{text}</p>
  {#if detail}
    <p class="mt-2 text-sm text-muted">{detail}</p>
  {/if}
  <div class="mt-6 flex justify-end gap-2">
    <button type="button" class="button-outline" onclick={() => (open = false)}>
      {t("web_cancel", "Cancel")}
    </button>
    <button
      type="button"
      class="button"
      onclick={() => {
        open = false;
        onconfirm();
      }}
    >
      {action}
    </button>
  </div>
</dialog>
