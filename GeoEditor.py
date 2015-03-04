"""
GeoEditor.py

This program allows one to edit a 2D latitude-longitude gridded
data pixel for pixel.

Author : Deepak Chandan
Date   : February 17th, 2015
"""

import sys
from netCDF4 import Dataset
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
	DataContainer: The main container class for this application which does the job
	of storing the map and other related data as well as the cursor on this data. 
	"""
	class Cursor(object):
		def __init__(self):
			self.marker = None
			self.x = 0
			self.y = 0


	def __init__(self, nrows, ncols, fname):
		"""
		ARGUMENTS
			nrows - number of rows for the view
			ncols - number of columns for the view
			fname - name of the data file.
		"""
		self.__read_nc_file(fname)
		# self.data = np.loadtxt(fname)
		self.orig_data = np.copy(self.data)
		self.ny, self.nx = self.data.shape
		# self.lons = np.linspace(-179.5,179.5,self.nx)
		# self.lats = np.linspace(89.5,-89.5,self.ny)
				
		
		# Datawindow variables
		self.view   = None        # The array (actually a numpy view) that stores the data to be displayed in the main window
		self.nrows  = nrows       # Number of rows to display in the main windows (the 'view')
		self.ncols  = ncols       # Number of cols to display in the main windows
		self.si     = None        # 0-based row index of the first element 
		self.sj     = None        # 0-based col index of the first element 
		
		self.dlat = self.lats[0] - self.lats[self.nrows]
		self.dlon = abs(self.lons[0] - self.lons[self.ncols])

		# Tracking which elements are changed
		self.longs_grid, self.lats_grid = np.meshgrid(self.lons, self.lats)
		self.modified = np.zeros((self.ny, self.nx))
		
		# A cursor object on the view
		self.cursor = DataContainer.Cursor()
	

	def __read_nc_file(self, fname):
		self.lons = None
		self.lats = None
		ncfile = Dataset(fname, "r", format="NETCDF4")
		for var in ["longitudes", "longitude", "lons"]:
			try:
				self.lons = ncfile.variables[var][:]
			except:
				pass
		# for var in ["lattudes", "laitude", "lts"]:
		# 	try:
		# 		self.lats = ncfile.variables[var][:]
		# 	except:
		# 		pass

		for var in ["latitudes", "latitude", "lats"]:
			try:
				self.lats = ncfile.variables[var][:]
			except:
				pass

		if (self.lats == None) or (self.lons == None):
			ncfile.close()
			QMessageBox.critical(QWidget(), 'Error', "Latitude and or longitude variables not found.", QMessageBox.Ok)
			sys.exit()
			
		self.data = ncfile.variables["data"][:,:]
		ncfile.close()



	def getViewStatistics(self): return (self.view.min(), self.view.max(), self.view.mean())


	def getCursor(self): return self.cursor


	def updateCursorPosition(self, event):
		"""
		Updates the current view in the data window. This function is 
		triggered whenever the user presses the arrow keys. 
		ARGUMENTS
			event - Qt key press event
		"""
		key = event.key()
		on_boundary = None   #This will store which boundary if any we've reached
		if key == Qt.Key_Up:
			self.cursor.y = max(0, self.cursor.y - 1)
		elif key == Qt.Key_Down:
			self.cursor.y = min(self.nrows-1, self.cursor.y + 1)
		elif key == Qt.Key_Left:
			self.cursor.x = max(0, self.cursor.x - 1)
		elif key == Qt.Key_Right:
			self.cursor.x = min(self.ncols-1, self.cursor.x + 1)

	
	def updateView(self, si, sj):
		"""
		Updates the data for the view. 
		ARGUMENTS
			si, sj - the global 0-based i,j indices of the top left corner of the view
		"""
		self.view = self.data[si:si+self.nrows, sj:sj+self.ncols].view()
		self.si = si
		self.sj = sj
		return self.getViewStatistics()
	
	
	def moveView(self, move):
		"""
		Moves the view window over the global dataset in response to the L,R,U,D keys. 
		ARGUMENTS
			move : A Qt key value
		RETURNS
			a tuple with the min, max, and the mean for the new view
		"""
		col_inc = int(self.ncols*0.25)  # Column increment
		row_inc = int(self.nrows*0.25)  # Row increment

		if (move == Qt.Key_L):  # MOVE THE VIEW RIGHT
			new_sj = min(self.nx-self.ncols, self.sj + col_inc)
			return self.updateView(self.si, new_sj)
		elif (move == Qt.Key_H): # MOVE THE VIEW LEFT
			new_sj = max(0, self.sj - col_inc)
			return self.updateView(self.si, new_sj)
		elif (move == Qt.Key_K): # MOVE THE VIEW UP
			new_si = max(0, self.si - row_inc)
			return self.updateView(new_si, self.sj)
		elif (move == Qt.Key_J): # MOVE THE VIEW DOWN
			new_si = min(self.ny-self.nrows, self.si + row_inc)
			return self.updateView(new_si, self.sj)

	
	def modifyValue(self, input):
		"""
		Modify the value fot a particular pixel. The location of the pixel is that
		determined by the current position of the cursor.
		ARGUMENTS
			input - a string containing a float (note: no data validity check is 
					performed on this string)
		"""
		ci, cj = self.viewIndex2GlobalIndex(self.cursor.y, self.cursor.x)
		self.modified[ci, cj] = 1
		self.data[ci, cj] = float(input)



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
		fname = "data.nc"
		super(GeoEditor, self).__init__(parent)
		self.setWindowTitle('GeoEditor - {0}'.format(fname))
		
		#  Creating a variable that contains all the data
		self.dc = DataContainer(dwy, dwx, fname)
		
		self.cursor = self.dc.getCursor()  # Defining a cursor on the data
		self.prvrect = None  # The Rectangle object on the world map

		self.save_fname = None
		self.save_fmt   = None

		self.maps = mpl.cm.datad.keys()  # The names of colormaps available
		self.maps.sort() # Sorting them alphabetically for ease of use

		self.create_menu()
		self.create_main_window()

		self.set_stats_info(self.dc.updateView(0, 0))  # Set the initial view for the data container class

		self.draw_preview_worldmap()
		self.render_view()
		self.statusBar().showMessage('GeoEditor 2015')
	
	
	def keyPressEvent(self, e):
		if e.key() == Qt.Key_E:
			# Pressing e for edit
			self.inputbox.setFocus()
		elif e.key() == Qt.Key_C:
			self.colormaps.setFocus()
		elif e.key() == Qt.Key_Escape:
			# Pressing escape to refocus back to the main frame
			self.main_frame.setFocus()
		elif e.key() in [Qt.Key_H, Qt.Key_J, Qt.Key_K, Qt.Key_L]:
			self.set_stats_info(self.dc.moveView(e.key()))
			self.render_view()
			self.draw_preview_rectangle()
		else:
			self.dc.updateCursorPosition(e)
			self.draw_cursor()
	
	
	def create_main_window(self):
		"""
		This function creates the main window of the program. 
		"""
		self.main_frame = QWidget()
		self.main_frame.setMinimumSize(QSize(700, 700))
		
		self.dpi = 100
		self.fig = plt.Figure((6, 6), dpi=self.dpi, facecolor='w', edgecolor='w')
		self.canvas = FigureCanvas(self.fig)
		self.canvas.setParent(self.main_frame)
		
		
		self.preview_frame = QWidget()
		self.preview_fig = plt.Figure((3, 1.5), dpi=self.dpi, facecolor='w', edgecolor='w')
		self.preview = FigureCanvas(self.preview_fig)
		self.preview.setParent(self.preview_frame)
		self.preview_axes = self.preview_fig.add_subplot(111)
		# self.preview_axes.get_xaxis().set_visible(False)
		# self.preview_axes.get_yaxis().set_visible(False)
		
		self.preview_fig.canvas.mpl_connect('button_press_event', self.onclick)
		
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
		font = QFont("SansSerif", 14)

		# STATISTICS >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
		self.statdisplay = QLabel("Statistics:")
		self.statgrid    = QGridLayout()
		self.statgrid.setSpacing(5)
		w = QLabel("Local"); w.setFont(font)
		self.statgrid.addWidget(w,  1, 1, Qt.AlignCenter)
		w = QLabel("Global"); w.setFont(font)
		self.statgrid.addWidget(w, 1, 2, Qt.AlignCenter)

		for i, name in enumerate(["Minimum", "Maximum", "Mean"]):
			w = QLabel(name)
			w.setFont(font)
			self.statgrid.addWidget(w, i+2, 0, Qt.AlignLeft)

		self.statsarray = []
		for i in range(6): self.statsarray.append(QLabel(''))

		self.statsarray[3].setText("{0:5.2f}".format(self.dc.data.min()))
		self.statsarray[4].setText("{0:5.2f}".format(self.dc.data.max()))
		self.statsarray[5].setText("{0:5.2f}".format(self.dc.data.mean()))

		for i in range(3):
			self.statgrid.addWidget(self.statsarray[i], i+2, 1, Qt.AlignCenter)
			self.statgrid.addWidget(self.statsarray[i+3], i+2, 2, Qt.AlignCenter)
			self.statsarray[i].setFont(font)
			self.statsarray[i+3].setFont(font)

		# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

		# PIXEL INFO >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

		self.infodisplay = QLabel("Pixel Information:")
		self.infogrid    = QGridLayout()
		self.infogrid.setSpacing(5)

		for i, name in enumerate(["Latitude", "Longitude", "Value"]):
			w = QLabel(name)
			w.setFont(font)
			self.infogrid.addWidget(w, i+1, 0, Qt.AlignLeft)

		self.latdisplay  = QLabel("")
		self.londisplay  = QLabel("")
		self.valdisplay  = QLabel("")
		for i,w in enumerate([self.latdisplay, self.londisplay, self.valdisplay]):
			self.infogrid.addWidget(w, i+1, 1, Qt.AlignLeft)
		# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

		
		# Colorscheme selector
		cmap_label = QLabel('Colorscheme:')
		self.colormaps = QComboBox(self)
		self.colormaps.addItems(self.maps)
		self.colormaps.setCurrentIndex(self.maps.index('Spectral'))
		self.colormaps.currentIndexChanged.connect(self.render_view)

		# New value editor
		hbox = QHBoxLayout()
		w = QLabel("Enter new value: ")
		w.setFont(font)
		hbox.addWidget(w)
		self.inputbox = QLineEdit()
		self.inputbox.returnPressed.connect(self.update_value)
		hbox.addWidget(self.inputbox)

		for item in [self.statdisplay, self.infodisplay, self.latdisplay, self.londisplay, self.valdisplay, cmap_label]:
			item.setFont(font)

		
		vbox = QVBoxLayout()
		vbox.addWidget(self.canvas)
		
		
		vbox2 = QVBoxLayout()
		vbox2.addWidget(self.preview)
		
		vbox2.addWidget(self.statdisplay)
		vbox2.setAlignment(self.statdisplay, Qt.AlignTop)
		vbox2.addLayout(self.statgrid)

		vbox2.addWidget(self.infodisplay)
		vbox2.setAlignment(self.infodisplay, Qt.AlignTop)
		vbox2.addLayout(self.infogrid)

		# vbox2.addWidget(self.inputbox, Qt.AlignTop)
		vbox2.addLayout(hbox, Qt.AlignTop)

		vbox2.addStretch(1)
		vbox2.addWidget(cmap_label)
		vbox2.addWidget(self.colormaps)
		vbox2.addStretch(1)
			
		
		hbox = QHBoxLayout()
		hbox.addLayout(vbox)
		hbox.addLayout(vbox2)
		
		self.main_frame.setLayout(hbox)
		self.setCentralWidget(self.main_frame)
		self.main_frame.setFocus()
	
	
	def draw_preview_worldmap(self):
		"""
		This function draws the world map in the preview window on the top right hand corner 
		of the application.
		"""
		m = Basemap(projection='cyl', lon_0=0, llcrnrlat=-90,urcrnrlat=90,\
			llcrnrlon=-180,urcrnrlon=180,resolution='c', ax=self.preview_axes)
		m.drawcoastlines(linewidth=0.5)
		self.preview_axes.set_xlim([-180,180])
		self.preview_axes.set_ylim([-90,90])
		self.draw_preview_rectangle()
		self.preview_fig.tight_layout()
	
	
	def draw_preview_rectangle(self):
		"""
		This function draws the Rectangle, which indicates the current region being shown
		in the view, in the preview window.
		"""
		# If a rectangle object exists, then remove it before drawing a new one
		if self.prvrect: self.prvrect.remove()

		rect_llc_col = self.dc.lons[self.dc.sj]
		rect_llc_row = self.dc.lats[min(self.dc.si+self.dc.nrows-1, self.dc.ny-1)]
		# print self.dc.si+self.dc.nrows-1, self.dc.ny-1
		# TODO: Change the value of dlon and dlat 

		self.prvrect = mpatches.Rectangle((rect_llc_col, rect_llc_row), 
						   self.dc.dlon, self.dc.dlat, 
						   linewidth=1, facecolor='g', alpha=0.3)


		self.preview_axes.add_patch(self.prvrect)
		self.preview.draw()
		
	
	def draw_cursor(self, noremove=False):
		if self.cursor.marker and (not noremove): self.cursor.marker.remove()
		# The increment by 0.5 below is done so that the center of the marker is shifted 
		# so that the top left corner of the square marker conicides with the top right corner
		# of each pixel. The value of 0.5 comes simply because each pixel are offset by 1 in each dimension.
		_cx, _cy = self.cursor.x+0.5, self.cursor.y+0.5
		self.cursor.marker = self.axes.scatter(_cx, _cy, s=65, 
							 marker='s', edgecolor="k", facecolor='none', linewidth=2)  
		self.set_information(_cy, _cx)        
		self.canvas.draw()
		
	
	
	def render_view(self):
		self.axes.clear()
		cmap = mpl.cm.get_cmap(self.maps[self.colormaps.currentIndex()])
		# self.axes.pcolor(self.dc.view, cmap=cmap, edgecolors='w', linewidths=0.5, vmin=self.dc.dmin, vmax=self.dc.dmax)
		self.axes.pcolor(self.dc.view, cmap=cmap, edgecolors='w', linewidths=0.5)
		
		# Setting the axes limits. This helps in setting the right orientation of the plot
		# and in clontrolling how much extra space we want around the scatter plot.
		tmp1 = self.dc.nrows
		tmp2 = self.dc.ncols
		# I am putting 4% space around the scatter plot
		self.axes.set_ylim([int(tmp1*1.02), 0 - int(tmp1*0.02)])
		self.axes.set_xlim([0 - int(tmp2*0.02), int(tmp2*1.02)])
		self.canvas.draw()
		self.fig.tight_layout()
		self.draw_cursor(noremove=True)
	
	


	def update_value(self):
		inp = self.inputbox.text()   # Get the value in the text box
		self.dc.modifyValue(inp)     # Modify the data array
		self.set_stats_info(self.dc.getViewStatistics()) 
		self.inputbox.clear()        # Now clear the input box
		self.render_view()           # Render the new view (which now contains the updated value)
		self.main_frame.setFocus()   # Bring focus back to the view
	
	
		
	
	def set_information(self, i, j):
		""" Sets the displayed information about the pixel in the right sidebar. 
		ARGUMENTS
			i, j : the local (i.e. DataContainer) 0-based indices for the element
		"""
		i_global, j_global = self.dc.viewIndex2GlobalIndex(i, j) # Convert local indices to global indices
		self.latdisplay.setText("{0}".format(self.dc.lats[i_global]))
		self.londisplay.setText("{0}".format(self.dc.lons[j_global]))
		self.valdisplay.setText("{0}".format(self.dc.data[i_global, j_global]))
	

	def set_stats_info(self, s):
		"""
		Updates the statistics display panel with the stats for the view.
		ARGUMENTS
			s - a tuple with the min, max and mean of the view
		"""
		self.statsarray[0].setText("{0:5.2f}".format(s[0]))
		self.statsarray[1].setText("{0:5.2f}".format(s[1]))
		self.statsarray[2].setText("{0:5.2f}".format(s[2]))


	def onclick(self, event):
		# 1. Get the global row, column indices of the point where mouse was clicked
		print event.xdata, event.ydata
		if (event.xdata == None) or (event.ydata == None): return
		px = np.where(abs(self.dc.lons - event.xdata) < 0.5)[0][0]
		py = np.where(abs(self.dc.lats - event.ydata) < 0.5)[0][0]
		# print px, py
		# 2. Update the view data array 
		self.set_stats_info(self.dc.updateView(py, px))
		# 3. Render the view
		self.render_view()
		# 4. Set the cursor to be at the top-left corner
		self.cursor.x = 0
		self.cursor.y = 0
		# 5. Draw the cursor
		self.draw_cursor()
		# 6. Update the preview 
		self.draw_preview_rectangle()

	
	def on_about(self):
		msg = """ Edit 2D geophysical field.  """
		QMessageBox.about(self, "About", msg.strip())
	
	
	def save_data(self):
		"""
		Saves the data array to a text file. It first opens a window to allow the user to select the
		save filename, and then prompts the user to enter a numpy save format. It remembers these 
		information so further calls to save do not prompt for this information. 
		"""
		file_choices = "Text files (*.txt)"
		if not self.save_fname:
			self.save_fname = unicode(QFileDialog.getSaveFileName(self, 'Save File', '', file_choices))
			fmt, ok = QInputDialog().getText(self, 'Output format', "Numpy save format:", text="%5.2f")
			self.save_fmt = str(fmt)
			if (not ok):
				self.statusBar().showMessage('Save cancelled', 2000)
				self.save_fname = None
				return
		np.savetxt(self.save_fname, self.dc.data, fmt=self.save_fmt)
		self.statusBar().showMessage('Saved to %s' % self.save_fname, 2000)

	
	
	def create_action(self, text, slot=None, shortcut=None, 
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
		
		load_file_action = self.create_action("&Save Data",
			shortcut="Ctrl+S", slot=self.save_data, 
			tip="Save the data array")
		
		self.add_actions(self.file_menu, (load_file_action,))

		self.help_menu = self.menuBar().addMenu("&Help")
		about_action = self.create_action("&About", 
			shortcut='F1', slot=self.on_about, 
			tip='About GeoEditor')
		self.add_actions(self.help_menu, (about_action,))


	def closeEvent(self, event):
		reply = QMessageBox.question(self, 'Message', "There are unsaved changes. Are you sure you want to quit?", 
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

		if reply == QMessageBox.Yes:
			event.accept()
		else:
			event.ignore()

	
	
def main():
	app = QApplication(sys.argv)
	mw = GeoEditor(dwx=50,dwy=50)
	mw.show()     # Render the window
	mw.raise_()   # Bring the PyQt4 window to the front
	app.exec_()   # Run the application loop


if __name__ == "__main__":
	main()
