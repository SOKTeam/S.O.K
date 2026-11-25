// The color of a poster, for the light of the scene: the average of its
// pixels, a little lifted so a dark poster still lights.

const cache = new Map<string, Promise<string | null>>();

/** "r, g, b" of an image, or null when it cannot be read (no CORS). */
export function posterColor(url: string): Promise<string | null> {
  let found = cache.get(url);
  if (!found) {
    found = read(url);
    cache.set(url, found);
  }
  return found;
}

function read(url: string): Promise<string | null> {
  return new Promise((resolve) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 12;
        const context = canvas.getContext("2d")!;
        context.drawImage(image, 0, 0, 12, 12);
        const pixels = context.getImageData(0, 0, 12, 12).data;
        resolve(averageOf(pixels));
      } catch {
        resolve(null);
      }
    };
    image.onerror = () => resolve(null);
    image.src = url;
  });
}

/** The average of RGBA pixels, lifted toward a light of at least 120. */
export function averageOf(pixels: ArrayLike<number>): string {
  let r = 0;
  let g = 0;
  let b = 0;
  const count = pixels.length / 4;
  for (let i = 0; i < pixels.length; i += 4) {
    r += pixels[i];
    g += pixels[i + 1];
    b += pixels[i + 2];
  }
  const rgb = [r / count, g / count, b / count];
  const top = Math.max(...rgb, 1);
  const lift = top < 120 ? 120 / top : 1;
  return rgb.map((value) => Math.min(255, Math.round(value * lift))).join(", ");
}
