# wdc_classification.py
"""
Description: This file contains a set of python functions for conducting
machine learning classification on remote sensing data contained in an
Open Data Cube instance.
License: The code in this notebook is licensed under the Apache License,
Version 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
Contact: If you need assistance, please contact Richard Lucas or
Carole Planque from Aberystwyth University.
Last modified: May 2021
"""
# import os
# import sys
# import joblib
# import datacube
# import rasterio
# import numpy as np
# import pandas as pd
# import xarray as xr
# import time
# from tqdm.auto import tqdm
# import dask.array as da
# import geopandas as gpd
# from copy import deepcopy
# import multiprocessing as mp
# import dask.distributed as dd
# import matplotlib.pyplot as plt
# from sklearn.cluster import KMeans
# from sklearn.utils import check_random_state
# from abc import ABCMeta, abstractmethod
# from datacube.utils import geometry
# from sklearn.base import ClusterMixin
# from dask.diagnostics import ProgressBar
# from rasterio.features import rasterize
# from dask_ml.wrappers import ParallelPostFit
# from sklearn.mixture import GaussianMixture
# from datacube.utils.geometry import assign_crs
# from sklearn.cluster import AgglomerativeClustering
# from sklearn.model_selection import KFold, ShuffleSplit
# from sklearn.model_selection import BaseCrossValidator

import warnings
from rasterstats import zonal_stats
import numpy as np


def collect_training_data(data, shpFile=None, affine=None, method='median'):
    """
    Collect values from one or multiple numpy.ndarray(s) for
    each feature of a shape file and return a median values
    Last modified: August 2021
    
    Parameters
    ----------
    data : a list of one or multiple numpy.ndarray(s). Required.
            The numpy.ndarray(s) must have a dimension ('y','x').
            Order of dimensions is important as can be affected
            latter on by the flattening (training step).
    shpFile : filename of the shapefile containing the training
            areas (i.e., polygons). Required.
    affine : affine of the raster (rasterio python library). Required.
            Must have the following format : Affine(a, b, c, d, e, f), with
            a = width of a pixel
            b = row rotation (typically zero)
            c = x-coordinate of the upper-left corner of the upper-left pixel
            d = column rotation (typically zero)
            e = height of a pixel (typically negative)
            f = y-coordinate of the of the upper-left corner of the upper-left pixel
    method : a string with the statistic method to use when
            collecting numpy.ndarray's values. By default median value will be
            returned for each polygon feature.
        
    Returns
    -------
    training_data : a numpy.ndarray object of dimension ('X','Y')
        where 'X' is the number of samples (i.e., number of
        features in shp) and 'Y' the length of the 'data' list
        
    """
    
    def _extract_val(val):
        return val[method]
    

    if shpFile is None:
        
        raise ValueError("Filename of a polygon shapefile is required.")

    elif affine is None:
        
        raise ValueError("'affine' has to be Affine(a, b, c, d, e, f) format. "
                         "Please refer to the function documentation \n"
                         "for detailed information.")

    elif method not in ['min', 'max', 'median', 'mean', 'sum', 'std']:
        
        raise ValueError(f"'{method}' is not a valid option for "
                            "`method`. Please specify either \n"
                            "'min', 'max', 'median', 'mean' ,"
                            "'sum', or 'std'. If left empty, "
                            "'median' will be used.")

    elif isinstance(data, list):
        
        if type(data[0]) != np.ndarray:
            raise ValueError(f"Your input data is not a list of numpy.ndarray(s). \n"
                            "Input data has to be a list of one "
                            "or multiple numpy.ndarray(s). \nPlease refer to "
                            "the function documentation to verify your parameters \n"
                            "meet all the format requirements.")
    
        training_data = []
        
        for array in data:
            zs = zonal_stats(shpFile, array, affine=affine , stats=[method])
            training_data.append(list(map(_extract_val, zs)))
        training_data = np.transpose(np.asarray(training_data))

    else:
        
        raise ValueError(f"Verify that your input data is a list of "
                         "one or multiple numpy.ndarray(s). \nPlease refer to "
                         "the function documentation to verify your parameters \n"
                         "meet all the format requirements.")

    return training_data