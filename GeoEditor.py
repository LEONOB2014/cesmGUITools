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

class DataContainer(object):
    """
    A view of the global data
    """
    def __init__(self, nrows, ncols, fname):
        """
        ARGUMENTS
            nrows - number of rows in the view
            ncols - number of columns in the view
            fname - name of the data file.
        """
        self.data = np.loadtxt(fname)
        self.ny, self.nx = self.data.shape
        self.lons = np.linspace(-179.5,179.5,self.nx)
        self.lats = np.linspace(89.5,-89.5,self.ny)
                
        
        # Datawindow variables
        self.view   = None        # The array (actually a numpy view) that stores the data to be displayed in the main window
        self.nrows  = nrows
        self.ncols  = ncols
        self.si     = None        # 0-based row index of the first element 
        self.sj     = None
        
        self.dlat = self.lats[0] - self.lats[self.nrows]
        self.dlon = abs(self.lons[0] - self.lons[self.ncols])
        
                
    
    def update(self, si, sj):
        self.view = self.data[si:si+self.nrows, sj:sj+self.ncols].view()
        self.si = si
        self.sj = sj
        
    def viewIndex2GlobalIndex(self, i, j):
        """ Converts an i,j index into the data window into an index for the
        same element into the global data. """
        return (self.si + i, self.sj + j)
    
    

class GeoEditor(QMainWindow):
    def __init__(self, parent=None, dwx=160, dwy=160):
        """
        ARGUMENTS:
            dwx, dwy - size of the DataContainer in number of array elements
        """
        super(GeoEditor, self).__init__(parent)
        self.setWindowTitle('GeoEditor (c) Deepak Chandan')
        
        self.dc = DataContainer(dwy, dwx, "data.txt")
        # Set the initial data to the DataContainer class
        self.dc.update(0, 0)
        
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
        self.main_frame.setMinimumSize(QSize(700, 700))
        
        self.dpi = 100
        self.fig = plt.Figure((7, 7), dpi=self.dpi, facecolor='w', edgecolor='w')
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
        self.pixel_slider.setValue(65)
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
        rect = mpatches.Rectangle((self.dc.lons[self.dc.sj], self.dc.lats[self.dc.si+self.dc.nrows]), self.dc.dlat, self.dc.dlon, linewidth=2, facecolor='k')
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
            if (self.cursory == self.dc.nrows-1):
                on_boundary = "down"
            else:
                self.cursory = min(self.dc.nrows-1, self.cursory + 1)
        elif key == Qt.Key_Left:
            if (self.cursorx == 0):
                on_boundary = "left"
            else:
                self.cursorx = max(0, self.cursorx - 1)
        elif key == Qt.Key_Right:
            if (self.cursorx == self.dc.ncols-1):
                on_boundary = "right"
            else:
                self.cursorx = min(self.dc.ncols-1, self.cursorx + 1)
        else:
            return
        
        # if on_boundary:
        #     i, j = self.dc.index_to_ij(self.dc.si)
        #     i, j = self.dc.viewIndex2GlobalIndex(i, j)
        #     m, n = self.dc.nrows, self.dc.ncols
        #     if on_boundary == "top":
        #         i = i-1
        #     elif on_boundary == "down":
        #         i = i+1
        #     elif on_boundary == "left":
        #         j = j-1
        #     elif on_boundary == "right":
        #         j = j+1
        #     _data = self.gd[i:i+m, j:j+n]
        #     self.dc.update(_data.flatten(), self.gd.ij_to_index(i, j))
        
        self.update_cursor_position()
        
    
    
    def update_cursor_position(self, noremove=False):
        if self.cursor and (not noremove): self.cursor.remove()
        _cx, _cy = self.cursorx+0.5, self.cursory+0.5
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
        # self.axes.pcolormesh(self.dc.x, self.dc.y, self.dc.data, cmap=cmap)
        self.axes.pcolor(self.dc.view, cmap=cmap, edgecolors='k', linewidths=0.5)
        # self.axes.imshow(self.dc.view, cmap=cmap, interpolation="nearest")
        
        # Setting the axes limits. This helps in setting the right orientation of the plot
        # and in clontrolling how much extra space we want around the scatter plot.
        tmp1 = self.dc.nrows
        tmp2 = self.dc.ncols
        # I am putting 4% space around the scatter plot
        self.axes.set_ylim([int(tmp1*1.04), 0 - int(tmp1*0.04)])
        self.axes.set_xlim([0 - int(tmp2*0.04), int(tmp2*1.04)])
        self.canvas.draw()
        self.fig.tight_layout()
        self.update_cursor_position(noremove=True)
    
    


    def update_value(self):
        print "text received: {0}".format(self.inputbox.text())
        self.main_frame.setFocus()
    
    
        
    
    def set_information(self, i, j):
        """ Sets the displayed information about the pixel in the right sidebar. 
        ARGUMENTS
            i, j : the local (i.e. DataContainer) 0-based indices for the element
        """
        i_global, j_global = self.dc.viewIndex2GlobalIndex(i, j) # Convert local indices to global indices
        self.latdisplay.setText("Latitude   : {0}".format(self.dc.lats[i_global]))
        self.londisplay.setText("Longitude: {0}".format(self.dc.lons[j_global]))
        self.valdisplay.setText("Value       : {0}".format(self.dc.data[i_global, j_global]))
    
    
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
