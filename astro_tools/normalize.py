import pylab as pl
import numpy as np
from scipy.interpolate import splrep, splev
import os

from fileio import read_spectrum

class Normalizer(object):

    def __init__(self, wave, flux, fig=None, title='', filename='spectrum.spec'):

        if fig is not None:
            self.fig = fig
        else:
            self.fig = pl.get_current_fig_manager().canvas.figure
            
        self.filename = filename

        self.ax1 = pl.subplot(211)
        self.ax2 = pl.subplot(212)

        pl.title(title)

        s = np.where(np.isfinite(flux))
        wave, flux = wave[s], flux[s]

        self.wave, self.flux = wave, flux
        self.continuum = None
        self.fluxnorm = np.ones_like(wave)

        self.spectrum = None
        self.normspectrum = None

        self.xlim = [min(self.wave), max(self.wave)]
        dy = max(self.flux) - min(self.flux)
        self.ylim1 = [min(self.flux) - 0.05*dy, max(self.flux) + 0.05*dy]


        self.fig.canvas.mpl_connect('button_press_event', self.onclick)
        self.fig.canvas.mpl_connect('pick_event', self.onpick)
        self.fig.canvas.mpl_connect('scroll_event', self.onscroll)
        self.fig.canvas.mpl_connect('key_press_event', self.ontype)

        self.ax1.callbacks.connect('xlim_changed', self.on_xlim_change)
        self.ax1.callbacks.connect('ylim_changed', self.on_ylim_change)

    def show(self):
        """
        Shows the plot and starts interactive part
        """

        self.spectrum, = self.ax1.plot(self.wave, self.flux, 'k-', label='spectrum')
        self.normspectrum, = self.ax2.plot(self.wave, self.fluxnorm, 'k-',
                                          label='normspectrum')

        self.ax2.axhline(y=1.0, ls=':', color='k')

        self.ax1.set_xlim(self.xlim)
        self.ax1.set_ylim(self.ylim1)
        self.ax2.set_xlim(self.xlim)

        pl.xlabel('Wavelength')
        pl.ylabel('Flux')
        pl.show()

    def update(self):

        # -- update spectrum
        self.spectrum.set_xdata(self.wave)
        self.spectrum.set_ydata(self.flux)

        self.normspectrum.set_xdata(self.wave)
        self.normspectrum.set_ydata(self.fluxnorm)

    def onclick(self, event):
        # when none of the toolbar buttons is activated and the user clicks in the
        # plot somewhere, compute the median value of the spectrum in a 10angstrom
        # window around the x-coordinate of the clicked point. The y coordinate
        # of the clicked point is not important. Make sure the continuum points
        # `feel` it when it gets clicked, set the `feel-radius` (picker) to 5 points
        toolbar = pl.get_current_fig_manager().toolbar
        if event.button == 1 and toolbar.mode == '':
            window = ((event.xdata - 0.5) <= self.wave) & (self.wave <= (event.xdata + 0.5))
            y = np.median(self.flux[window])
            self.ax1.plot(event.xdata, y, 'rs', ms=10, picker=5, label='cont_pnt')


        # when the user middle clicks:
        # 1. Cycle through the artists in the current axes. If it is a continuum
        #    point, remember its coordinates. If it is the fitted continuum from the
        #    previous step, remove it
        # 2. sort the continuum-point-array according to the x-values
        # 3. fit a spline and evaluate it in the wavelength points
        # 4. plot the continuum
        elif event.button == 2:
            cont_pnt_coord = []
            for artist in self.ax1.get_children():
                if hasattr(artist, 'get_label') and artist.get_label() == 'cont_pnt':
                    cont_pnt_coord.append(artist.get_data())
                elif hasattr(artist, 'get_label') and artist.get_label() == 'continuum':
                    artist.remove()

            cont_pnt_coord = np.array(cont_pnt_coord)[..., 0]
            sort_array = np.argsort(cont_pnt_coord[:, 0])
            x, y = cont_pnt_coord[sort_array].T
            spline = splrep(x, y, k=3)
            self.continuum = splev(self.wave, spline)
            self.ax1.plot(self.wave, self.continuum, 'r-', lw=2, label='continuum')

            self.fluxnorm = self.flux / self.continuum

            self.update()

        pl.draw()


    def onpick(self, event):
        # when the user clicks right on a continuum point, remove it
        if event.mouseevent.button == 3:
            if hasattr(event.artist, 'get_label') and event.artist.get_label() == 'cont_pnt':
                event.artist.remove()


    def onscroll(self, event):
        # move the display sideways when scrolling
        xlim = self.xlim
        dx = xlim[1] - xlim[0]

        if event.button == 'down':
            self.xlim = [xlim[0] + dx / 2, xlim[1] + dx / 2]

        elif event.button == 'up':
            self.xlim = [xlim[0] - dx / 2, xlim[1] - dx / 2]

        # calculate the new y limits:
        window = np.where((self.wave >= self.xlim[0]) & (self.wave <= self.xlim[1]))
        dy = max(self.flux[window]) - min(self.flux[window])

        self.ylim1 = [min(self.flux[window]) - 0.05 * dy, max(self.flux[window]) + 0.05 * dy]

        # only need to set ax1 xlim, ax2 xlim is updated automatically
        self.ax1.set_xlim(self.xlim)

        self.ax1.set_ylim(bottom=self.ylim1[0], top=self.ylim1[1], auto=False)

        pl.draw()

    def on_xlim_change(self, axis):
        self.xlim = axis.get_xlim()
        self.ax2.set_xlim(self.xlim)

    def on_ylim_change(self, axis):
        self.ylim1 = axis.get_ylim()

    def ontype(self, event):
        
        # when the user hits 'n' and a spline-continuum is fitted, normalise the
        # spectrum
        # if event.key == 'n':
        #     continuum = None
        #     for artist in pl.gca().get_children():
        #         if hasattr(artist, 'get_label') and artist.get_label() == 'continuum':
        #             continuum = artist.get_data()[1]
        #             break
        #     if continuum is not None:
        #         pl.cla()
        #         pl.plot(wave, flux / continuum, 'k-', label='normalised')

        # when the user hits 'r': clear the axes and plot the original spectrum
        if event.key == 'r':
            self.ax1.cla()
            self.ax2.cla()
            self.update()

        # when the user hits 'w': if the normalised spectrum exists, write it to a
        # file.
        elif event.key == 'w':
            for artist in pl.gca().get_children():
                if hasattr(artist, 'get_label') and artist.get_label() == 'normspectrum':
                    data = np.array(artist.get_data())
                    np.savetxt(os.path.splitext(self.filename)[0] + '.nspec', data.T)
                    print('Saved to file')
                    break
        pl.draw()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=r"""
      Normalize a spectrum by fitting a spline function to chosen continuum points
      """)
    parser.add_argument("spectrum", type=str,
                        help="The filename of the spectrum (ascii, fits)")

    args, variables = parser.parse_known_args()

    wave, flux = read_spectrum(args.spectrum)

    fig = pl.figure(1, figsize=(18, 8))
    pl.subplots_adjust(left=0.05, right=0.99)

    norm = Normalizer(wave, flux, fig=fig, title=args.spectrum, filename=args.spectrum)
    norm.show()


if __name__ == '__main__':
    main()
