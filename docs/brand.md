# The mark

A leaf whose midrib is a process pipe.

The band down the centre is one continuous column that changes polarity partway down: above
the flip it is cut out of the fill and reads as a channel; below it, it is ink and reads as
the stem leaving the leaf. That flip is the whole mark — a stream crossing a boundary, which
is how a flowsheet draws a feed entering a unit. It is the app's subject in one glyph: a
plant, and the thing flowing through it.

`assets/mark.svg` · `assets/favicon.svg` · `assets/favicon-32.png` ·
`assets/apple-touch-icon.png` — 5.9 KB the lot.

## How it was arrived at

Generated first, then hand-authored. Both `gemini-2.5-flash-image` and `gpt-image-1` were run
across several concept families — a leaf that is also a flowsheet, a split water droplet, an
H₂O/H₂ glyph, a plant schematic. Generation was useful for finding the *shape language* and
useless for the artefact: every model output failed the only test that matters here, which is
16 pixels.

Three failures worth recording, because they are the reason the final mark is as plain as it is:

- **Hairlines die at 16px.** Veins branching off the midrib at 45° looked best at 180px and
  became an even grey diamond at favicon size, because the cuts and the surviving fill were
  both about one pixel.
- **Small detail becomes a different symbol.** A bowtie gate valve on the midrib — correct
  P&ID notation, and the most "process" thing in any draft — resolved to a crucifix.
- **A floating channel reads as an eye.** The fix was for the channel to break the silhouette:
  a cut with an opening is unmistakably a channel.

What survives a 4× downsample is one bold silhouette with one wide cut, so that is all this is.
The geometry sits on a 64-unit grid, so every edge lands on a whole pixel at 16, 32 and 64.

The prompts that produced the useful concepts are worth keeping for a regeneration:

> flat two-colour vector mark, a leaf whose central vein is a pipe carrying bubbles, technical
> drawing style, Prussian blue on cream, no gradient, no 3D, no glow, thick confident line,
> reads at 16 pixels

> minimal engineering glyph: a water droplet splitting into two, drawn as a flowsheet symbol,
> flat, single colour, hairline construction lines, 1960s technical manual

## How it ships

As a **CSS mask**, not an `<img>`. The two places it appears have opposite grounds — the
masthead is the app's dark surface, the front door is cream — so a mask that inherits
`currentColor` serves both without a second file or a recolour. `mark.svg` is authored
`fill="currentColor"` as well, so inlining it also works.

The favicon bakes its colour instead, because a favicon renders outside the page and has no
`currentColor` to inherit.

## The loading animation

Deliberately **not** Lottie. `lottie-web` is about 250 KB of JavaScript, and shipping it to
decorate the wait for a 25 MB runtime makes the wait longer — worse, it has to load and run
before it can tell you that something is loading.

Instead the mark itself is the indicator: the channel fills from the stem up, driven by
`--fill`, which `deploy/boot.js` writes from the same percentage that drives the progress bar.
So what you are watching rise is the thing that is actually loading, rather than an animation
running on a timer beside it. Before the first real progress arrives there is nothing honest
to show, so the level breathes; that stops the moment a stage reports.

One element, two rules and a keyframe, and it honours `prefers-reduced-motion`.
