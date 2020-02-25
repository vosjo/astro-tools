import numpy as np
import pylab as pl

from ivs.spectra import linelists
from ivs.spectra import tools as stools

from fileio import read_spectrum

class SFI(object):
    """
      Interactive matplotlib plot to fit a gaussian profile to a spectral line.
      Will return the radial velocity and its error upon closing.

      Call as:
      >>> fig = pl.figure(1)
      >>> lf = LineFitter(wave, flux, fig=fig, line=4685.71)
      >>> rv, err = lf.show()

      Usage:

      When calling LineFitter you need to provide the wavelengt, flux, figure to plot in,
      and the central wavelength of the line to fit (fx. 4685.71 AA for HeII 4685)

      There are two modes to select boundaries
         Fit: set boundaries for the gaussian fit (green lines)
         Noise: set boundaries for the determination of the noise (black lines)
      Switch between the modes using the 'n' key.
      The mode is shown in top right corner

      To rebin the spectrum to improve selection of boundaries press r, and in the
      terminal enter the binsize. All other operations will still be performed on
      the original spectrum, but will be shown on the rebined spectrum.

      To fit the line:
      select fit mode
      click left mouse button to set left boundary
      click right mouse button to set right boundary
      press 'f' key to fit gaussian (parameters are shown in terminal)

      To determine error:
      select noise mode
      click left and right to set boundaries for a part of the continuum to determine the noise
      press 'm' key to start monte carlo simulation.
      final error will be shown in terminal

      To exit and return rv and error to the main script press enter.
     """

    def __init__(self, wave, flux, teff=5500, logg=4.5, binsize=1, vrad=0, fig=None, title=''):
        """
         Create the LineFitter object

         :parameter array wave: wavelength array of spectrum to fit
         :parameter array flux: flux array of spectrum to fit (can be normalised or not)
         :parameter float line: central wavelength of the line to fit (AA)
         :parameter int binsize: Automatically rebin provided spectra to this binsize
         :parameter object fig: mpl figure to use, optional
         :parameter str title: Title of the plot, optional
         :return: instantiated :class:`LineFitter` object
        """

        if fig != None:
            self.fig = fig
        else:
            self.fig = pl.get_current_fig_manager().canvas.figure

        pl.title(title)

        s = np.where(np.isfinite(flux))
        wave, flux = wave[s], flux[s]

        self.wave_, self.flux_ = wave, flux
        self.wave, self.flux = stools.rebin_spectrum(wave, flux, binsize)
        self.wave = stools.doppler_shift(self.wave, vrad, vrad_units='km/s')

        self.binsize = binsize
        self.vrad = vrad

        self.teff = teff
        self.logg = logg

        self.lines = np.empty((0,), dtype=[('wavelength', 'f8'), ('depth', 'f8'), ('ion', 'a7')])

        self.zoom = 0.5

        self.fig.canvas.mpl_connect('button_press_event', self.onClick)
        self.fig.canvas.mpl_connect('scroll_event', self.onScroll)
        self.fig.canvas.mpl_connect('key_press_event', self.onKey)

        # -- remove default key binding for f
        pl.rcParams['keymap.fullscreen'] = [u'ctrl+f'],

    def show(self):
        """
        Shows the plot and starts interactive part

        :return: (float, float): the radial velocity and error.
        """

        self.spectrum = pl.plot(self.wave, self.flux, '-b')[0]

        self.line_annotations = []

        # set boundaries
        dx = np.max(self.wave) - np.min(self.wave)
        dy = np.max(self.flux) - np.min(self.flux)
        pl.xlim([np.min(self.wave), np.max(self.wave)])
        pl.ylim([np.min(self.flux) - 0.05 * dy, np.max(self.flux) + 0.05 * dy])

        pl.xlabel('Wavelength')
        pl.ylabel('Flux')
        pl.show()

        return None

    def update_figure(self):
        """
        Internal method
        Update the plot
        """

        # -- update spectrum
        self.spectrum.set_xdata(self.wave)
        self.spectrum.set_ydata(self.flux)

        if len(self.lines) > len(self.line_annotations):
            ax = pl.gca()
            trans = ax.get_xaxis_transform()  # x in data untis, y in axes fraction
            for l in self.lines[len(self.line_annotations):]:
                w = l['wavelength']
                y1 = self.flux[(self.wave >= w)][0]
                y2 = np.average(self.flux[(self.wave > w - 2) & (self.wave < w + 2)]) * 1.1
                an = ax.annotate('{} - {:0.2f}'.format(l['ion'], l['depth']),
                                 xy=(w, y1), xycoords='data',
                                 xytext=(w, 1.01), textcoords=trans,
                                 rotation='vertical',
                                 va='bottom', ha='center',
                                 arrowprops=dict(arrowstyle="->",
                                                 connectionstyle="arc3"),
                                 )
                self.line_annotations.append(an)

        pl.draw()

    def get_lines(self, wave):
        """
        Get the spectral line information and add to figure
        """

        lines = linelists.get_lines(teff=self.teff, logg=self.logg, wrange=(wave - 1, wave + 1),
                                    blend=0.1, return_name=True)

        self.lines = np.hstack([self.lines, lines])

    def onClick(self, event=None):
        """
        Event handler for mouse clicks
        """

        if event.inaxes and self.fig.canvas.toolbar.mode == '':
            x, y = event.xdata, event.ydata
            axes = event.inaxes

            if event.button == 1:
                # load lines
                self.get_lines(event.xdata)

        self.update_figure()

    def onScroll(self, event=None):
        """
        Event handler for mouse clicks
        """
        if event.inaxes:
            x, y = event.xdata, event.ydata
            axes = event.inaxes

            if event.button == 'up':
                # zoom in
                zoom = 1.0 - self.zoom
                xleft = (x - axes.get_xlim()[0]) * zoom
                xright = (axes.get_xlim()[1] - x) * zoom

                window = np.where((self.wave >= x - xleft) & (self.wave <= x + xright))
                yup = np.max(self.flux[window])
                ydown = np.min(self.flux[window])
                dy = (yup - ydown)

                axes.set_xlim([x - xleft, x + xright])
                axes.set_ylim([ydown - dy * 0.05, yup + dy * 0.1])

            if event.button == 'down':
                # Zoom out
                zoom = 1.0 / (1.0 - self.zoom)
                xleft = (x - axes.get_xlim()[0]) * zoom
                xright = (axes.get_xlim()[1] - x) * zoom
                yup = (axes.get_ylim()[1] - y) / (axes.get_ylim()[1] - axes.get_ylim()[0])
                ydown = (y - axes.get_ylim()[0]) / (axes.get_ylim()[1] - axes.get_ylim()[0])

                xlim = [x - xleft, x + xright]
                xmin, xmax = self.get_xdata_limits(axes)
                dx = (xmax - xmin) * 0.05
                if xlim[0] < xmin - dx:
                    xlim[0] = xmin - dx
                if xlim[1] > xmax + dx:
                    xlim[1] = xmax + dx
                axes.set_xlim(xlim)

                ymin, ymax = self.get_visble_ylim(axes)
                dy = (ymax - ymin) * 1.05
                ylim = [y - dy * ydown, y + dy * yup]

                ymin, ymax = self.get_ydata_limits(axes)
                dy = (ymax - ymin) * 0.05

                if ylim[0] < ymin - dy:
                    ylim[0] = ymin - dy
                if ylim[1] > ymax + dy:
                    ylim[1] = ymax + dy
                axes.set_ylim(ylim)

            pl.draw()

    def get_visble_ylim(self, axes, xlim=None):
        """ Return the minimum and maximum of the visible y-values """
        if xlim == None:
            xlim = axes.get_xlim()

        ymin, ymax = [], []
        lines = axes.get_lines()
        for line in lines:
            x = line.get_xdata()
            y = line.get_ydata()
            y = y[(x >= xlim[0]) & (x <= xlim[1])]
            if len(y) > 0:
                ymin.append(np.nanmin(y))
                ymax.append(np.nanmax(y))

        return np.min(ymin), np.max(ymax)

    def get_xdata_limits(self, axes):
        """ Return the minimum and maximum of the x-values """
        lines = axes.get_lines()
        xmin, xmax = [], []
        for line in lines:
            x = line.get_xdata()
            xmin.append(np.nanmin(x))
            xmax.append(np.nanmax(x))
        return np.nanmin(xmin), np.nanmax(xmax)

    def get_ydata_limits(self, axes):
        """ Return the minimum and maximum of the y-values """
        lines = axes.get_lines()
        ymin, ymax = [], []
        for line in lines:
            y = line.get_ydata()
            ymin.append(np.nanmin(y))
            ymax.append(np.nanmax(y))
        return np.nanmin(ymin), np.nanmax(ymax)

    def onKey(self, event=None):
        """
        Event handler for key strokes
        """
        if event.key == 'r':
            # Rebin the spectrum to given factor

            binsize = input("Input new binsize for rebinning: ")
            try:
                binsize = int(binsize)
                self.wave, self.flux = stools.rebin_spectrum(self.wave_, self.flux_, binsize)
                self.wave = stools.doppler_shift(self.wave, self.vrad, vrad_units='km/s')
                self.binsize = binsize
                self.update_figure()
            except Exception, e:
                print e
                print "Could not rebin spectrum"

        if event.key == 'v':
            # Change the radial velocity shift

            vrad = input("Input new radial velocity shift: ")
            try:
                vrad = int(vrad)
                self.wave, self.flux = stools.rebin_spectrum(self.wave_, self.flux_, self.binsize)
                self.wave = stools.doppler_shift(self.wave, vrad, vrad_units='km/s')
                self.vrad = vrad
                self.update_figure()
            except Exception, e:
                print e
                print "Could not shift spectrum"

        if event.key == 'enter':
            pl.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(description=r"""
   Program to interactively identify spectral lines.
   Author: Joris Vos
   """)
    parser.add_argument("spectrum", type=str,
                        help="The filename of the spectrum (ascii, fits)")
    parser.add_argument("-bin", type=int, dest='binsize', default=1,
                        help="binsize for rebinning (default=1)")
    parser.add_argument("-vrad", type=float, dest='vrad', default=0,
                        help="radial velocity of the spectrum (default=0)")
    parser.add_argument("-teff", type=float, dest='teff', default=6000,
                        help="Effective temperature of the star (default=6000)")
    parser.add_argument("-logg", type=float, dest='logg', default=0,
                        help="surface gravity of the star (default=4.5)")
    args, variables = parser.parse_known_args()

    wave, flux = read_spectrum(args.spectrum)

    fig = pl.figure(1, figsize=(14, 5.2))
    pl.subplots_adjust(left=0.07, top=0.85, right=0.99, bottom=0.09)
    sf = SFI(wave, flux, fig=fig, vrad=args.vrad, binsize=args.binsize,
             teff=args.teff, logg=args.logg)
    sf.show()


if __name__ == '__main__':
    main()
