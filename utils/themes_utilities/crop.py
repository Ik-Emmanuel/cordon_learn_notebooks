'''
Description: This file contains a set of python functions for the near-real time crop monitoring
study cases.
'''
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


crop_colours = {"Winter wheat":"gold", 
                 "Rapeseed":"yellow", 
                 "Winter barley":"mediumseagreen", 
                 "Spring barley":"darkseagreen",
                 "Spring wheat":"khaki",
                 "Maize":"darkgreen",
                 "Other":"lightgrey",
                 "Grass":"yellowgreen"}


def rapeseed_study_case_plot(median_VH=None, median_VV=None, median_Ratio=None):        
    import datetime as dt
    import matplotlib.dates as mdates
    from matplotlib.dates import DateFormatter
    
    plt.figure(figsize=(16, 16))
    img = plt.imread("../img/rapeseed_planet.png")
    plt.axis('off')
    plt.title("Planet images available around key growth stage dates")
    plt.imshow(img)
    
    fig, (ax1, ax2, ax3) = plt.subplots(3,figsize=(18,18))
    # set title
    fig.suptitle('Evolution of SAR-C signal in the rapeseed parcel during the whole crop season', y=0.9)
    # set date format for the a axises
    dates=[dt.datetime.strptime(d,'%Y-%m-%d').date() for d in median_VV.time.values]

    for subplot in [ax1, ax2, ax3]:
        subplot.axvline(x = dt.date(2017, 9, 15), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2017, 10, 21), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 2, 1), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 4, 1), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 4, 25), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 5, 10), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 5, 25), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 7, 7), color = 'black',linewidth=1.5)
        subplot.axvline(x = dt.date(2017, 8, 18), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2017, 9, 19), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2017, 10, 16), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2017, 10, 27), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 2, 7), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 3, 7), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 4, 5), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 5, 5), color = 'y',linewidth=1.5)
        subplot.axvline(x = dt.date(2018, 5, 15), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 5, 22), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 6, 6), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 6, 22), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 6, 26), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 7, 3), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 7, 8), color = 'lightcoral',linewidth=1)
        subplot.axvline(x = dt.date(2018, 7, 19), color = 'lightcoral',linewidth=1)

    # Plot the  ratio
    ax1.plot(dates, median_Ratio.values, marker="o")
    ax1.set_ylim([-16, -2])
    ax1.grid(visible=True, which='major', axis='y')
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax1.tick_params('x',labelrotation=25)
    ax1.set_ylabel("Ratio")

    # Plot the VH backscatter
    ax2.plot(dates,median_VH.values, marker="o")
    ax2.set_ylim([-26, -5])
    ax2.grid(visible=True, which='major', axis='y')
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax2.tick_params('x',labelrotation=25)
    ax2.set_ylabel("VH backscatter")

    # Plot the VV backscatter
    ax3.plot(dates, median_VV.values, marker="o")
    ax3.set_ylim([-20, -2])
    ax3.grid(visible=True, which='major', axis='y')
    ax3.xaxis.set_major_locator(mdates.MonthLocator())
    ax3.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    ax3.tick_params('x',labelrotation=25)
    ax3.set_ylabel("VV backscatter")



def play_crop_rotation(field_plots):
    import time
    from IPython import display
    import pylab as pl
    
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_axis_off()

    for year in ['2018','2019', '2020', '2021','2018','2019', '2020', '2021','2018','2019', '2020', '2021']:
        legend_elements=[]
        for ctype, data in field_plots.groupby('Year_'+year):
            color = crop_colours[ctype]
            legend_elements.append(Patch(facecolor=color, label=ctype))
            data.plot(color=color,
                      ax=ax,
                      label=ctype)
        ax.legend(handles=legend_elements, loc='upper right')
        ax.set_title(year, fontsize=20)
        display.display(pl.gcf())
        display.clear_output(wait=True)
        time.sleep(1.5)


def crop_type_widget():
    import ipywidgets as widgets
    crop_widget = widgets.RadioButtons(
        options=['All','Winter wheat', 'Rapeseed', 'Winter barley', 
                 'Spring barley', 'Spring wheat', 'Maize', 'Grass', 'Other' ],
        layout={'width': 'max-content'}, # If the items' names are long
        description='Crop type:',
        disabled=False
    )
    return crop_widget


def report_crop_type_area(field_plots, crop_type):
    if crop_type != 'All':
        selected_plots = field_plots[field_plots["Year_"+str(year)]==crop_type]
    else:
        selected_plots = field_plots
    
    crop_types_area = {}
    for year in range(2018, 2022):
        crop_types_area[str(year)] = {}
        for crop in selected_plots["Year_"+str(year)].unique():
            area = selected_plots[selected_plots["Year_"+str(year)]==crop].area.sum()/10000
            crop_types_area[str(year)][crop] = area
    
    return crop_types_area