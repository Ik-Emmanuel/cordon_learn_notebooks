## dea_bandindices.py
'''
Description: This file contains a set of python functions for computing
remote sensing flood mapping on WDC data.
'''

# Define custom functions
def select_flooded_site(site_index):
    """
    Takes a site index and returns its coordinates with EPSG:27700.  
    Last modified: June 2022
    
    Parameters
    ----------
    site_index : integer between 1 and 4 or string from sites_label dictionary 

    """
    sites_label = {1: {"area": "River Wye", 
                       "min_x_27700": 330650,
                       "min_y_27700": 243050, 
                       "max_x_27700": 337330, 
                       "max_y_27700": 248690},
                   2: {"area": "River Usk",
                        "min_x_27700": 332950,
                        "min_y_27700": 188900,
                        "max_x_27700": 342480,
                        "max_y_27700": 198900},
                   3: {"area": "Severn",
                       "min_x_27700": 321930,
                       "min_y_27700": 308340,
                       "max_x_27700": 332030,
                       "max_y_27700": 316870},
                   4: {"area": "River Dee",
                       "min_x_27700": 336140,
                       "min_y_27700": 342860,
                       "max_x_27700": 342950,
                       "max_y_27700": 351810},
                   "wye": {"area": "River Wye",
                       "min_x_27700": 330650, 
                       "min_y_27700": 243050, 
                       "max_x_27700": 337330, 
                       "max_y_27700": 248690},
                   "usk": {"area": "River Usk",
                        "min_x_27700": 332950,
                        "min_y_27700": 188900,
                        "max_x_27700": 342480,
                        "max_y_27700": 198900},
                   "severn": {"area": "Severn",
                       "min_x_27700": 321930,
                       "min_y_27700": 308340,
                       "max_x_27700": 332030,
                       "max_y_27700": 316870},
                   "dee": {"area": "River Dee",
                       "min_x_27700": 336140,
                       "min_y_27700": 342860,
                       "max_x_27700": 342950,
                       "max_y_27700": 351810}
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
             'measurements': ['VH','VV'],
             'resolution': (-10,10)}
    return query

def flood_mapping(ds):
    """
    Takes Sentinel-1 dataset and returns a binary flood map.  
    Last modified: June 2022
    
    Parameters
    ----------
    ds : xarray.Dataset with dims ('time', 'latitude', 'longitude') and variables VH and VV
    """    
    
    # detect areas under water 
    flood_map = ds.VH.where((ds.VV <(-14)) & (ds.VH <(-24)))*0 +1
    return flood_map

def flood_progression(flood_series):
    """
    Takes series of binary flood maps and returns a map of flood progression.  
    Last modified: June 2022
    
    Parameters
    ----------
    flood_series : xarray.DataArray of binary flood maps with dims ('time', 'latitude', 'longitude')
    """
    import xarray as xr
    
    strDate = flood_series.time[1].values
    water_changes = flood_series.isel(time=1).fillna(0)*2 - flood_series.isel(time=0).fillna(0)
    water_changes = water_changes.assign_coords(time=strDate).expand_dims('time')

    for time in range(2,flood_series.time.size):
        strDate = flood_series.time[time].values
        previous_time = time-1

        diff_maps = flood_series.isel(time=time).fillna(0)*2 - flood_series.isel(time=previous_time).fillna(0)
        diff_maps = diff_maps.assign_coords(time=strDate).expand_dims('time')
        water_changes = xr.concat([water_changes, diff_maps], 'time')
    
    return water_changes.where(water_changes!=0)

def flood_frequency(flood_series, start_date, end_date):
    """
    Takes series of binary flood maps and returns frequency of floods for a period of interest.  
    Last modified: June 2022
    
    Parameters
    ----------
    flood_series : xarray.DataArray of binary flood maps with dims ('time', 'latitude', 'longitude')
    start_date : str with format 'YYYY-MM-DD'
    end_date : str with format 'YYYY-MM-DD'
    """

    flooded_feb = flood_series.sel(time=slice(start_date, end_date))
    wet_feb = flooded_feb.count(dim='time').where(flooded_feb.count(dim='time')>0)
    nb_images_feb = flooded_feb.time.size

    frequency = (wet_feb / nb_images_feb).rename("frequency")
    
    return frequency