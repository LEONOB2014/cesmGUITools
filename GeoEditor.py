"""
GeoEditor.py

This program allows one to edit a 2D latitude-longitude gridded
data pixel for pixel.

Author : Deepak Chandan
Date   : February 17th, 2015
"""

import sys
import numpy as np
from PyQt4.QtCore import *
from PyQt4.QtGui import *


import matplotlib as mpl
from matplotlib import pylab as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar


class DataWindow(object):
    """
    A view of the global data
    """
    def __init__(self, m, n):
        self.data = None
        self.nrows= m
        self.ncols= n
        self.si   = None  # the global index of the first element 
    
    def update(self, vals):
        self.data = np.copy(vals)


class GlobalData(object):
    def __init__(self, fname):
        self.raw_data = np.loadtxt(fname)
        self.nrows, self.ncols = self.raw_data.shape
        self.fdata = self.raw_data.flatten()
        
        lons = np.linspace(-179.5,179.5,self.raw_data.shape[1])
        lats = np.linspace(89.5,-89.5,self.raw_data.shape[0])
        self.x, self.y = np.meshgrid(lons, lats)
        
        self.original_data = np.copy(self.raw_data)
        
    
    def global_index_to_ij(self, idx):
        return (idx/self.ncols, idx%self.ncols)
    
    def if_to_global_index(self, i, j):
        return i*self.ncols + j
    
    def __getitem__(self, i):
        if isinstance(i, tuple):
            return self.raw_data[i]
        else:
            return self.fdata[i]
    
    def __setitem__(self, i, val):
        if isinstance(i, tuple):
            self.raw_data[i] = val
        else:
            self.fdata[i] = val
    
    
    

class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle('PyQt & matplotlib demo: Data plotting')
        
        self.alldata = GlobalData("data.txt")
        
        self.dw = DataWindow(20,20)
        # self.dw.update(self.raw_data[0:20,0:20].flatten())
        
        self.create_menu()
        self.create_main_frame()
        self.on_draw()
        self.statusBar().showMessage('GeoEditor 2015')
        
        #
        # self.update_ui()
        # self.on_show()
    
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        self.main_frame.setMinimumSize(QSize(800, 600))
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = plt.Figure((6.5, 5), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        
        
        # # Bind the 'pick' event for clicking on one of the bars
        # #
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        # Create the navigation toolbar, tied to the canvas
        #
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        # Other GUI controls


        self.infodisplay = QLabel("Pixel &information:")
        self.latdisplay  = QLabel("Lat: ")
        self.londisplay  = QLabel("Lon: ")
        self.valdisplay  = QLabel("Val: ")

        # Layout with box sizers
    
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        
        
        vbox2 = QVBoxLayout()
        for w in [self.infodisplay, self.latdisplay, self.londisplay, self.valdisplay]:
            w.setFixedWidth(150)
            vbox2.addWidget(w)
            vbox2.setAlignment(w, Qt.AlignTop)
        vbox2.addStretch(1)
        
        hbox = QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.addLayout(vbox2)
        
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)
    
    
    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action
    
    
    def on_draw(self):
        """ Redraws the figure
        """
        self.axes.clear()
        
        self.axes.scatter(self.alldata.x, self.alldata.y, s=5, c=self.alldata.fdata, marker='s', cmap=mpl.cm.RdBu, edgecolor=None, linewidth=0, picker=1)
        # plt.colorbar(mappable)
        self.axes.set_xlim([-179.5,179.5])
        self.axes.set_ylim([-89.5,89.5])
        self.canvas.draw()
        self.fig.tight_layout()
    
    
    def on_pick(self, event):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        # 
        # box_points = event.artist.get_bbox().get_points()
        
        mevent = event.mouseevent
        # print mevent.xdata, mevent.ydata
        print event.ind
        self.latdisplay.setText("Hello!")
    
    
    def on_about(self):
        msg = """ A demo of using PyQt with matplotlib:
        
         * Use the matplotlib navigation bar
         * Add values to the text box and press Enter (or click "Draw")
         * Show or hide the grid
         * Drag the slider to modify the width of the bars
         * Save the plot to a file using the File menu
         * Click on a bar to receive an informative message
        """
        QMessageBox.about(self, "About the demo", msg.strip())
    
    
    def save_plot(self): pass
    
    
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
    

    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        load_file_action = self.create_action("&Save plot",
            shortcut="Ctrl+S", slot=self.save_plot, 
            tip="Save the plot")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (load_file_action, None, quit_action))
        
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the demo')
        
        self.add_actions(self.help_menu, (about_action,))
    
    
def main():
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    app.exec_()


if __name__ == "__main__":
    main()
