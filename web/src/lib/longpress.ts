// A long press with a finger (500ms without moving): the selection of the
// phone. The click that follows the press is swallowed.

const DELAY = 500;
const SLOP = 10;

export function longpress(node: HTMLElement, onpress: () => void) {
  let timer: ReturnType<typeof setTimeout> | null = null;
  let start = { x: 0, y: 0 };
  let fired = false;

  const cancel = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };
  const down = (event: PointerEvent) => {
    if (event.pointerType !== "touch") return;
    fired = false;
    start = { x: event.clientX, y: event.clientY };
    timer = setTimeout(() => {
      fired = true;
      timer = null;
      navigator.vibrate?.(10);
      onpress();
    }, DELAY);
  };
  const move = (event: PointerEvent) => {
    if (timer && Math.hypot(event.clientX - start.x, event.clientY - start.y) > SLOP) cancel();
  };
  const click = (event: MouseEvent) => {
    if (fired) {
      event.preventDefault();
      event.stopImmediatePropagation();
      fired = false;
    }
  };
  // No menu of the browser on a long press.
  const menu = (event: Event) => fired && event.preventDefault();

  node.addEventListener("pointerdown", down);
  node.addEventListener("pointermove", move);
  node.addEventListener("pointerup", cancel);
  node.addEventListener("pointercancel", cancel);
  node.addEventListener("click", click, true);
  node.addEventListener("contextmenu", menu);
  return {
    update(next: () => void) {
      onpress = next;
    },
    destroy() {
      cancel();
      node.removeEventListener("pointerdown", down);
      node.removeEventListener("pointermove", move);
      node.removeEventListener("pointerup", cancel);
      node.removeEventListener("pointercancel", cancel);
      node.removeEventListener("click", click, true);
      node.removeEventListener("contextmenu", menu);
    },
  };
}
