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


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle('PyQt & matplotlib demo: Data plotting')

        # self.data = DataHolder()
        # self.series_list_model = QStandardItemModel()
        
        # Loading data
        self.data = np.loadtxt("data.txt")
        lons = np.linspace(-179.5,179.5,self.data.shape[1])
        lats = np.linspace(89.5,-89.5,self.data.shape[0])
        x, y = np.meshgrid(lons, lats)
        self.data = self.data.flatten()
        
        self.x = x.flatten()
        self.y = y.flatten()
        
        self.create_menu()
        self.create_main_frame()
        self.on_draw()
        self.statusBar().showMessage('GeoEditor 2015')
        
        #
        # self.update_ui()
        # self.on_show()
    
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        self.main_frame.setMinimumSize(QSize(1280, 800))
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = plt.Figure((18.0, 10.0), dpi=self.dpi)
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

        # self.textbox = QLineEdit()
        # self.textbox.setMinimumWidth(200)
        # self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
        
        slider_label = QLabel('Scatter marker size:')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 100)
        self.slider.setValue(5)
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.slider, SIGNAL('valueChanged(int)'), self.on_draw)
        

        self.infodisplay = QLabel("Pixel &information:")
        self.latdisplay  = QLabel("Lat: ")
        self.londisplay  = QLabel("Lon: ")
        self.valdisplay  = QLabel("Val: ")

        # Layout with box sizers
    
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.addWidget(self.mpl_toolbar)
        
        
        vbox2 = QVBoxLayout()
        # vbox2.addWidget(self.draw_button)
        for w in [self.infodisplay, self.latdisplay, self.londisplay, self.valdisplay, slider_label, self.slider]:
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
        
        self.axes.scatter(self.x, self.y, s=self.slider.value(), c=self.data, marker='s', cmap=mpl.cm.RdBu, edgecolor=None, linewidth=0, picker=1)
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
