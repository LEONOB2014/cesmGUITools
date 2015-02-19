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

mpl.rc('axes',edgecolor='w')

class Data(object):
    def __init__(self):
        self.ncols = None
        self.nrows = None
    
    def index_to_ij(self, idx):
        """ Maps the scalar index of each element into it's (i,j) index. """
        return (idx/self.ncols, idx%self.ncols)
    
    def ij_to_index(self, i, j):
        """ Maps the (i,j) index of each element into a unique scalar index. """
        return i*self.ncols + j
    


class DataWindow(Data):
    """
    A view of the global data
    """
    def __init__(self, m, n):
        self.data = None
        self.nrows= m
        self.ncols= n
        self.si   = None  # the global index of the first element 
        
        self.x, self.y = np.meshgrid(np.arange(self.ncols), np.arange(self.nrows))
        self.x = self.x.flatten()
        self.y = self.y.flatten()
    
    def update(self, vals, si):
        self.data = np.copy(vals)
        self.si = si
        
    def dw_ij2_global(self, i, j):
        """ Converts an i,j index into the data window into an index for the
        same element into the global data. """
        return (self.si/self.ncols + i, self.si%self.ncols + j)


class GlobalData(Data):
    """
    This class contains the global, i.e. the full data for the program. It also
    contains the lat/lon coordinates for the data and a number of helper functions
    to help convert between 2D and 1D indexing of the data. 
    """
    def __init__(self, fname):
        self.raw_data = np.loadtxt(fname)
        self.original_data = np.copy(self.raw_data)
        self.nrows, self.ncols = self.raw_data.shape
        self.fdata = self.raw_data.flatten()
        
        self.lons = np.linspace(-179.5,179.5,self.raw_data.shape[1])
        self.lats = np.linspace(89.5,-89.5,self.raw_data.shape[0])
                
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
    
    
    

class GeoEditor(QMainWindow):
    def __init__(self, parent=None, dwx=160, dwy=160):
        """
        ARGUMENTS:
            dwx, dwy - size of the DataWindow in number of array elements
        """
        super(GeoEditor, self).__init__(parent)
        self.setWindowTitle('GeoEditor (c) Deepak Chandan')
        
        self.gd = GlobalData("data.txt")
        self.dw = DataWindow(dwy, dwx)
        # Set the initial data to the DataWindow class
        self.dw.update(self.gd[0:dwy, 0:dwx].flatten(), self.gd.ij_to_index(0,0))
        
        self.maps = mpl.cm.datad.keys()  # The names of colormaps available
        self.maps.sort() # Sorting them alphabetically for ease of use
        
        self.cursor = None
        self.cursorx = 0
        self.cursory = 0
        
        
        self.create_menu()
        self.create_main_frame()
        self.on_draw()
        self.statusBar().showMessage('GeoEditor 2015')
    
    
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_E:
            # Pressing e for edit
            self.inputbox.setFocus()
        elif e.key() == Qt.Key_C:
            self.colormaps.setFocus()
        elif e.key() == Qt.Key_Plus:
            self.pixel_slider.setValue(self.pixel_slider.value()+2)
        elif e.key() == Qt.Key_Minus:
            self.pixel_slider.setValue(self.pixel_slider.value()-2)
        elif e.key() == Qt.Key_Escape:
            # Pressing escape to refocus back to the main frame
            self.main_frame.setFocus()
        else:
            self.draw_cursor(event=e)
    
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        self.main_frame.setMinimumSize(QSize(800, 600))
        
        self.dpi = 100
        self.fig = plt.Figure((6.5, 5), dpi=self.dpi, facecolor='w', edgecolor='w')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        self.axes = self.fig.add_subplot(111)
        # Turning off the axes ticks to maximize space. Also the labels were meaningless
        # anyway because they were not representing the actual lat/lons. 
        self.axes.get_xaxis().set_visible(False)
        self.axes.get_yaxis().set_visible(False)
        
        self.canvas.mpl_connect('pick_event', self.on_pick)
        # self.canvas.mpl_connect('key_press_event', self.draw_cursor)
        
        # Create the navigation toolbar, tied to the canvas
        #
        # self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        # Other GUI controls


        self.infodisplay = QLabel("Pixel Information:")
        self.latdisplay  = QLabel("Latitude   : ")
        self.londisplay  = QLabel("Longitude: ")
        self.valdisplay  = QLabel("Value       : ")
        
        pixel_slider_label = QLabel('Pixel size:')
        self.pixel_slider = QSlider(Qt.Horizontal)
        self.pixel_slider.setRange(1, 100)
        self.pixel_slider.setValue(25)
        self.pixel_slider.setTracking(True)
        self.pixel_slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.pixel_slider, SIGNAL('valueChanged(int)'), self.on_draw)
        
        cmap_label = QLabel('Colormap:')
        self.colormaps = QComboBox(self)
        self.colormaps.addItems(self.maps)
        self.colormaps.setCurrentIndex(self.maps.index('RdBu'))
        self.connect(self.colormaps, SIGNAL("currentIndexChanged(int)"), self.on_draw)
        
        self.inputbox = QLineEdit()
        self.connect(self.inputbox, SIGNAL('editingFinished ()'), self.update_value)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        # vbox.addWidget(self.mpl_toolbar)
        
        
        vbox2 = QVBoxLayout()
        for w in [self.infodisplay, self.latdisplay, self.londisplay, self.valdisplay, self.inputbox]:
            w.setFixedWidth(150)
            vbox2.addWidget(w)
            vbox2.setAlignment(w, Qt.AlignTop)
        vbox2.addStretch(1)
        vbox2.addWidget(cmap_label)
        vbox2.addWidget(self.colormaps)
        vbox2.addStretch(1)
        for w in [pixel_slider_label, self.pixel_slider]:
            vbox2.addWidget(w)
            vbox2.setAlignment(w, Qt.AlignBottom)
            
        
        hbox = QHBoxLayout()
        hbox.addLayout(vbox)
        hbox.addLayout(vbox2)
        
        self.main_frame.setLayout(hbox)
        self.setCentralWidget(self.main_frame)
        self.main_frame.setFocus()
        
    
    def on_draw(self):
        """ Redraws the figure
        """
        self.axes.clear()
        
        cmap = mpl.cm.get_cmap(self.maps[self.colormaps.currentIndex()])
        self.axes.scatter(self.dw.x, 
                          self.dw.y, 
                          s=self.pixel_slider.value(), 
                          c=self.dw.data, 
                          marker='s', 
                          cmap=cmap, 
                          edgecolor=None, 
                          linewidth=0, 
                          picker=3)
        
        # Setting the axes limits. This helps in setting the right orientation of the plot
        # and in clontrolling how much extra space we want around the scatter plot.
        tmp1 = self.dw.nrows
        tmp2 = self.dw.ncols
        # I am putting 4% space around the scatter plot
        self.axes.set_ylim([int(tmp1*1.04), 0 - int(tmp1*0.04)])
        self.axes.set_xlim([0 - int(tmp2*0.04), int(tmp2*1.04)])
        self.canvas.draw()
        self.fig.tight_layout()
        self.draw_cursor(noremove=True)
    
    
    def draw_cursor(self, event=None, noremove=False):
        """ noremove - If True, does not make a call to remove the previous cursor. """
        if event is not None: 
            # We are only doin this when there is an event, i.e. we have reached this function
            # not from a manual call but the triggering of a function
            key = event.key()
            # Changing the position of the cursor, while making sure that the new position
            # is not outside the boundary of the datawindow. 
            if key == Qt.Key_Up:
                self.cursory = max(0, self.cursory - 1)
            elif key == Qt.Key_Down:
                self.cursory = min(self.dw.nrows-1, self.cursory + 1)
            elif key == Qt.Key_Left:
                self.cursorx = max(0, self.cursorx - 1)
            elif key == Qt.Key_Right:
                self.cursorx = min(self.dw.ncols-1, self.cursorx + 1)
            else:
                return
        
        if self.cursor and (not noremove): self.cursor.remove()
        self.cursor = self.axes.scatter(self.cursorx, 
                                        self.cursory, 
                                        s=self.pixel_slider.value(), 
                                        marker='s', 
                                        edgecolor="k", 
                                        facecolor='none', 
                                        linewidth=2)
        
        self.set_information(self.cursory, self.cursorx)        
        self.canvas.draw()
    
    
    # def update_value_under_cursor(self):
    def update_value(self):
        print "text received: {0}".format(self.inputbox.text())
        # self.canvas.setFocus()
        self.main_frame.setFocus()
    
    
    
    def on_pick(self, event):
        # If we've picked up more than one point then we need to try again!
        if len(event.ind) > 1:
            self.statusBar().showMessage("!!! More than one points picked. Try again !!!")
            self.latdisplay.setText("Latitude   : ")
            self.londisplay.setText("Longitude: ")
            self.valdisplay.setText("Value       : ")
        else:
            self.statusBar().showMessage("Selected one point")
            # event.ind[0] is the "local" index in the data window. 
            dw_i, dw_j = self.dw.index_to_ij(event.ind[0])
            self.set_information(dw_i, dw_j)
    
    
    
    def set_information(self, i, j):
        """ Sets the displayed information about the pixel in the right sidebar. 
        ARGUMENTS
            i, j : the local (i.e. DataWindow) 0-based indices for the element
        """
        i_global, j_global = self.dw.dw_ij2_global(i, j) # Convert local indices to global indices
        self.latdisplay.setText("Latitude   : {0}".format(self.gd.lats[i_global]))
        self.londisplay.setText("Longitude: {0}".format(self.gd.lons[j_global]))
        self.valdisplay.setText("Value       : {0}".format(self.gd[i_global, j_global]))
    
    
    def on_about(self):
        msg = """ Edit 2D geophysical field.  """
        QMessageBox.about(self, "About", msg.strip())
    
    
    def save_plot(self): pass
    
    
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
    mw = GeoEditor(dwx=50,dwy=50)
    mw.show()
    app.exec_()


if __name__ == "__main__":
    main()
