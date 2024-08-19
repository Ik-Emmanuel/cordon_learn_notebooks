"""
Notebook dropbown functions.

This notebook contains variables and functions that allow users to select areas using a combination of dropdowns and interactive maps.
It was developed as part of the Living Wales project.

Authors: Abigail Sanders, Dan Clewley, Emmanuel Nwokocha.

"""

import glob
import os
import pandas as pd
import geopandas as gpd
import ipywidgets as widgets
import ipyleaflet
from ipyleaflet import Map, GeoData, LayersControl, FullScreenControl, DrawControl, basemaps
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
from ipywidgets import RadioButtons, BoundedFloatText, Layout, IntProgress, VBox, HBox, HTML, Button
import threading
from shapely.geometry import shape, mapping

from shapely.ops import transform
import pyproj


import time


# folders to look for shape files
WELSH_AREAS_FOLDER = "/home/jovyan/shared_space/welsh_areas"
USER_UPLOADS_FOLDER = "/home/jovyan/shared_space/uploads"

# default shapefile search glob
vector_types_list = glob.glob(f"{WELSH_AREAS_FOLDER}/*")
vector_types_dict = {}

# Add in user uploads directory
vector_types_dict["1. User uploads"] = USER_UPLOADS_FOLDER

vector_types_dict = vector_types_dict | {
    os.path.basename(vector_type).replace("_", " "): vector_type
    for vector_type in vector_types_list
    if os.path.isdir(vector_type)
}


# declare accessible global variables to store objects reused across components 
global gpd_df  ## the geopandas dataframe for the selected shapefile
global col_name_var   ## suitable column name for site names within a shapefile
global AREA_SELECTION
global selected_polygon
global RESULTS
global get_polygon
global buffer_distance
global confirmed_buffer_distance


# instantiate variables
RESULTS = {}
RESULTS["global_selected_polygon"] = None
RESULTS["global_selected_polygon_geomvalue"] = None  ## the geometry value of selected polygon

RESULTS["global_area_selection_type"] = None  # options are 1. Draw: if selection method is to draw on map  2. Select: if selection method is to select from map or shp file.
RESULTS["global_selected_area"] = None  # for drawn area from map
RESULTS["global_selected_polygon_type"] = None  # options are All: if all is selected and Selected: if a single one is selected
RESULTS["get_polygon"] = None
RESULTS["area_selection_type"] = None
RESULTS["buffer_distance"] = 100
AREA_SELECTION = None
selected_polygon = None


   # <b>To use entire areas shown, please click <span style='color:orange'> 'USE ALL POLYGONS' </span>.<br> If you want to select a specific polygon please click on the map, to select area and <span style='color:orange'> wait for <span style='color:#5a5c5a'> 'Selected Polygon' </span> confirmation below.<span>  </b>
def helper():
    """This method will display all the available method and usage snippet to the user """
    html = widgets.HTML()
    docs = """
    <p> <b style='color:black'> List of available commands for selecting geographic sites for analysis </b> </p>
    <p style='color:black'>Example commands and description: <br> 
    <span style='color:black'> 1.   <b style='color:orange'> polygon_select = notebook_dropdowns.area_selection() </b>: Displays available options to select vector polygon, or to draw area on map and assigns option selected to a variable "polygon_select"  </span> <br>
     <span style='color:black'> 2.  <b style='color:orange'> polygon_df = notebook_dropdowns.view_selected_polygon(polygon_select)</b>: Reads and sets the selected vector/polygon as a geopandas dataframe  to a varible called "polygon_df" for use.  </span> <br>
     <span style='color:black'> 3. <b style='color:orange'> notebook_dropdowns.plot_selected_polygon(polygon_select) </b>: Plots the selected vector/polygon for visual confirmation </span> <br>
     <span style='color:black'> 4. <b style='color:orange'> notebook_dropdowns.map_and_select_area(polygon_select) </b>: Generates an interactive map to click and select an area or draw area on map if draw option is selected in  'area_selection()' </span> <br>
     <span style='color:black'> 5. <b style='color:orange'> notebook_dropdowns.polygon_selected() </b>: Displays the set vector/polygon selected and confirmed for use for analysis it can be assigned to a variable. </span> <br>
     <span style='color:black'> 6. <b style='color:orange'> notebook_dropdowns.visualize_selected_area() </b>: Maps the selected area for visual confirmation.  </span> <br>
     <span style='color:black'> 7. <b style='color:orange'> notebook_dropdowns.include_buffer() </b>: Provides option to select buffer to be added to selected sites  </span> <br>
     <span style='color:black'> 8. <b style='color:orange'> notebook_dropdowns.active_buffer() </b>: Displays how much active buffer has been set  </span> <br>
     <span style='color:black'> 9. <b style='color:orange'> notebook_dropdowns.buffer_include_selection() </b>: Applies and displays set buffer amount to selected area, INCLUDING the selected area.  </span> <br>
     <span style='color:black'> 10. <b style='color:orange'> notebook_dropdowns.buffer_exclude_selection() </b>: Applies and displays set buffer amount to selected area, EXCLUDING the selected area.  </span> <br>
    </p>
    """
    html.value = docs
    display(html)
    return None

# ================================= Helper Functions =========================================================
def set_global_result(key, value, results_dict):
    """ This function sets value to
    globally defined RESULTS dictionary """
    results_dict[key] = value
    
    
def get_global_result(key, results_dict):
    """ This reads value from globally defined RESULTS dictionary """
    # return RESULTS.get(key, "Nothing selected")
    return results_dict.get(key, None)


def mapper_preprocessor(geopandas_dataframe):
    """
    Prepares the vector geopandas dataframe ready for mapping.
    """
    # Make a copy if the DataFrame might be a slice
    geopandas_dataframe = geopandas_dataframe.copy()
    
    # Set the GeoDataFrame to geographic CRS for plotting
    geopandas_dataframe = geopandas_dataframe.to_crs(epsg=4326)
    return geopandas_dataframe


def convert_to_geojson(selected_polygon):
    """Given a geopandas dataframe of single site, else it takes just first row  
    this converts and return a geojson format of it """
    if isinstance(selected_polygon, gpd.GeoDataFrame):
        # geometry = selected_polygon.loc[0, 'geometry']
        geometry = selected_polygon.iloc[0]['geometry']
        # Convert to GeoJSON-like dictionary
        area_to_geojson = geometry.__geo_interface__
        return area_to_geojson
    else:
        print("Error converting: Area is not a geopandas dataframe")
        return None
    
def convert_to_geopandas_df(selected_polygon):
    """Given a geojson of a single site, 
    this converts and return a geopandas dataframe with one column = "geometry"  """
    # If selected_polygon is a dictionary representing a geometry
    if isinstance(selected_polygon, dict) and 'type' in selected_polygon and 'coordinates' in selected_polygon:
        # Convert dictionary to a GeoPandas DataFrame
        geom = shape(selected_polygon)
        area_gdf = gpd.GeoDataFrame({'geometry': [geom]})
        return area_gdf
    else:
        print("Error converting: Area is not in GeoJson format")
        return None

def convert_timestamps_to_strings(df):
    """
    Converts all Timestamp columns in the DataFrame to strings.
    """
    for col in df.columns:
        if isinstance(df[col].dtype, pd.core.dtypes.dtypes.DatetimeTZDtype) or df[col].dtype == 'datetime64[ns]' or df[col].dtype == 'datetime64[ms]':
            df[col] = df[col].astype(str)
    return df


# ==================================== End of helper functions =======================================


    
def polygon_selected():
    """ This function fetches and returns value of selected polygon if it exists """
    selected_global_polygon =  get_global_result("global_selected_polygon", RESULTS)
    selected_global_polygon_geomvalue =  get_global_result("global_selected_polygon_geomvalue", RESULTS)
    selected_global_polygon_type =  get_global_result("global_selected_polygon_type", RESULTS)
    global_area_selection_type =  get_global_result("global_area_selection_type", RESULTS)
    
    # get and retrun user drawn polygon from map 
    if global_area_selection_type and global_area_selection_type == "Draw":
        drawn_polygon = get_global_result("global_selected_area", RESULTS)
        return  drawn_polygon
    
    # get and return user selected polygon area(s)
    elif global_area_selection_type and global_area_selection_type == "Select":
        
        if selected_global_polygon_type and selected_global_polygon_type == "All":
             # return whole geodataframe selected  if all is selected
            get_polygon = get_global_result("get_polygon", RESULTS)
            if get_polygon and get_polygon.value is not None:
                gpd_df_sub = gpd_df[gpd_df[col_name_var] == get_polygon.value]
                return gpd_df_sub
            else:
                gpd_df_sub = gpd_df
                return gpd_df_sub

        elif selected_global_polygon and selected_global_polygon_type == "Selected":
            try:
          
                # Option1: fetch object using fid
                identifier = selected_global_polygon.get("fid", None)
                if identifier is not None:
                    # find and return selected polygon 
                    gpd_df_sub = gpd_df[gpd_df["fid"] == identifier]
                    return gpd_df_sub
                
                # Option2: fetch object identifier from selected_polygon dict
                # identifier_key = list(selected_global_polygon.keys())[0]
                # if identifier_key:
                #     gpd_df_sub = gpd_df[gpd_df[identifier_key] == selected_global_polygon[identifier_key]]
                #     # find and return selected polygon 
                #     return gpd_df_sub
                
                
                # Option 3: fetch object iuse geometry to pick 

#                 if selected_global_polygon_geomvalue:
#                     selected_geometry = shape(selected_global_polygon_geomvalue)
#                     # gpd_df_sub = gpd_df[gpd_df["geometry"].apply(lambda x: x.equals(selected_geometry))]
#                     gpd_df_sub = gpd_df[gpd_df["geometry"].intersects(selected_geometry)]
#                     return gpd_df_sub
#                 else:
#                     print("no geom value")
#                     return None
        
            except Exception as e:
                print("error occured", e)

    # returns None set read drop down value
    if not selected_global_polygon:
        get_polygon_dropdown =  get_global_result("get_polygon", RESULTS)
        polygon_dropdown_value = get_polygon_dropdown.value
        if polygon_dropdown_value is not None:
            gpd_df_sub = gpd_df[gpd_df[col_name_var] == polygon_dropdown_value]
            return gpd_df_sub
        else:
            print("Polygon not set")
    print("No polygon currently selected. Run map_and_select_area(polygon_select), click/draw and confirm area on map")
    return None



def area_selection():
    """Function that displays options to select an area, shapefile and polygon"""
    # Path to Welsh Dataset repository
    shapefiles_dict = {}

    def update_shapefiles(*args):
        args        # List all shapefiles in the selected directory
        shapefiles_list = glob.glob(
            os.path.join(vector_types_dict[get_type.value], "*.shp")
        )
        shapefiles_dict.clear()
        shapefiles_dict.update(
            {
                os.path.basename(shapefile)
                .replace(".shp", "")
                .replace("_", " ")
                .lower(): shapefile
                for shapefile in shapefiles_list
            }
        )

        # Update shapefile dropdown options
        get_shapefile.options = list(shapefiles_dict.keys())
        get_shapefile.value = (
            list(shapefiles_dict.keys())[0] if shapefiles_dict else None
        )
        update_polygons()

    # Function to update the polygon options
    def update_polygons(*args):
        selected_shapefile_path = shapefiles_dict.get(get_shapefile.value, None)

        if selected_shapefile_path:
            global gpd_df, col_name_var  # Define as global variables
            gpd_df = gpd.read_file(selected_shapefile_path)
            ## Very important. it adds the unique identifier to be used to identifiy polygons with shp file
            gpd_df["fid"] = gpd_df.index

            # Try to find a suitable column name for site names
            col_name_var = None
            if "name" in gpd_df.columns:
                col_name_var = "name"
            else:
                for col in gpd_df.columns:
                    if "name" in col.lower():
                        col_name_var = col
                        break

            if col_name_var is not None:
                site_names = gpd_df[col_name_var].drop_duplicates().tolist()
                get_polygon.options = site_names
                get_polygon.value = None
            else:
                get_polygon.options = []
                get_polygon.value = None
        else:
            get_polygon.options = []
            get_polygon.value = None

    style = {'description_width': 'initial'}
    
    # Dropdown for selecting vector type
    get_type = widgets.Dropdown(
        options=list(vector_types_dict.keys()),
        value=list(vector_types_dict.keys())[0],
        default="User uploads",
        description="Area Selection Type",
        disabled=False,
        layout=Layout(width='40%'),
        style=style
    )

    # Dropdown for selecting shapefile
    get_shapefile = widgets.Dropdown(
        options=[],
        description="Choose Vector",
        disabled=False,
        layout=Layout(width='40%'),
        style=style
    )

    # Dropdown for selecting polygon
  
    get_polygon = widgets.Dropdown(
        options=[],
        description="Select a polygon",
        disabled=False,
        default="",
        layout=Layout(width='40%'),
        style=style
    )

    # Observe changes and update accordingly
    get_type.observe(update_shapefiles, "value")
    get_shapefile.observe(update_polygons, "value")

    # Function to reset the dropdowns and clear outputs
    def reset_dropdowns(*args):
        get_type.value = list(vector_types_dict.keys())[0]
        update_shapefiles()
        clear_output(wait=True)
        display(get_type)
        display(get_shapefile)
        display(get_polygon)
        display(reset_button)

    # Button for resetting the dropdowns
    reset_button = widgets.Button(description="Reset")
    reset_button.on_click(reset_dropdowns)

    # Initial update of shapefiles and polygons
    update_shapefiles()

    # Display the dropdowns and reset button
    display(get_type)
    display(get_shapefile)
    display(get_polygon)
    display(reset_button)
    # return get_type, get_shapefile, get_polygon, reset_button
    
    set_global_result("get_polygon", get_polygon, RESULTS)
    set_global_result("area_selection_type", get_type, RESULTS)
    return get_polygon



def view_selected_polygon(selected_polygon):
    """
    returns a geodataframe of the selected polygon 
    """
    if selected_polygon.value is not None:
        gpd_df_sub = gpd_df[gpd_df[col_name_var] == selected_polygon.value]
        polygon_name = selected_polygon.value
    else:
        gpd_df_sub = gpd_df
        polygon_name = "All"

    return gpd_df_sub


# formally called:  static_polygon_plot
def plot_selected_polygon(selected_polygon):
    """
    Produces a static plot of a given polygon
    """
    # ================ add progress bar =========
    progress_value = IntProgress(min=0, max=100) # instantiate the progress bar
    print("Generating Plot ...")
    display(progress_value) # display the bar
    
    stop_thread = threading.Event()  # Event used to signal the thread to stop
    
    def update_progress_bar():
        """Continuously update the progress bar until the map is ready."""
        progress = 0
        while not stop_thread.is_set():  # Continue until stop signal is received
            progress_value.value = progress % 100
            progress += 1
            time.sleep(0.2)
        progress_value.value = 100  # Ensure progress bar is set to 100% when stop_thread is set
        
    
     # Start progress bar in a separate thread
    progress_thread = threading.Thread(target=update_progress_bar)
    progress_thread.start()

    if selected_polygon.value is not None:
        gpd_df_sub = gpd_df[gpd_df[col_name_var] == selected_polygon.value]
        polygon_name = selected_polygon.value
    else:
        gpd_df_sub = gpd_df
        polygon_name = "All"

    # Ensure the GeoDataFrame is in a projected CRS for accurate area calculation
    gpd_df_sub = gpd_df_sub.to_crs(epsg=3857)

    # Calculate the area in square meters
    gpd_df_sub["area"] = gpd_df_sub.geometry.area

    # Sum the areas to get the total area in hectares (1 hectare = 10,000 square meters)
    total_area = gpd_df_sub["area"].sum() / 10000

    # Set the GeoDataFrame back to geographic CRS for plotting
    gpd_df_sub = gpd_df_sub.to_crs(epsg=4326)

    # Set the figure size for standardization
    fig, ax = plt.subplots(figsize=(10, 10))

    # Visualize the polygon with standardized size
    gpd_df_sub.plot(ax=ax, color="blue", edgecolor="black")
    ax.set_title(f"Site Visualization ({polygon_name})")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    # Add north arrow
    x, y = -0.2, 1  # Adjust these values based on your plot
    arrow_length = 0.1
    ax.annotate(
        "N",
        xy=(x, y),
        xytext=(x, y - arrow_length),
        arrowprops=dict(facecolor="black", width=5, headwidth=15),
        ha="center",
        va="center",
        fontsize=20,
        xycoords="axes fraction",
    )
    
    
    plt.show()
    # Display total area
    print(f"Total area: {total_area:.2f} ha")
    
        # Signal the progress thread to stop before function exists
    stop_thread.set()
    progress_thread.join()  # Ensure the progress thread has finished 

    return None






def map_and_select_area(selected_polygon):
    """" Function to map selected polygon and click to select or draw to select """
    # fetch geodataframe of selected polygon
    if selected_polygon.value is not None:
        gpd_df_sub = gpd_df[gpd_df[col_name_var] == selected_polygon.value]
        polygon_name = selected_polygon.value
    else:
        gpd_df_sub = gpd_df
        polygon_name = "All"
        
    gpd_df_sub = mapper_preprocessor(gpd_df_sub)
                
    # identify if DRAW ON MAP or others 
    area_selection_type = get_global_result("area_selection_type", RESULTS)
    if area_selection_type and area_selection_type.value:
        if area_selection_type.value.endswith("Draw an area"):
            # set global area selection type to: Draw
            set_global_result("global_area_selection_type", "Draw", RESULTS)
            # show map to draw area
            draw_site_from_map(gpd_df_sub)
        else: 
            # set global area selection type to: Select
            set_global_result("global_area_selection_type", "Select", RESULTS)
            # show interactive map to select site from 
            select_site_from_map(gpd_df_sub)

    else:
        print("Unidentified Area Selection Type")
        return None
    
    


def select_site_from_map(gpd_df_sub):
    """
    Produces an interactive plot of a given polygon for click and select
    """

    stop_thread = threading.Event()  # Event to signal the thread to stop
    # Initialize selected_polygon variable
    selected_polygon = None

    # Style dictionary for non-selected polygons
    default_style = {
        "color": "black",
        "fillColor": "#3366cc",
        "opacity": 0.05,
        "weight": 1.9,
        "dashArray": "2",
        "fillOpacity": 0.6,
    }

    # Style dictionary for the selected polygon
    selected_style = {
        "color": "black",
        "fillColor": "orange",  # Color for the selected polygon
        "opacity": 0.8,
        "weight": 2,
        "dashArray": "2",
        "fillOpacity": 0.6,
    }

    
    # Function to update the style of the polygons
    def update_polygon_style():
        for feature in geo_data.data['features']:
            if selected_polygon and all(
                feature["properties"][k] == selected_polygon[k] for k in selected_polygon
            ):
                feature['style'] = selected_style
            else:
                feature['style'] = selected_style
        
    
    # Function to confirm and rename the output to AREA_selection
    def confirm_selection(button):
        AREA_SELECTION = AREA_SELECTION
        print("The selected area has been confirmed as 'AREA_SELECTION'")

    # Function to select all polygons 
    def confirm_select_all(button):
        selected_polygon = None  # Clear any individual polygon  selection
        update_polygon_style()  # Reset the styles
        html.value = "<b style='color:orange'>  All polygons currently selected <b><br>"
        set_global_result("global_selected_polygon", gpd_df_sub, RESULTS)
        set_global_result("global_selected_polygon_type", "All", RESULTS)
     

    # ================ add progress bar =========
    progress_value = IntProgress(min=0, max=100) # instantiate the bar
    print("Generating Interactive Map ...")
    display(progress_value) # display the progress  bar as a widget

    def update_progress_bar():
        """Continuously update the progress bar until the map is ready."""
        progress = 0
        while not stop_thread.is_set():  # Continue until stop signal is received
            progress_value.value = progress % 100
            progress += 1
            time.sleep(0.2)
        progress_value.value = 100  #
    
    # Start progress bar in a separate thread
    progress_thread = threading.Thread(target=update_progress_bar)
    progress_thread.start()

    # Calculate the bounding box
    bounds = gpd_df_sub.total_bounds  # returns (minx, miny, maxx, maxy)
    sw = [bounds[1], bounds[0]]  # southwest corner (miny, maxx)
    ne = [bounds[3], bounds[2]]  # northeast corner (maxy, minx)

    # Calculate the center of the bounding box
    center = [(sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2]

    # Convert any Timestamps to strings
    AREA_SELECTION = convert_timestamps_to_strings(gpd_df_sub)

    # Initialize selected_polygon variable
    selected_polygon = None

    # Create a button for confirming the selection
    confirm_button = widgets.Button(description="CONFIRM")
    confirm_button.on_click(confirm_selection)
    
    # Display the instructions, button, and map
    # instructions = widgets.HTML("<b>If you are happy with the entire areas shown please click 'Confirm'.<br>If you want to select a specific polygon please click on the map.</b>")
    # display(widgets.VBox([instructions, confirm_button]))
    # HTML widget to display selected shapefile information
    html = widgets.HTML()
    html.value = "<b style='color:orange'> All polygons currently selected <b>"
    
    #use all polygon button
    select_all_poly_button = widgets.Button(description="USE ALL POLYGONS")
    select_all_poly_button.on_click(confirm_select_all)

    # Create GeoData layer
    geo_data = ipyleaflet.GeoData(
        geo_dataframe=AREA_SELECTION,
        style=default_style,
        hover_style={"fillColor": "red", "fillOpacity": 0.2},
        name="Boundary",
    )
    
    # # Create GeoData layer
    # selected_data = ipyleaflet.GeoData(
    #     geo_dataframe=AREA_SELECTION,
    #     style=selected_style,
    #     hover_style={"fillColor": "orange", "fillOpacity": 0.2},
    #     name="Selected",
    # )
    
    # Function to handle click events and store the selected polygon
    def handle_click(event, feature, **kwargs):
        html.value = f"<b style='color:orange'> Identifying selected area please wait .... </b> <br><br>"
        global selected_polygon
        selected_polygon = feature["properties"]
        selected_polygon_geomvalue = feature["geometry"]
        # Update the style of the selected polygon
        update_polygon_style()
        html.value = f"<b style='color:orange'> Selected Polygon: </b> <br> {selected_polygon} <br>"
        set_global_result("global_selected_polygon", selected_polygon, RESULTS)
        set_global_result("global_selected_polygon_geomvalue", selected_polygon_geomvalue, RESULTS)
        set_global_result("global_selected_polygon_type", "Selected", RESULTS)
        
        
    geo_data.on_click(handle_click)

    # Create a map centered on the GeoDataFrame
    m = ipyleaflet.Map(
        center=center,
        zoom=50,
        basemap=ipyleaflet.basemaps.Esri.WorldImagery,
        layout=widgets.Layout(height="600px"),
    )

    # Add GeoData layer to the map

    # m.add_layer(selected_data)
    m.add_layer(geo_data)
  

    # Fit map to bounds
    m.fit_bounds([sw, ne])

    # Add controls to the map
    m.add_control(ipyleaflet.LayersControl(position="topright"))
    m.add_control(ipyleaflet.FullScreenControl())

    # Display the map and UI elements
    display(
        widgets.VBox(
            [
                widgets.HTML(
                    "<b>To use entire areas shown, please click <span style='color:orange'> 'USE ALL POLYGONS' </span>.<br> If you want to select a specific polygon please click on the map, to select area and <span style='color:orange'> wait for <span style='color:#5a5c5a'> 'Selected Polygon' </span> confirmation below.<span>  </b>"
                ),
                html,
                select_all_poly_button,
                m,
            ]
        )
    )


    # Stop progress thread
    stop_thread.set()
    # Ensure progress thread has finished before exiting function
    progress_thread.join()




    
# ==================  Draw site from map 


def draw_site_from_map(gpd_df_sub):
    """
    This function will allow users to draw interested  site area from the welsh boundry 
    """
    stop_thread = threading.Event()  # Event to signal the thread to stop
    # Function to handle area selection
    def handle_draw(self, action, geo_json):
        global selected_area
        selected_area = geo_json['geometry']
        html.value = f"<b> <span style='color:orange' >Selected area: </span>     <br> {selected_area}</b>"
        set_global_result("global_selected_area", selected_area, RESULTS)
    
    # ================ add progress bar =========
    progress_value = IntProgress(min=0, max=100) # instantiate the bar
    print("Generating Interactive Map ...")
    display(progress_value) # display the progress  bar as a widget

    def update_progress_bar():
        """Continuously update the progress bar until the map is ready."""
        progress = 0
        while not stop_thread.is_set():  # Continue until stop signal is received
            progress_value.value = progress % 100
            progress += 1
            time.sleep(0.2)
        progress_value.value = 100  #
    
    # Start progress bar in a separate thread
    progress_thread = threading.Thread(target=update_progress_bar)
    progress_thread.start()
        
    boundary = gpd_df_sub

    # HTML widget to display selected area information
    html = HTML()
    html.value = "<b> Draw an area on the map below within the highlighted boundry, to select it.</b>"

    # Create GeoData layer for the boundary
    geo_data = GeoData(
        geo_dataframe=boundary,
        style={'color': 'red', 'fillColor': 'none', 'opacity': 1, 'weight': 2},
        name='Boundary'
    )

    # Create a map centered on the boundary with appropriate zoom
    bounds = boundary.total_bounds  # returns (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = Map(center=center, zoom=8, basemap=basemaps.Esri.WorldImagery, layout=Layout(height='600px'))

    # Add GeoData layer to the map
    m.add_layer(geo_data)

    # Add drawing tools to the map
    draw_control = DrawControl(
        polygon={"shapeOptions": {"color": "#ff0000", "weight": 4}},
        polyline={"shapeOptions": {"color": "#ff0000", "weight": 4}},
        circle={"shapeOptions": {"color": "#ff0000", "weight": 4}},
        rectangle={"shapeOptions": {"color": "#ff0000", "weight": 4}},
        marker={"shapeOptions": {"color": "#ff0000", "weight": 4}}
    )

    draw_control.on_draw(handle_draw)
    m.add_control(draw_control)

    # Add controls to the map
    m.add_control(LayersControl(position='topright'))
    m.add_control(FullScreenControl())

    # Display the initial map with the HTML widget
    display(VBox([html, m]))

    # Initialize selected_area variable
    selected_area = None
    # Stop progress thread
    stop_thread.set()
    # Ensure progress thread has finished before exiting function
    progress_thread.join()
    
    

    
    


    
# ========================= Visualize selection  ======================== 


# Function to display AREA_selection on a map if in geopandas df format
def display_geopandas_df_selection(area_selection):
    """ Given a df this allows to map area for visual confirmation """
    # Explicitly create a copy if needed
    area_selection = area_selection.copy()
    
    
    area_selection = convert_timestamps_to_strings(area_selection)
    area_selection = mapper_preprocessor(area_selection)
    if not area_selection.empty:
        # Create GeoData layer for AREA_selection
        selection_geo_data = GeoData(
            geo_dataframe=area_selection,
            style={
                "color": "black",
                "fillColor": "#3366cc",
                "opacity": 0.5,
                "weight": 1.9,
                "dashArray": "2",
                "fillOpacity": 0.3,
            },
            hover_style={"fillColor": "red", "fillOpacity": 0.2},
            name="AREA Selection",
        )
        
        # Calculate the center of the selection area
        bounds = area_selection.total_bounds  # returns (minx, miny, maxx, maxy)
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        # Create a map centered on the selection area
        selection_map = Map(center=center, zoom=10, basemap=basemaps.Esri.WorldImagery, layout=Layout(height='600px'))
        
        # Add GeoData layer to the map
        selection_map.add_layer(selection_geo_data)
        
        # Fit map to bounds
        sw = [bounds[1], bounds[0]]  # southwest corner (miny, minx)
        ne = [bounds[3], bounds[2]]  # northeast corner (maxy, maxx)
        selection_map.fit_bounds([sw, ne])
        
        # Add controls to the map
        selection_map.add_control(LayersControl(position='topright'))
        selection_map.add_control(FullScreenControl())
        
        # Display the map
        display(selection_map)
    else:
        display(HTML("No area selected."))


# Function to visualize the selected area on a new map if in GeoJson format
def visualize_selected_area():
    """ This function visualizes drawn selected area that is in GeoJson format  """
    selected_global_polygon =  get_global_result("global_selected_polygon", RESULTS)
    selected_global_polygon_geomvalue =  get_global_result("global_selected_polygon_geomvalue", RESULTS)
    global_area_selection_type =  get_global_result("global_area_selection_type", RESULTS)
    global_area_selection = get_global_result("global_selected_area", RESULTS)
    

    # get and retrun user drawn polygon from map 
    if global_area_selection_type and global_area_selection_type == "Draw":
        drawn_polygon = get_global_result("global_selected_area", RESULTS)

        if drawn_polygon:
            selected_area = drawn_polygon
            # Convert the selected area to a GeoDataFrame
            selected_geom = shape(selected_area)
            selected_gdf = gpd.GeoDataFrame({'geometry': [selected_geom]}, crs='epsg:4326')

            # Calculate the area in hectares
            proj = pyproj.Transformer.from_crs('epsg:4326', 'epsg:3857', always_xy=True).transform
            selected_gdf['area_ha'] = selected_gdf['geometry'].apply(lambda geom: transform(proj, geom).area / 10000)
            area_ha = selected_gdf['area_ha'].iloc[0]

            # Transform shapefile boundaries into geographic data (and affect a style)
            geo_data = GeoData(
                geo_dataframe=selected_gdf,
                style={
                    "color": "black",
                    "fillColor": "#3366cc",
                    "opacity": 0.05,
                    "weight": 1.9,
                    "dashArray": "2",
                    "fillOpacity": 0.6,
                },
                hover_style={"fillColor": "red", "fillOpacity": 0.2},
                name="Selected Area",
            )

            # Calculate the center of the selected area
            bounds = selected_gdf.total_bounds  # returns (minx, miny, maxx, maxy)
            center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

            # Create a map centered on the selected area
            selected_map = Map(center=center, zoom=10, basemap=basemaps.Esri.WorldImagery, layout=Layout(height='600px'))

            # Add GeoData layer to the map
            selected_map.add_layer(geo_data)

            # Fit map to bounds
            sw = [bounds[1], bounds[0]]  # southwest corner (miny, minx)
            ne = [bounds[3], bounds[2]]  # northeast corner (maxy, maxx)
            selected_map.fit_bounds([sw, ne])

            # Add controls to the map
            selected_map.add_control(LayersControl(position='topright'))
            selected_map.add_control(FullScreenControl())

            # Function to confirm and rename the output to AREA_selection
            def confirm_selection(button):
                global AREA_selection
                AREA_selection = selected_gdf
                display(HTML("<b>The selected area has been confirmed as AREA_selection</b>"))

            # Create a button for confirming the selection
            confirm_button = Button(description="CONFIRM")
            confirm_button.on_click(confirm_selection)

            # Display the map, button, and area in hectares
            display(VBox([HTML("<b>If you are happy with this AREA please confirm before continuing</b>"), selected_map, HTML(f"Selected area: {area_ha:.2f} hectares")]))
        else:
            display(HTML("No area selected."))
    else: 
        # display(HTML("<b> <span style='color:orange'> No visuals </span>: Selected area was not drawn from map. Below is the currently selected area details</b>"))
        selected_area = polygon_selected()
        
        if selected_area is not None and not selected_area.empty:
            display_geopandas_df_selection(selected_area)
        else:
            display(HTML("No area selected."))
        return None
    
# # Example: Visualize the selected area stored in 'selected_area' from PART 2
# visualize_selected_area(selected_area)



# ================================= Add a buffer including your site ========================================== 

# Global variable for buffer distance
buffer_distance = 100


# Radio buttons widget for selecting buffer distance
buffer_distance_options = RadioButtons(
    options=[('100m', 100), ('500m', 500), ('1km', 1000), ('5km', 5000), ('10km', 10000), ('25km', 25000), ('50km', 50000), ('CUSTOM', 'CUSTOM')],
    value=100,
    description='Buffer Distance:',
    layout=Layout(width='300px')  # Set the width of the widget
)


def active_buffer():
    selected_buffer = get_global_result("buffer_distance", RESULTS)
    if selected_buffer:
        in_km = int(selected_buffer)/1000
        in_meters = int(selected_buffer)
        buffer_to_display = f"{in_km} km ({in_meters} meters)"
    else:
        buffer_to_display = "Not Selected"
        
    html = widgets.HTML()
    docs = f""" <p style='color:black'>  Buffer distance:  <b style='color:'>  {buffer_to_display} </b>  </p>"""
    html.value = docs
    display(html)
    

# Function to handle custom buffer distance input
def on_custom_buffer_distance_change(change):
    buffer_distance = change['new'] * 1000  # Convert km to meters
    set_global_result("buffer_distance", buffer_distance, RESULTS)


# Function to handle buffer distance selection
def on_buffer_distance_change(change):
    if change['new'] == 'CUSTOM':
        custom_buffer_distance.layout.display = ''  # Show custom distance input
    else:
        custom_buffer_distance.layout.display = 'none'  # Hide custom distance input
        if change.get("new"):
            buffer_distance = change.get("new")
            set_global_result("buffer_distance", buffer_distance, RESULTS) 


# Function to create buffer and display it on a map
def create_and_display_buffer_include_selection(area_gdf, buffer_distance):
    
     # Check if area_gdf is a GeoPandas DataFrame
    if isinstance(area_gdf, gpd.GeoDataFrame):
        selected_geom = area_gdf.iloc[0].geometry
        
    # If area_gdf is a dictionary representing a geometry
    elif isinstance(area_gdf, dict) and 'type' in area_gdf and 'coordinates' in area_gdf:
        # Convert dictionary to a GeoPandas DataFrame
        geom = shape(area_gdf)
        area_gdf = gpd.GeoDataFrame({'geometry': [geom]})
        selected_geom = area_gdf.iloc[0].geometry
    else:
        raise ValueError("Invalid input: area_gdf must be a GeoPandas DataFrame or a valid GeoJSON-like dictionary.")
        
    
    if area_gdf is not None and not area_gdf.empty:
        # Use the geometry of the first (and only) feature in the GeoDataFrame
        selected_geom = area_gdf.iloc[0].geometry
        
        # Reproject the geometry to EPSG:3857 for buffering in meters
        proj = pyproj.Transformer.from_crs('epsg:4326', 'epsg:3857', always_xy=True).transform
        reprojected_geom = transform(proj, selected_geom)
        
        # Create buffer around the reprojected geometry
        buffer_geom = reprojected_geom.buffer(buffer_distance)
        
        # Reproject the buffer back to EPSG:4326
        proj_back = pyproj.Transformer.from_crs('epsg:3857', 'epsg:4326', always_xy=True).transform
        buffer_geom = transform(proj_back, buffer_geom)
        
        # Convert the buffer to a GeoDataFrame
        AREA_BufferA = gpd.GeoDataFrame({'geometry': [buffer_geom]}, crs='epsg:4326')
        
        # Create GeoData layer for the selected area
        selected_geo_data = GeoData(
            geo_dataframe=area_gdf,
            style={
                "color": "black",
                "fillColor": "#3366cc",
                "opacity": 0.05,
                "weight": 1.9,
                "dashArray": "2",
                "fillOpacity": 0.6,
            },
            hover_style={"fillColor": "red", "fillOpacity": 0.2},
            name="Selected Area",
        )
        
        # Create GeoData layer for the buffer area
        buffer_geo_data = GeoData(
            geo_dataframe=AREA_BufferA,
            style={
                "color": "black",
                "fillColor": "#ffcc00",
                "opacity": 0.5,
                "weight": 1.9,
                "dashArray": "2",
                "fillOpacity": 0.3,
            },
            hover_style={"fillColor": "red", "fillOpacity": 0.2},
            name="Buffer Area",
        )
        
        # Calculate the center of the buffer area
        bounds = AREA_BufferA.total_bounds  # returns (minx, miny, maxx, maxy)
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
        
        # Create a map centered on the buffer area
        buffer_map = Map(center=center, zoom=10, basemap=basemaps.Esri.WorldImagery, layout=Layout(height='600px'))
        
        # Add GeoData layers to the map
        buffer_map.add_layer(selected_geo_data)
        buffer_map.add_layer(buffer_geo_data)
        
        # Fit map to bounds
        sw = [bounds[1], bounds[0]]  # southwest corner (miny, minx)
        ne = [bounds[3], bounds[2]]  # northeast corner (maxy, maxx)
        buffer_map.fit_bounds([sw, ne])
        
        # Add controls to the map
        buffer_map.add_control(LayersControl(position='topright'))
        buffer_map.add_control(FullScreenControl())
        
        # Display the map
        display(buffer_map)
        
        # Function to confirm and  buffer selection
        def confirm_buffer_selection(button):
            # AREA_selection = area_gdf
            # geometry = AREA_BufferA.loc[0, 'geometry']
            geometry = AREA_BufferA.iloc[0]['geometry']
            # Convert to GeoJSON-like dictionary
            buffered_area_togeojson = geometry.__geo_interface__
            set_global_result("global_selected_area", buffered_area_togeojson, RESULTS)


        # Create a button for confirming the buffer as the selection
        confirm_selection_button = Button(description="CONFIRM BUFFER")
        confirm_selection_button.on_click(confirm_buffer_selection)

        # Display the instructions, button, and map
        instructions = HTML("<b>If applied buffer to site selection is good, click  <span style='color:orange'> CONFIRM BUFFER </span> button below. <br> If more buffer is needed change the value selected from 'include_buffer()'. </b>")
        display(VBox([instructions, confirm_selection_button]))

    else:
        display(HTML("No area selected."))



# Function to confirm buffer distance selection
def on_confirm_button_clicked(b):
    selected_buffer = get_global_result("buffer_distance", RESULTS)
    confirmed_buffer_distance = selected_buffer
    set_global_result("confirmed_buffer_distance", confirmed_buffer_distance, RESULTS)
    

    

style = {'description_width': 'initial'}          
# Text box for custom buffer distance
custom_buffer_distance = BoundedFloatText(
    value=1,
    min=0.001,
    max=100,
    step=0.1,
    description='Custom (km): Maximum = 100km',
    # layout=Layout(width='200px')  # Set the width of the widget
       layout=Layout(width='40%'),
        style=style
)
custom_buffer_distance.layout.display = 'none'  # Hide initially   
        
# Button to confirm buffer distance selection
confirm_button = Button(description="Confirm Buffer Distance")
confirm_button.on_click(on_confirm_button_clicked) 


        
def include_buffer():
    """When called will show options to add buffer to selected site including the site selection."""
    global_area_selection_type = get_global_result("global_area_selection_type", RESULTS)
    if global_area_selection_type and (global_area_selection_type != "Draw"):
        html = widgets.HTML()
        docs = f""" <b style='color:black'>  Buffers can only be applied on map-drawn areas. Draw area on map using 'notebook_dropdowns.map_and_select_area(polygon_select)' to apply buffer  </b>"""
        html.value = docs
        display(html)
        return None 
    # Display widgets
    display(VBox([buffer_distance_options, custom_buffer_distance, confirm_button]))
    # Observe changes
    buffer_distance_options.observe(on_buffer_distance_change, names='value')
    custom_buffer_distance.observe(on_custom_buffer_distance_change, names='value')
    # Initialize buffer_distance variable
    buffer_distance = 100
    confirmed_buffer_distance = buffer_distance  # Initialize confirmed buffer distance
    
    


def buffer_include_selection():
    """Adds set buffer to stored area selection including"""
    # Fetch set selected area 
    polygon_select = polygon_selected()
    # Fetch set selected buffer
    selected_buffer = get_global_result("buffer_distance", RESULTS)
    selected_global_polygon_type = get_global_result("global_selected_polygon_type", RESULTS)
    global_area_selection_type = get_global_result("global_area_selection_type", RESULTS)
    
    # Check if polygon_select is not None and selected_buffer is set
    if polygon_select is not None and selected_buffer:
        # If polygon_select is a GeoPandas DataFrame
        if isinstance(polygon_select, gpd.GeoDataFrame):
            if not polygon_select.empty:
                # Convert the first geometry to GeoJSON-like dict
                # polygon_select = convert_to_geojson(polygon_select)
                polygon_select = mapping(polygon_select.iloc[0].geometry)
            else:
                print("The GeoDataFrame is empty. No valid area selected.")
                return None
        # Pass the (possibly converted) polygon_select to create_and_display_buffer_include_selection
        if global_area_selection_type and (global_area_selection_type == "Draw"):
            create_and_display_buffer_include_selection(polygon_select, selected_buffer)
        else:
            
            # create_and_display_buffer_include_selection(polygon_select, selected_buffer)
            print("Buffers can only be applied on map drawn areas for now. Draw area on map to apply buffer")
            return None                               
    else:
        print("No area or buffer selection set")
        return None


    
    
    
# Function to create AREA_BufferB by removing AREA_selection from AREA_BufferA
def create_and_display_buffer_exclude_selection(area_gdf, buffer_distance):

    global AREA_BufferB  # Declare AREA_BufferB as a global variable to store the new buffer area
     # Check if area_gdf is a GeoPandas DataFrame
    if isinstance(area_gdf, gpd.GeoDataFrame):
        selected_geom = area_gdf.iloc[0].geometry
        
    # If area_gdf is a dictionary representing a geometry
    elif isinstance(area_gdf, dict) and 'type' in area_gdf and 'coordinates' in area_gdf:
        # Convert dictionary to a GeoPandas DataFrame
        geom = shape(area_gdf)
        area_gdf = gpd.GeoDataFrame({'geometry': [geom]})
        selected_geom = area_gdf.iloc[0].geometry
    else:
        raise ValueError("Invalid input: area_gdf must be a GeoPandas DataFrame or a valid GeoJSON-like dictionary.")
        
    
    if area_gdf is not None and not area_gdf.empty:
        # Use the geometry of the first (and only) feature in the GeoDataFrame
        selected_geom = area_gdf.iloc[0].geometry
        
        # Reproject the geometry to EPSG:3857 for buffering in meters
        proj = pyproj.Transformer.from_crs('epsg:4326', 'epsg:3857', always_xy=True).transform
        reprojected_geom = transform(proj, selected_geom)
        
        # Create buffer around the reprojected geometry
        buffer_geom = reprojected_geom.buffer(buffer_distance)
        
        # Reproject the buffer back to EPSG:4326
        proj_back = pyproj.Transformer.from_crs('epsg:3857', 'epsg:4326', always_xy=True).transform
        buffer_geom = transform(proj_back, buffer_geom)
        
        # Convert the buffer to a GeoDataFrame
        AREA_BufferA = gpd.GeoDataFrame({'geometry': [buffer_geom]}, crs='epsg:4326')
        bufferA_geom = AREA_BufferA.iloc[0].geometry
    
        # Perform the difference operation
        bufferB_geom = bufferA_geom.difference(selected_geom)

        # Convert the result to a GeoDataFrame
        AREA_BufferB = gpd.GeoDataFrame({'geometry': [bufferB_geom]}, crs='epsg:4326')
    
        # Create GeoData layer for AREA_BufferB
        bufferB_geo_data = GeoData(
            geo_dataframe=AREA_BufferB,
            style={
                "color": "black",
                "fillColor": "#00cc66",
                "opacity": 0.5,
                "weight": 1.9,
                "dashArray": "2",
                "fillOpacity": 0.3,
            },
            hover_style={"fillColor": "red", "fillOpacity": 0.2},
            name="Buffer B Area",
        )
    
        # Calculate the center of the buffer area
        bounds = AREA_BufferB.total_bounds  # returns (minx, miny, maxx, maxy)
        center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    
        # Create a map centered on the buffer area
        bufferB_map = Map(center=center, zoom=10, basemap=basemaps.Esri.WorldImagery, layout=Layout(height='600px'))
    
        # Add GeoData layer to the map
        bufferB_map.add_layer(bufferB_geo_data)
    
        # Fit map to bounds
        sw = [bounds[1], bounds[0]]  # southwest corner (miny, minx)
        ne = [bounds[3], bounds[2]]  # northeast corner (maxy, maxx)
        bufferB_map.fit_bounds([sw, ne])
    
        # Add controls to the map
        bufferB_map.add_control(LayersControl(position='topright'))
        bufferB_map.add_control(FullScreenControl())
    
        # Display the map
        display(bufferB_map)

        # Function to confirm and  buffer selection
        def confirm_buffer_selection(button):
            # geometry = AREA_BufferB.loc[0, 'geometry']
            geometry = AREA_BufferB.iloc[0]['geometry']
            # Convert to GeoJSON-like dictionary
            buffered_area_togeojson = geometry.__geo_interface__
            set_global_result("global_selected_area", buffered_area_togeojson, RESULTS)


        # Create a button for confirming the buffer as the selection
        confirm_selection_button = Button(description="CONFIRM BUFFER")
        confirm_selection_button.on_click(confirm_buffer_selection)

        # Display the instructions, button, and map
        instructions = HTML("<b>If applied buffer excluding site selection is good, click  <span style='color:orange'> CONFIRM BUFFER </span> button below. <br> If more buffer is needed change the value selected from 'include_buffer()'. </b>")
        display(VBox([instructions, confirm_selection_button]))




def buffer_exclude_selection():
    """Adds set buffer to stored area selection excluding the selection"""
    # Fetch set selected area 
    polygon_select = polygon_selected()
    # Fetch set selected buffer
    selected_buffer = get_global_result("buffer_distance", RESULTS)
    selected_global_polygon_type = get_global_result("global_selected_polygon_type", RESULTS)
    global_area_selection_type = get_global_result("global_area_selection_type", RESULTS)
    
    # Check if polygon_select is not None and selected_buffer is set
    if polygon_select is not None and selected_buffer:
        # If polygon_select is a GeoPandas DataFrame
        if isinstance(polygon_select, gpd.GeoDataFrame):
            if not polygon_select.empty:
                # Convert the first geometry to GeoJSON-like dict
                # polygon_select = convert_to_geojson(polygon_select)
                polygon_select = mapping(polygon_select.iloc[0].geometry)
            else:
                print("The GeoDataFrame is empty. No valid area selected.")
                return None
        # Pass the (possibly converted) polygon_select to create_and_display_buffer_exclude_selection
        if global_area_selection_type and (global_area_selection_type == "Draw"):
            create_and_display_buffer_exclude_selection(polygon_select, selected_buffer)
        else:
         
            # create_and_display_buffer_exclude_selection(polygon_select, selected_buffer)
            print("Buffers can only be applied on map drawn areas for now. Draw area on map to apply buffer")
            return None                               
    else:
        print("No area or buffer selection set")
        return None

















