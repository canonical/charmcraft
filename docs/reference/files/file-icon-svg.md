(file-icon-svg)=
# File 'icon.svg'

> <small> {ref}`List of files in the charm project <list-of-files-in-a-charm-project>` > `icon.svg` </small>
>

If you've uploaded your charm on Charmhub, once you've released the charm into a channel with the `stable` risk level, if your charm project includes an `icon.svg` file, the icon  will be displayed in your charm's Charmhub profile.

## Requirements

- The file must have this exact name: `icon.svg`. 
- The canvas size must be 100x100 pixels.
- The icon must consist of a circle with a flat color and a logo -- any other detail is up to you, but it's a good idea to also conform to best practices.

## Best practices

- Icons should have some padding between the edges of the circle and the logo.
- Icons should not be overly complicated. Charm icons are displayed in various sizes (from 160x160 to 32x32 pixels) and they should be always legible. 

```{tip}
In Inkscape, the ‘Icon preview’ tool can help you to check the sharpness of your icons at small sizes.
```
- Symbols should have a similar weight on all icons: Avoid too thin strokes and use the whole space available to draw the symbol within the limits defined by the padding. However, if the symbol is much wider than it is high, it may overflow onto the horizontal padding area to ensure its weight is consistent.
- Do not use glossy materials unless they are parts of a logo that you are not allowed to modify.
