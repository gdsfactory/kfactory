// Header button toggling between full width (default) and the theme's
// narrow layout. The choice is stored like the palette (per docs version);
// main.html applies it before first paint.
function kfSetWidth(button, narrow) {
  const label = narrow ? "Full width" : "Narrow layout"
  button.title = label
  button.setAttribute("aria-label", label)
  if (narrow) {
    document.documentElement.setAttribute("data-kf-width", "narrow")
  } else {
    document.documentElement.removeAttribute("data-kf-width")
  }
}

// Instant navigation may re-render the header, so (re)insert on every page.
document$.subscribe(() => {
  const header = document.querySelector(".md-header__inner")
  const template = document.getElementById("kf-width-toggle")
  if (!header || !template || header.querySelector(".kf-width-toggle")) return

  const button = template.content.firstElementChild.cloneNode(true)
  kfSetWidth(button, __md_get("kf.width") === "narrow")
  button.addEventListener("click", () => {
    const narrow = document.documentElement.getAttribute("data-kf-width") !== "narrow"
    kfSetWidth(button, narrow)
    __md_set("kf.width", narrow ? "narrow" : "full")
  })
  header.insertBefore(button, header.querySelector("[data-md-component=palette]"))
})
