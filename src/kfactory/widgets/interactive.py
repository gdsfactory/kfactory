try:
    import asyncio
    from threading import Timer
    from time import time
    from typing import Any, Callable, Optional

    import klayout.db as db
    import klayout.lay as lay
    from ipyevents import Event  # type: ignore[import]
    from ipywidgets import (  # type: ignore[import]
        HTML,
        Accordion,
        AppLayout,
        Button,
        HBox,
        Image,
        Label,
        Layout,
        Tab,
        VBox,
    )

    from ..kcell import KCell, KLib

except ImportError as e:
    print(
        "You need install jupyter notebook plugin with `pip install gdsfactory[full]`"
    )
    raise e

from threading import Thread
from time import sleep


def throttle(wait: float) -> Callable[..., Callable[..., None]]:
    """Decorator that prevents a function from being called
    more than once every wait period."""

    def decorator(fn: Callable[..., None]) -> Callable[..., None]:
        time_of_last_call: float = 0
        scheduled, timer = False, None
        new_args, new_kwargs = None, None

        def throttled(*args: Any, **kwargs: Any) -> None:
            nonlocal new_args, new_kwargs, time_of_last_call, scheduled, timer

            def call_it() -> None:
                nonlocal new_args, new_kwargs, time_of_last_call, scheduled, timer
                time_of_last_call = time()
                fn(*new_args, **new_kwargs)  # type: ignore
                scheduled = False

            time_since_last_call = time() - time_of_last_call
            new_args, new_kwargs = args, kwargs
            if not scheduled:
                scheduled = True
                new_wait = max(0, wait - time_since_last_call)
                timer = Timer(new_wait, call_it)
                timer.start()

        return throttled

    return decorator


class LayoutWidget:
    def __init__(
        self,
        cell: KCell,
        layer_properties: Optional[str] = None,
        hide_unused_layers: bool = True,
        with_layer_selector: bool = True,
    ):
        global i
        layer_properties = str(layer_properties)
        self.hide_unused_layers = hide_unused_layers
        self.layer_properties = layer_properties

        self.layout_view = lay.LayoutView()
        # self.load_layout(filepath, layer_properties)
        self.layout_view.show_layout(cell.klib, True)
        self.layout_view.max_hier()
        self.layout_view.active_cellview().show_cell(cell)
        self.layout_view.resize(800, 600)
        png_data = self.layout_view.get_screenshot_pixels().to_png_data()

        # if self.hide_unused_layers:
        #     self.layout_view.remove_unused_layers()
        #     self.layout_view.reload_layout(self.layout_view.current_layer_list)

        self.image = Image(value=png_data, format="png")
        self.refresh()
        scroll_event = Event(source=self.image, watched_events=["wheel"])
        scroll_event.on_dom_event(self.on_scroll)
        # self.wheel_info = HTML("Waiting for a scroll...")
        # self.mouse_info = HTML("Waiting for a mouse event...")
        self.layout_view.on_image_updated_event = self.refresh  # type: ignore[attr-defined]
        mouse_event = Event(
            source=self.image, watched_events=["mousedown", "mouseup", "mousemove"]
        )
        mouse_event.on_dom_event(self.on_mouse_down)

        if with_layer_selector:
            layer_selector_tabs = self.layer_selector_tabs = self.build_layer_selector(
                max_height=self.layout_view.viewport_height()
            )
        else:
            layer_selector_tabs = None
        # self.layout_view.on_image_updated_event = lambda: self.refresh()

        self.widget = AppLayout(
            center=self.image,
            right_sidebar=layer_selector_tabs,
            left_sidebar=None,
            # footer=VBox([self.wheel_info, self.mouse_info]),
            align_items="top",
            justify_items="left",
        )

    def button_toggle(self, button: Button) -> None:
        button.style.button_color = (
            "transparent"
            if (button.style.button_color == button.default_color)
            else button.default_color
        )

        layer_iter = self.layout_view.begin_layers()

        while not layer_iter.at_end():
            props = layer_iter.current()
            name = (
                props.name
                if props.name
                else f"{props.source_layer}/{props.source_datatype}"
            )
            if name == button.layer_props.name:
                props.visible = not props.visible
                self.layout_view.set_layer_properties(layer_iter, props)
                self.layout_view.reload_layout(self.layout_view.current_layer_list)
                break
            layer_iter.next()
        self.refresh()

    def build_layer_toggle(self, prop_iter: lay.LayerPropertiesIterator) -> HBox:
        # from gdsfactory.utils.color_utils import ensure_six_digit_hex_color

        props = prop_iter.current()
        layer_color = f"#{props.eff_fill_color():06x}"
        # Would be nice to use LayoutView.icon_for_layer() rather than simple colored box
        button_layout = Layout(
            width="5px",
            height="20px",
            # border=f"solid 2px {layer_color}",
            display="block",
        )

        layer_checkbox = Button(
            style={"button_color": layer_color if props.visible else "transparent"},
            layout=button_layout,
        )
        layer_checkbox.default_color = layer_color
        layer_checkbox.layer_props = props

        if props.has_children():
            prop_iter = prop_iter.down_first_child()
            n_children = prop_iter.num_siblings()
            # print(f"{props.name} has {n_children} children!")
            children = []
            for _i in range(n_children):
                prop_iter = prop_iter.next()
                children.append(self.build_layer_toggle(prop_iter))
            layer_label = Accordion([VBox(children)], titles=(props.name,))
        else:
            if props.name:
                layer_label = Label(props.name)
            else:
                layer_label = Label(f"{props.source_layer}/{props.source_datatype}")
        layer_checkbox.label = layer_label

        layer_checkbox.on_click(self.button_toggle)
        return HBox([layer_checkbox, layer_label])

    def build_layer_selector(self, max_height: float) -> Tab:
        """Builds a widget for toggling layer displays.

        Args:
            max_height: Maximum height to set for the widget (likely the height of the pixel buffer).
        """

        all_boxes = []

        prop_iter = self.layout_view.begin_layers()
        while not prop_iter.at_end():
            layer_toggle = self.build_layer_toggle(prop_iter)
            all_boxes.append(layer_toggle)
            prop_iter.next()

        layers_layout = Layout(
            max_height=f"{max_height}px", overflow_y="auto", display="block"
        )
        layer_selector = VBox(all_boxes, layout=layers_layout)

        # For when tabs are implemented
        layer_selector_tabs = Tab([layer_selector])
        layer_selector_tabs.titles = ("Layers",)
        return layer_selector_tabs

    def load_layout(self, filepath: str, layer_properties: Optional[str]) -> None:
        """Loads a GDS layout.

        Args:
            filepath: path for the GDS layout.
            layer_properties: Optional path for the layer_properties klayout file (lyp).
        """
        self.layout_view.load_layout(filepath)
        self.layout_view.max_hier()
        if layer_properties:
            self.layout_view.load_layer_props(layer_properties)

    def refresh(self) -> None:
        # print(i)
        self.layout_view.timer()  # type: ignore[attr-defined]
        png_data = self.layout_view.get_screenshot_pixels().to_png_data()
        self.image.value = png_data
        self.layout_view.timer()  # type: ignore[attr-defined]

    def _get_modifier_buttons(self, event: Event) -> int:
        shift = event["shiftKey"]
        alt = event["altKey"]
        ctrl = event["ctrlKey"]
        # meta = event["metaKey"]

        mouse_buttons = event["buttons"]

        buttons = 0
        if shift:
            buttons |= lay.ButtonState.ShiftKey
        if alt:
            buttons |= lay.ButtonState.AltKey
        if ctrl:
            buttons |= lay.ButtonState.ControlKey

        if mouse_buttons == 1:
            buttons |= lay.ButtonState.LeftButton
        elif mouse_buttons == 2:
            buttons |= lay.ButtonState.RightButton
        elif mouse_buttons == 4:
            buttons |= lay.ButtonState.MidButton

        return buttons

    @throttle(0.05)
    def on_scroll(self, event: Event) -> None:
        self.layout_view.timer()  # type: ignore[attr-defined]
        delta = int(event["deltaY"])
        x = event["offsetX"]
        y = event["offsetY"]
        buttons = self._get_modifier_buttons(event)
        # TODO: this is what I *want* to respond with, but it doesn't work, so I am using zoom_in/zoom_out instead
        self.layout_view.send_wheel_event(-delta, False, db.DPoint(x, y), buttons)
        self.refresh()

    @throttle(0.05)
    def on_mouse_down(self, event: Event) -> None:
        self.layout_view.timer()  # type: ignore[attr-defined]
        x = event["offsetX"]
        y = event["offsetY"]
        moved_x = event["movementX"]
        moved_y = event["movementY"]
        buttons = self._get_modifier_buttons(event)
        # TODO: this part is also not working. why?
        if event == "mousedown":
            self.layout_view.send_mouse_press_event(db.DPoint(x, y), buttons)
        elif event == "mouseup":
            self.layout_view.send_mouse_release_event(db.DPoint(x, y), buttons)
        elif event == "mousemove":
            self.layout_view.send_mouse_move_event(db.DPoint(moved_x, moved_y), buttons)
        self.refresh()
