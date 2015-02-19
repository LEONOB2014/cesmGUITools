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
from mpl_toolkits.basemap import Basemap
import matplotlib.patches as mpatches
from matplotlib.collections import PatchCollection
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
        
        self.cursor  = None
        self.cursorx = 0
        self.cursory = 0
        
        
        self.create_menu()
        self.create_main_frame()
        self.draw_datawindow_content()
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
            self.update_data_window(e)
    
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        self.main_frame.setMinimumSize(QSize(800, 600))
        
        self.dpi = 100
        self.fig = plt.Figure((6.5, 5), dpi=self.dpi, facecolor='w', edgecolor='w')
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        
        self.preview_frame = QWidget()
        self.preview_fig = plt.Figure((3, 1.5), dpi=self.dpi, facecolor='w', edgecolor='w')
        self.preview = FigureCanvas(self.preview_fig)
        self.preview.setParent(self.preview_frame)
        self.preview_axes = self.preview_fig.add_subplot(111)
        self.preview_axes.get_xaxis().set_visible(False)
        self.preview_axes.get_yaxis().set_visible(False)
        
        
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
        
        
        # Other GUI controls
        # Information section
        self.infodisplay = QLabel("Pixel Information:")
        self.latdisplay  = QLabel("Latitude   : ")
        self.londisplay  = QLabel("Longitude: ")
        self.valdisplay  = QLabel("Value       : ")
        
        # Pixel size control slider
        pixel_slider_label = QLabel('Pixel size:')
        self.pixel_slider = QSlider(Qt.Horizontal)
        self.pixel_slider.setRange(1, 100)
        self.pixel_slider.setValue(25)
        self.pixel_slider.setTracking(True)
        self.pixel_slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.pixel_slider, SIGNAL('valueChanged(int)'), self.draw_datawindow_content)
        
        # Colorscheme selector
        cmap_label = QLabel('Colorscheme:')
        self.colormaps = QComboBox(self)
        self.colormaps.addItems(self.maps)
        self.colormaps.setCurrentIndex(self.maps.index('RdBu'))
        self.connect(self.colormaps, SIGNAL("currentIndexChanged(int)"), self.draw_datawindow_content)
        
        # New value editor
        self.inputbox = QLineEdit()
        self.connect(self.inputbox, SIGNAL('editingFinished ()'), self.update_value)
        
        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        
        
        vbox2 = QVBoxLayout()
        vbox2.addWidget(self.preview)
        self.draw_preview_worldmap()
        
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
    
    
    def draw_preview_worldmap(self):
        m = Basemap(projection='cyl', lon_0=0,llcrnrlat=-90,urcrnrlat=90,\
            llcrnrlon=-180,urcrnrlon=180,resolution='c', ax=self.preview_axes)
        m.drawcoastlines(linewidth=0.5)
        self.preview_axes.set_xlim([-180,180])
        self.preview_axes.set_ylim([-90,90])
        self.preview.draw()
        self.draw_preview_window()
        self.preview_fig.tight_layout()
    
    
    def draw_preview_window(self):
        patches = []
        i, j = self.dw.index_to_ij(self.dw.si)
        i, j = self.dw.dw_ij2_global(i, j)
        print self.gd.lons[j], self.gd.lats[i+self.dw.nrows]
        dlat = self.gd.lats[0] - self.gd.lats[self.dw.nrows]
        dlon = abs(self.gd.lons[0] - self.gd.lons[self.dw.ncols])
        print dlat, dlon
        rect = mpatches.Rectangle((self.gd.lons[j], self.gd.lats[i+self.dw.nrows]), dlat, dlon, linewidth=2, facecolor='k')
        patches.append(rect)
        collection = PatchCollection(patches, cmap=plt.cm.hsv, alpha=0.3)
        self.preview_axes.add_collection(collection)
        self.preview.draw()
    
    
    
    def update_data_window(self, event):
        """
        Updates the current view in the data window. This function is 
        triggered whenever the user presses the arrow keys. 
        ARGUMENTS
            event - Qt key press event
        """
        key = event.key()
        on_boundary = None   #This will store which boundary if any we've reached
        if key == Qt.Key_Up:
            if (self.cursory == 0):
                on_boundary = "top"
            else:
                self.cursory = max(0, self.cursory - 1)
        elif key == Qt.Key_Down:
            if (self.cursory == self.dw.nrows-1):
                on_boundary = "down"
            else:
                self.cursory = min(self.dw.nrows-1, self.cursory + 1)
        elif key == Qt.Key_Left:
            if (self.cursorx == 0):
                on_boundary = "left"
            else:
                self.cursorx = max(0, self.cursorx - 1)
        elif key == Qt.Key_Right:
            if (self.cursorx == self.dw.ncols-1):
                on_boundary = "right"
            else:
                self.cursorx = min(self.dw.ncols-1, self.cursorx + 1)
        else:
            return
        
        if on_boundary: 
            pass
        
        self.update_cursor_position()
        
    
    
    def update_cursor_position(self, noremove=False):
        if self.cursor and (not noremove): self.cursor.remove()
        _cx, _cy = self.cursorx, self.cursory
        self.cursor = self.axes.scatter(_cx, _cy, 
                                        s=self.pixel_slider.value(), 
                                        marker='s', 
                                        edgecolor="k", 
                                        facecolor='none', 
                                        linewidth=2)  
        self.set_information(_cy, _cx)        
        self.canvas.draw()
        
    
    
    def draw_datawindow_content(self):
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
        self.update_cursor_position(noremove=True)
    
    


    def update_value(self):
        print "text received: {0}".format(self.inputbox.text())
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
