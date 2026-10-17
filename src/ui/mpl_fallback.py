"""Software-rendered vector field view for machines without usable OpenGL.

PyVista/VTK needs an OpenGL context, which remote desktops, virtual machines
and missing graphics drivers often cannot provide.  This view draws the same
data with Matplotlib's Agg rasteriser instead: a quiver plot in 2D mode and
an ``mplot3d`` quiver in 3D mode.  It is slower and not as interactive, but
it keeps the Visualization tab useful.
"""

import matplotlib
import numpy as np
from matplotlib import cm, colors
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.ui.themes import PALETTES


def _directions(vectors):
    """Unit vectors (zero where the field vanishes)."""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(norms > 0, vectors / norms, 0.0)


class MatplotlibFieldView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure(figsize=(6, 5), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self._palette = PALETTES["dark"]
        self.clear()

    def apply_palette(self, palette):
        self._palette = palette
        self.figure.set_facecolor(palette["plot_background"])
        for axes in self.figure.axes:
            self._style_axes(axes)
        self.canvas.draw_idle()

    def _style_axes(self, axes):
        foreground = self._palette["plot_foreground"]
        axes.set_facecolor(self._palette["plot_background"])
        axes.tick_params(colors=foreground)
        for label in (axes.xaxis.label, axes.yaxis.label, axes.title):
            label.set_color(foreground)
        if hasattr(axes, "zaxis"):
            axes.zaxis.label.set_color(foreground)
            for axis in (axes.xaxis, axes.yaxis, axes.zaxis):
                axis.set_pane_color(colors.to_rgba(self._palette["plot_background"]))
        else:
            for spine in axes.spines.values():
                spine.set_color(foreground)

    def clear(self):
        self.figure.clear()
        self.figure.set_facecolor(self._palette["plot_background"])
        self.canvas.draw_idle()

    def show_message(self, text):
        self.clear()
        self.figure.text(
            0.5, 0.5, text, ha="center", va="center", color=self._palette["plot_foreground"]
        )
        self.canvas.draw_idle()

    def plot(self, points, vectors, magnitudes, lengths, is_2d):
        """Draw arrows of the given ``lengths`` along ``vectors``, coloured by magnitude."""
        self.clear()
        scaled = _directions(vectors) * np.asarray(lengths)[:, None]
        norm = colors.Normalize(vmin=float(magnitudes.min()), vmax=float(magnitudes.max()))
        colormap = matplotlib.colormaps["viridis"]
        rgba = colormap(norm(magnitudes))

        if is_2d:
            axes = self.figure.add_subplot()
            axes.quiver(
                points[:, 0], points[:, 1], scaled[:, 0], scaled[:, 1],
                color=rgba, angles="xy", scale_units="xy", scale=1,
                width=0.004, pivot="tail",
            )
            axes.set_aspect("equal")
            self._pad_limits(axes, points, scaled)
        else:
            axes = self.figure.add_subplot(projection="3d")
            # A 3D quiver arrow is three line segments (shaft, two head
            # lines), and ``colors`` is consumed per segment.
            segment_colours = np.concatenate([rgba, np.repeat(rgba, 2, axis=0)])
            axes.quiver(
                points[:, 0], points[:, 1], points[:, 2],
                scaled[:, 0], scaled[:, 1], scaled[:, 2],
                colors=segment_colours, length=1.0, normalize=False,
                arrow_length_ratio=0.3,
            )
            axes.set_zlabel("z")
        axes.set_xlabel("x")
        axes.set_ylabel("y")
        self._style_axes(axes)

        mappable = cm.ScalarMappable(norm=norm, cmap=colormap)
        colourbar = self.figure.colorbar(mappable, ax=axes, shrink=0.8, label="magnitude")
        foreground = self._palette["plot_foreground"]
        colourbar.ax.tick_params(colors=foreground)
        colourbar.ax.yaxis.label.set_color(foreground)
        colourbar.outline.set_edgecolor(foreground)
        self.canvas.draw_idle()

    @staticmethod
    def _pad_limits(axes, points, scaled):
        tips = points[:, :2] + scaled[:, :2]
        both = np.vstack([points[:, :2], tips])
        low, high = both.min(axis=0), both.max(axis=0)
        pad = 0.05 * np.maximum(high - low, 1e-9)
        axes.set_xlim(low[0] - pad[0], high[0] + pad[0])
        axes.set_ylim(low[1] - pad[1], high[1] + pad[1])

    def save_png(self, file_path):
        self.canvas.draw()
        self.figure.savefig(file_path, format="png", facecolor=self.figure.get_facecolor())
        return True
