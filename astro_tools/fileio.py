
import os

from ivs.io import ascii, hdf5

from astropy.io import fits, ascii


def read_1d_fits_spectrum(filename):
    """
    Function to read a 1D spectrum,
    will return the wavelength and flux as numpy arrays.
    """
    hdu = fits.open(filename, mode='readonly')

    header = hdu[0].header
    data = hdu[0].data

    if len(hdu[0].data.shape) == 2:
        data = hdu[0].data[0]

    if len(hdu[0].data.shape) == 3:
        data = hdu[0].data[0][0]

    data = data.flatten()

    flux = data
    dnu = float(header["CDELT1"]) if 'CDELT1' in header else header['CD1_1']
    nu_0 = float(header["CRVAL1"])  # the first wavelength value
    nu_n = nu_0 + (len(flux) - 1) * dnu
    wave = np.linspace(nu_0, nu_n, len(flux))

    if ('CTYP1' in header and 'log' in header['CTYP1']) or \
            ('CTYPE1' in header and 'log' in header['CTYPE1']):
        wave = np.exp(wave)

    return wave, flux


def read_spectrum(filename):

    if os.path.splitext(filename)[1] == '.fits':
        try:
            wave, flux = read_1d_fits_spectrum(filename)
            print 'standard 1D fits'
        except Exception as e:
            print e
            data = fits.getdata(filename)

            if 'WAVE' in data.dtype.names or 'wave' in data.dtype.names:
                wave = data['WAVE']  # eso DR3
            else:
                wave = data['wavelength']

            if 'FLUX' in data.dtype.names or 'flux' in data.dtype.names:
                flux = data['flux']
            else:
                flux = data['FLUX_REDUCED']

    elif os.path.splitext(filename)[1] == '.hdf5':
        wave, flux = hdf5.read_uves(filename)
        print 'uves hdf5'
    else:
        data = ascii.read(filename)
        wave, flux = data['col1'], data['col2']
        print 'ascii spectrum'

    return wave, flux
