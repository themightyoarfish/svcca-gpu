# MODIFICATION NOTICE AS PER §4 B) OF THE APACHE LICENSE, VERSION 2.0
# THIS FILE WAS MODIFIED

import pandas as pd
import svcca.cca_core as cca_core
import svcca.linalg as linalg


def fft_resize(images, resize=False, new_size=None):
    '''Function for applying DFT and resizing.

    This function takes in an array of images, applies the 2-d fourier transform
    and resizes them according to new_size, keeping the frequencies that overlap
    between the two sizes.

    Args:
        images: a numpy array with shape
                [batch_size, height, width, num_channels]
        resize: boolean, whether or not to resize
        new_size: a tuple (size, size), with height and width the same

    Returns:
        im_fft_downsampled: a numpy array with shape
                            [batch_size, (new) height, (new) width, num_channels]
    '''
    assert len(images.shape) == 4, ('expecting images to be'
                                    '[batch_size, height, width, num_channels]')

    im_fft = linalg.fft2(images, axes=(1, 2))

    # resizing images
    if resize:
        # get fourier frequencies to threshold
        assert (im_fft.shape[1] == im_fft.shape[2]), ('Need images to have same' 'height and width')
        # downsample by threshold
        width = im_fft.shape[2]
        new_width = new_size[0]
        freqs = linalg.fftfreq(width, d=1.0 / width)
        idxs = linalg.flatnonzero((freqs >= -new_width / 2.0) & (freqs < new_width / 2.0))
        im_fft_downsampled = im_fft[:, :, idxs, :][:, idxs, :, :]

    else:
        im_fft_downsampled = im_fft

    return im_fft_downsampled


def fourier_ccas(conv_acts1, conv_acts2, return_coefs=False,
                 compute_dirns=False, verbose=False):
    '''Computes cca similarity between two conv layers with DFT.

    This function takes in two sets of convolutional activations, conv_acts1,
    conv_acts2, after resizing the spatial dimensions to be the same, applies fft
    and then computes the ccas.

    Finally, it applies the inverse fourier transform to get the CCA directions
    and neuron coefficients.

    Args:
        conv_acts1: numpy array with shape [batch_size, height1, width1, num_channels1]
        conv_acts2: numpy array with shape [batch_size, height2, width2, num_channels2]
        compute_dirns: boolean, used to determine whether results also contain actual cca
                       directions.

    Returns:
        all_results: a pandas dataframe, with cca results for every spatial
                     location. Columns are neuron coefficients (combinations
                     of neurons that correspond to cca directions), the cca
                     correlation coefficients (how well aligned directions
                     correlate) x and y idxs (for computing cca directions
                     on the fly if compute_dirns=False), and summary
                     statistics. If compute_dirns=True, the cca directions
                     are also computed.
    '''
    height1, width1 = conv_acts1.shape[1], conv_acts1.shape[2]
    height2, width2 = conv_acts2.shape[1], conv_acts2.shape[2]
    if height1 != height2 or width1 != width2:
        height   = min(height1, height2)
        width    = min(width1, width2)
        new_size = [height, width]
        resize   = True
    else:
        height   = height1
        width    = width1
        new_size = None
        resize   = False

    # resize and preprocess with fft
    fft_acts1 = fft_resize(conv_acts1, resize=resize, new_size=new_size)
    fft_acts2 = fft_resize(conv_acts2, resize=resize, new_size=new_size)

    # loop over spatial dimensions and get cca coefficients
    all_results = pd.DataFrame()
    for i in range(height):
        for j in range(width):
            results_dict = cca_core.get_cca_similarity(
                fft_acts1[:, i, j, :].T,
                fft_acts2[:, i, j, :].T,
                compute_dirns=compute_dirns,
                verbose=verbose
            )

            # apply inverse FFT to get coefficients and directions if specified
            if return_coefs:
                results_dict['neuron_coeffs1'] = linalg.ifft2(
                    results_dict['neuron_coeffs1'])
                results_dict['neuron_coeffs2'] = linalg.ifft2(
                    results_dict['neuron_coeffs2'])
            else:
                del results_dict['neuron_coeffs1']
                del results_dict['neuron_coeffs2']

            if compute_dirns:
                results_dict['cca_dirns1'] = linalg.ifft2(results_dict['cca_dirns1'])
                results_dict['cca_dirns2'] = linalg.ifft2(results_dict['cca_dirns2'])

            # accumulate results
            results_dict['location'] = (i, j)
            all_results = all_results.append(results_dict, ignore_index=True)

    return all_results
