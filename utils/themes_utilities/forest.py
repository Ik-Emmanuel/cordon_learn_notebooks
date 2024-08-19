## dea_bandindices.py
'''
Description: This file contains a set of python functions for computing
remote sensing flood mapping on WDC data.
'''
import xarray as xr
import numpy as np
import scipy.ndimage as ndimage
from time import time as time


def get_year(string):
    year = string.split("_")[1]
    return int(year)

# Define custom functions
def select_forest_site(site_index):
    """
    Takes a site index and returns its coordinates with EPSG:27700.  
    Last modified: June 2022
    
    Parameters
    ----------
    site_index : integer between 1 and 4 or string from sites_label dictionary 

    """
    sites_label = {1: {"area": "Cefn Fannog", 
                       "min_x_27700": 280400,
                       "min_y_27700": 251900, 
                       "max_x_27700": 284040, 
                       "max_y_27700": 255080},
                   2: {"area": "Esgair Gelli",
                        "min_x_27700": 277600,
                        "min_y_27700": 254000,
                        "max_x_27700": 281000,
                        "max_y_27700": 257750},
                   "cefn fannog": {"area": "Cefn Fannog", 
                       "min_x_27700": 280400,
                       "min_y_27700": 251900, 
                       "max_x_27700": 284040, 
                       "max_y_27700": 255080},
                   "esgair gelli": {"area": "Esgair Gelli",
                        "min_x_27700": 277600,
                        "min_y_27700": 254000,
                        "max_x_27700": 281000,
                        "max_y_27700": 257750},
                  }
    
    print("Chosen area: " + sites_label[site_index]["area"])
    
    return(sites_label[site_index]["min_x_27700"], sites_label[site_index]["min_y_27700"], 
            sites_label[site_index]["max_x_27700"], sites_label[site_index]["max_y_27700"])

def query_site_period(extent, start_date, end_date):
    """
    Takes extent and period of interest and return query dictionary for datacube load.  
    Last modified: June 2022
    
    Parameters
    ----------
    extent : tuple with (min_x, min_y, max_x, max_y) in EPSG: 27700
    start_date : str with format 'YYYY-MM-DD'
    end_date : str with format 'YYYY-MM-DD'
    """    
    from pyproj import Proj, transform
    
    training_inProj = Proj(init='EPSG:27700')
    training_outProj = Proj(init='EPSG:4326')
    min_x,min_y = transform(training_inProj,training_outProj,extent[0],extent[1])
    max_x,max_y = transform(training_inProj,training_outProj,extent[2],extent[3])

    query = {'product': 'sen1_rtc_pyroSNAP',
             'x': (min_x, max_x),
             'y': (min_y, max_y),
             'time': (start_date, end_date),
             'output_crs': 'epsg:27700',
             'measurements': ['VH'],
             'resolution': (-10,10)}
    return query

def group_data_by(ds, period="month"):
    """
    Takes Sentinel-1 VH dataset and returns a VH dataset with data grouped by month.  
    Last modified: June 2022
    
    Parameters
    ----------
    ds : xarray.Dataset with dims ('time', 'latitude', 'longitude') and variable is VH
    period : str of the period (e.g., "month")
    """    
    year = ds.time.dt.year.values.min()
    S1_dataset = ds.sel(time=slice(str(year)+"-01-01", str(year)+"-12-31"))
    S1_dataset = S1_dataset.groupby(S1_dataset.time.dt.month).mean("time")
    S1_dataset = S1_dataset.rename_vars({'VH': 'VH_'+str(year)})
    for year in range(ds.time.dt.year.values.min()+1, ds.time.dt.year.values.max()+1):
        S1_dataset_year = ds.sel(time=slice(str(year)+"-01-01", str(year)+"-12-31")).VH
        S1_dataset_year = S1_dataset_year.groupby(S1_dataset_year.time.dt.month).mean("time")
        S1_dataset["VH_"+str(year)] = S1_dataset_year

    print("Done. Data grouped by month.")
    return S1_dataset
    
def forest_mapping(S1_dataset):
    """
    Takes Sentinel-1 dataset and returns a binary forest map.  
    Last modified: June 2022
    
    Parameters
    ----------
    S1_dataset : xarray.Dataset with dims ('month', 'latitude', 'longitude') and variables VH 
    """    
    #import xarray as xr
    
    years = list(map(get_year, list(S1_dataset.keys())))
    
    # Map annual woody extent
    print("Mapping forests ... ")
    year = years[0]
    woody_count = S1_dataset["VH_"+str(year)].where(S1_dataset["VH_"+str(year)] > -15.).count(dim="month")
    woody = ((woody_count.where(woody_count>8))*0+1)
    woody = woody.assign_coords(year=str(year)).expand_dims('year')
    for year in years[1:]:
        woody_count = S1_dataset["VH_"+str(year)].where(S1_dataset["VH_"+str(year)] > -15.).count(dim="month")
        woody_year =((woody_count.where(woody_count>8))*0+1)
        woody_year = woody_year.assign_coords(year=str(year)).expand_dims('year')
        woody = xr.concat([woody, woody_year], 'year')
    
    woody = woody.where(woody>0)
    print("Done." )
    return woody



def clearfells_monitoring(woody):
    """
    Takes series of binary forest maps and returns annual clearfells.  
    Last modified: June 2022
    
    Parameters
    ----------
    woody : xarray.DataArray of binary forest maps with dims ('year', 'latitude', 'longitude')
    """
    
    start_time = time()
    print("Detecting clearfells that occurred in: ")
    from_year = woody.year.values[0]
    to_year = woody.year.values[1]
    print(to_year)
    changes = woody.sel(year=to_year).fillna(0) - woody.sel(year=from_year).fillna(0)
    clear_cuts = (changes.where(changes<0)*0+1).fillna(0)
    clear_cuts_clean = ndimage.morphology.binary_opening(
        clear_cuts.values, structure=np.ones((3,3))).astype(np.uint8)
    clear_cuts_clean = xr.DataArray(np.flipud(clear_cuts_clean), dims=('latitude','longitude'))
    clear_cuts_clean = clear_cuts_clean.assign_coords(year=str(to_year)).expand_dims('year')

    for year_index in range(2,len(woody.year.values)):
        from_year = woody.year.values[year_index-1]
        to_year = woody.year.values[year_index]
        print(to_year)
        changes_year = woody.sel(year=to_year).fillna(0) - woody.sel(year=from_year).fillna(0)
        clear_cuts_year = (changes_year.where(changes_year<0)*0+1).fillna(0)
        clear_cuts_year_clean = ndimage.morphology.binary_opening(
            clear_cuts_year.values, structure=np.ones((3,3))).astype(np.uint8)
        clear_cuts_year_clean = xr.DataArray(np.flipud(clear_cuts_year_clean), dims=('latitude','longitude'))
        clear_cuts_year_clean = clear_cuts_year_clean.assign_coords(year=str(to_year)).expand_dims('year')
        clear_cuts_clean = xr.concat([clear_cuts_clean, clear_cuts_year_clean], 'year')
    print("Done.")
    print("")
    print("The new Digital Infrastructure for Wales and algorithms, that have been developped and set up by the Living Wales project, allowed to analyse 5 years of almost daily data and detect clearfells in " + str(round(time()-start_time,2)) + " seconds.")
    print("")
    
    clear_cuts_clean = clear_cuts_clean.where(clear_cuts_clean>0)
    return clear_cuts_clean


def mapping_clearfelling_dates(clear_cuts_clean):
    """
    Takes annual clearfell maps and returns a map of clearfell dates (i.e., year).  
    Last modified: June 2022
    
    Parameters
    ----------
    clear_cuts_clean : xarray.DataArray of clearfells with dims ('year', 'latitude', 'longitude')
    """
    
    year = clear_cuts_clean.year.values[0]
    clear_cuts_clean = clear_cuts_clean.fillna(0)
    annual_clear_cuts = clear_cuts_clean.sel(year=year) * 2018
    
    for year in clear_cuts_clean.year.values[1:]:
        annual_clear_cuts_year = (clear_cuts_clean.sel(year=year).where(annual_clear_cuts < 2000) * int(year)).fillna(0)
        annual_clear_cuts = annual_clear_cuts + annual_clear_cuts_year
    annual_clear_cuts = annual_clear_cuts.where(annual_clear_cuts>0)
    
    return annual_clear_cuts


def clearfell_reporting(site, clearfell_date):
    """
    Takes the name of the site of interest and a map of clearfell dates and returns a report summarising 
    the area (ha) of clearfelled forest by year.
    Last modified: June 2022
    
    Parameters
    ----------
    site : str indicating site name
    clearfell_date : xarray.DataArray of clearfell dates
    """
    import math
    
    year_stats = np.unique(clearfell_date.fillna(0), return_counts=True)
    stats_summary = "For the " + site.upper() + " forest site, we report : "
    print(stats_summary)
    for year_index in range(len(year_stats[0])):
        year = year_stats[0][year_index]
        if (year > 1900):
            px = year_stats[1][year_index]
            area_ha = (px * 100) / 10000
            print(str(math.floor(area_ha)) + " hectares of clearfelling during " + str(int(year)))
