from ipywidgets import RadioButtons
from habitat import habitat_dict
'''
Description: This file contains a set of python functions for computing
remote sensing burnt area mapping with WDC data.
'''

# Define custom functions
def burnt_site_list():
    site_widget = RadioButtons(
        options=["Glanaman","Bwlch Corog","Mynydd Mawr","Foel Feddau", "Mynydd Llanllwni"],
        layout={'width': 'max-content'}, # If the items' names are long
        description='',
        disabled=False
    )
    return site_widget


def get_site_extent(site_index):
    """
    Takes a site index and returns its coordinates with EPSG:27700.  
    Last modified: June 2022
    
    Parameters
    ----------
    site_index : integer between 1 and 5 or string from sites_label dictionary 

    """
    sites_label = {"Bwlch Corog": {"area": "Bwlch Corog",
                       "min_x": -3.865763, 
                       "min_y": 52.522037, 
                       "max_x": -3.827761, 
                       "max_y": 52.542997},
                   "Mynydd Mawr": {"area": "Mynydd Mawr",
                       "min_x": -4.216724, 
                       "min_y": 53.054927, 
                       "max_x": -4.149385, 
                       "max_y": 53.085853},
                   "Foel Feddau": {"area": "Foel Feddau",
                       "min_x": -4.787036, 
                       "min_y": 51.941578, 
                       "max_x": -4.686715, 
                       "max_y": 51.982923},
                   "Glanaman": {"area": "Glanaman",
                       "min_x": -3.93625, 
                       "min_y": 51.814918, 
                       "max_x": -3.843181, 
                       "max_y": 51.855518},
                   "Mynydd Llanllwni": {"area": "Mynydd Llanllwni",
                       "min_x": -4.196349, 
                       "min_y": 52.009084, 
                       "max_x": -4.177463, 
                       "max_y": 52.019668}
                  }
    
    print("Chosen area: " + sites_label[site_index]["area"])
    
    return(sites_label[site_index]["min_x"], sites_label[site_index]["min_y"], 
            sites_label[site_index]["max_x"], sites_label[site_index]["max_y"])

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
             'measurements': ['VH','VV'],
             'resolution': (-10,10)}
    return query

def burn_mapping(ds, normalise=False):
    """
    Takes Sentinel-2 dataset and returns a binary burn map.  
    
    Parameters
    ----------
    ds : xarray.Dataset with variables nir and swir2 (normalised)
    """    
    
    # calculating NBR
    from wdc_bandindices import calculate_indices
    dataset_index = calculate_indices(ds, index='NBR', platform= 'SENTINEL_2',normalise=normalise)
    
    # detect areas under water 
    burn_map = dataset_index.NBR.where((dataset_index.NBR < (-0.01))&(dataset_index.NBR > (-0.99)))*0+1
    return burn_map

def burn_progression(burnt_series):
    """
    Takes series of binary burn maps and returns a map of burn progression.  
    Last modified: June 2022
    
    Parameters
    ----------
    burnt_series : xarray.DataArray of binary burnt areas maps with dims ('time', 'latitude', 'longitude')
    """
    import xarray as xr
    
    strDate = burnt_series.time[1].values
    burnt_changes = burnt_series.isel(time=1).fillna(0)*2 - burnt_series.isel(time=0).fillna(0)
    burnt_changes = burnt_changes.assign_coords(time=strDate).expand_dims('time')

    for date in range(2,burnt_series.time.size):
        strDate = burnt_series.time[date].values
        previous_date = date-1

        diff_maps = burnt_series.isel(time=date).fillna(0)*2 - burnt_series.isel(time=previous_date).fillna(0)
        diff_maps = diff_maps.assign_coords(time=strDate).expand_dims('time')
        burnt_changes = xr.concat([burnt_changes, diff_maps], 'time')
    
    return burnt_changes.where(burnt_changes!=0)


def report_max_burn_extent(burnt_area_ha):
    # group the amount of burnt areas by year 
    annual_burnt_area_ha_list = burnt_area_ha.groupby(burnt_area_ha.time.dt.year)


    # for each year calculate the maximum burnt area and return the date when it happened.
    report_total_annual_burnt_area = []
    for annual_burnt_area_ha in annual_burnt_area_ha_list:
        annual_report = str(annual_burnt_area_ha[0])+ ": " + str(annual_burnt_area_ha[1].max().values) + " ha burnt by the " +             str(annual_burnt_area_ha[1][annual_burnt_area_ha[1].argmax()].time.values).split("T")[0]
        report_total_annual_burnt_area.append(annual_report)

    return report_total_annual_burnt_area


def report_burnt_habitats(burn, habitat_map):
    """
    Takes a binary burn map and habitat map and returns a report about burnt habitats (ha and year).  
    Last modified: Sept 2023
    """
    import numpy as np
    
    report_burnt_habitats= {}
    for year in np.unique(burn.time.dt.year.values):
        report_burnt_habitats[str(year)]={}

        burnt_areas = (burn.where(burn.time.dt.year==year, drop=True).sum(dim='time') > 0)
        burnt_habitats = habitat_map.detailed.where(burnt_areas==True)
        burnt_habitats_summary = burnt_habitats.groupby(burnt_habitats).count()

        for habitat_burnt in burnt_habitats_summary:
            if (((int(habitat_burnt.detailed.values) < 134) | (int(habitat_burnt.detailed.values)==159) | 
                 (int(habitat_burnt.detailed.values)==202))) & (int(habitat_burnt.detailed.values)!=90):
                report_burnt_habitats[str(year)][habitat_dict[int(habitat_burnt.detailed.values)
                                                             ]]=habitat_burnt.values*100/10000

    for habitat_name in list(set(val for dic in report_burnt_habitats for val in list(report_burnt_habitats[dic].keys()))):
        for dic in report_burnt_habitats:
            if habitat_name not in list(report_burnt_habitats[dic].keys()):
                report_burnt_habitats[dic][habitat_name]=0

    for dic in report_burnt_habitats:
        report_burnt_habitats[dic] = {key: value for key, value in sorted(report_burnt_habitats[dic].items())}

    return report_burnt_habitats