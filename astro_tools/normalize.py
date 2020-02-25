
import pylab as plt
import numpy as np
from scipy.interpolate import splrep,splev
import sys
import os

from astropy.io import fits, ascii

def onclick(event):
   # when none of the toolbar buttons is activated and the user clicks in the
   # plot somewhere, compute the median value of the spectrum in a 10angstrom
   # window around the x-coordinate of the clicked point. The y coordinate
   # of the clicked point is not important. Make sure the continuum points
   # `feel` it when it gets clicked, set the `feel-radius` (picker) to 5 points
   toolbar = plt.get_current_fig_manager().toolbar
   if event.button==1 and toolbar.mode=='':
      window = ((event.xdata-0.5)<=wave) & (wave<=(event.xdata+0.5))
      y = np.median(flux[window])
      plt.plot(event.xdata,y,'rs',ms=10,picker=5,label='cont_pnt')
      
      
   # when the user middle clicks:
   # 1. Cycle through the artists in the current axes. If it is a continuum
   #    point, remember its coordinates. If it is the fitted continuum from the
   #    previous step, remove it
   # 2. sort the continuum-point-array according to the x-values
   # 3. fit a spline and evaluate it in the wavelength points
   # 4. plot the continuum
   elif event.button==2:
      cont_pnt_coord = []
      for artist in plt.gca().get_children():
            if hasattr(artist,'get_label') and artist.get_label()=='cont_pnt':
               cont_pnt_coord.append(artist.get_data())
            elif hasattr(artist,'get_label') and artist.get_label()=='continuum':
               artist.remove()
      cont_pnt_coord = np.array(cont_pnt_coord)[...,0]
      sort_array = np.argsort(cont_pnt_coord[:,0])
      x,y = cont_pnt_coord[sort_array].T
      spline = splrep(x,y,k=3)
      continuum = splev(wave,spline)
      plt.plot(wave,continuum,'r-',lw=2,label='continuum')
      
      
   plt.draw()
   
def onpick(event):
   # when the user clicks right on a continuum point, remove it
   if event.mouseevent.button==3:
      if hasattr(event.artist,'get_label') and event.artist.get_label()=='cont_pnt':
            event.artist.remove()

def onscroll(event):
   # move the display sidways when scrolling
   if event.button=='down':
      xlim = plt.gca().get_xlim()
      dx = xlim[1]-xlim[0]
      plt.gca().set_xlim(xlim[0]+dx/2, xlim[1]+dx/2)
      
   
   elif event.button=='up':
      xlim = plt.gca().get_xlim()
      dx = xlim[1]-xlim[0]
      plt.gca().set_xlim(xlim[0]-dx/2, xlim[1]-dx/2)
      
   plt.draw()
   

def ontype(event):
   

   # when the user hits 'n' and a spline-continuum is fitted, normalise the
   # spectrum
   if event.key=='n':
      continuum = None
      for artist in plt.gca().get_children():
            if hasattr(artist,'get_label') and artist.get_label()=='continuum':
               continuum = artist.get_data()[1]
               break
      if continuum is not None:
            plt.cla()
            plt.plot(wave,flux/continuum,'k-',label='normalised')

   # when the user hits 'r': clear the axes and plot the original spectrum
   elif event.key=='r':
      plt.cla()
      plt.plot(wave,flux,'k-')

   # when the user hits 'w': if the normalised spectrum exists, write it to a
   # file.
   elif event.key=='w':
      for artist in plt.gca().get_children():
            if hasattr(artist,'get_label') and artist.get_label()=='normalised':
               data = np.array(artist.get_data())
               np.savetxt(os.path.splitext(filename)[0]+'.nspec',data.T)
               print('Saved to file')
               break
   plt.draw()

if __name__=='__main__':
   import argparse
   
   parser = argparse.ArgumentParser(description=r"""
   Normalize a spectrum by fitting a spline function to chosen continuum points
   """)
   parser.add_argument("spectrum", type=str,
                     help="The filename of the spectrum (ascii, fits)")

   args, variables = parser.parse_known_args()
   
   filename = args.spectrum
   
   if os.path.splitext(args.spectrum)[1] == '.fits':
      try:
         wave, flux = read_spectrum(args.spectrum)
         print 'standard 1D fits'
      except Exception as e:
         print e
         data = fits.getdata(args.spectrum)
         
         if 'WAVE' in data.dtype.names or 'wave' in data.dtype.names:
            wave = data['WAVE'] # eso DR3
         else:
            wave = data['wavelength']
         
         if 'FLUX' in data.dtype.names or 'flux' in data.dtype.names:
            flux = data['flux']
         else:
            flux = data['FLUX_REDUCED']
         
   elif os.path.splitext(args.spectrum)[1] == '.hdf5':
      wave, flux = hdf5.read_uves(args.spectrum)
      print 'uves hdf5'
   else:
      data = ascii.read(args.spectrum)
      wave, flux = data['col1'], data['col2']
      print 'ascii spectrum'
   
   plt.figure(1, figsize=(18, 6))
   plt.subplots_adjust(left=0.05, right=0.99)
   spectrum, = plt.plot(wave,flux,'k-',label='spectrum')
   plt.title(args.spectrum)

   # Connect the different functions to the different events
   plt.gcf().canvas.mpl_connect('key_press_event',ontype)
   plt.gcf().canvas.mpl_connect('button_press_event',onclick)
   plt.gcf().canvas.mpl_connect('pick_event',onpick)
   plt.gcf().canvas.mpl_connect('scroll_event',onscroll)
   plt.show() # show the window
