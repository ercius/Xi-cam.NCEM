import pyqtgraph as pg
import numpy as np

from qtpy.QtWidgets import *

from xicam.plugins import QWidgetPlugin
from xicam.core import msg
from .NCEMViewerPlugin import NCEMViewerPlugin
from .ncemimageview import NCEMFFTView


class FFTViewerPlugin(QWidgetPlugin):
    def __init__(self, catalog, stream: str = 'primary', field: str = 'raw', toolbar: QToolBar = None, *args, **kwargs):

        self.stream = stream
        self.field = field
        self.catalog = catalog

        super(FFTViewerPlugin, self).__init__(*args, **kwargs)

        # Set up two views
        self.Rimageview = NCEMViewerPlugin(catalog)
        self.Fimageview = NCEMFFTView()

        self.Rimageview.imageItem.setOpts(axisOrder="row-major")
        # self.Fimageview.imageItem.setOpts(axisOrder="row-major") # not needed for FFT

        # Add to a layout
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.Rimageview)
        self.layout().addWidget(self.Fimageview)

        # Add ROI to real image
        self.Rroi = pg.RectROI(pos=(0, 0), size=(1, 1))
        self.Rimageview.view.vb.addItem(self.Rroi)

        # Hide the menu and roi buttons in the FFT view
        self.Fimageview.ui.menuBtn.setParent(None)
        self.Fimageview.ui.roiBtn.setParent(None)

        # Wireup signals
        self.Rroi.sigRegionChanged.connect(self.updateFFT)
        self.Rimageview.sigTimeChanged.connect(
            self.updateFFT)  # TODO: If you'd like, use sigTimeChangeFinished here instead?
        self.Rimageview.sigStreamChanged.connect(self.initialize_Rroi)
        self.Rimageview.sigStreamChanged.connect(self.updateFFT)
        self.Rimageview.sigFieldChanged.connect(self.initialize_Rroi)
        self.Rimageview.sigFieldChanged.connect(self.updateFFT)

        # Init vars
        self.autoLevels = True

        self.initialize_Rroi()
        self.updateFFT()

    def initialize_Rroi(self):
        scale0, units0 = self.Rimageview._get_physical_size()

        # Set the starting position of the real ROI
        sh = self.Rimageview.xarray.shape
        sz = [int(ii / 8) for ii in sh]
        self.Rroi.setPos((scale0[-1] * (sh[-1] / 2 - sz[-1] / 2), scale0[-2] * (sh[-2] / 2 - sz[-2] / 2)))
        self.Rroi.setSize((scale0[-1] * sz[-1], scale0[-2] * sz[-2]))

    def updateFFT(self):
        """ Update the FFT diffractogram based on the Real space
        ROI location and size

        """
        # Get the frame data back from Rimageview (applies timeline slicing)
        try:
            data = self.Rimageview.imageItem.image[::-1, :]

            scale0, units0 = self.Rimageview._get_physical_size()

            # Extract the data in the ROI
            x, y = self.Rroi.pos()
            w, h = self.Rroi.size()

            # For testing. Show real space image instead of FFT
            # dataSlice = data[int(y / scale0[1]):int((y + h) / scale0[1]), int(x / scale0[0]):int((x + w) / scale0[0])]
            # self.Fimageview.setImage(dataSlice)

            # Unsure of the scale0 order with respect to x,y and w,h
            dataSlice = data[int(y / scale0[1]):int((y + h) / scale0[1]), int(x / scale0[0]):int((x + w) / scale0[0])]
            fft = np.fft.fft2(dataSlice)
            self.Fimageview.setImage(np.log(np.abs(np.fft.fftshift(fft)) + .001))

            self.Rroi.setPen(pg.mkPen('w'))
        except ValueError:
            self.Rroi.setPen(pg.mkPen('r'))
