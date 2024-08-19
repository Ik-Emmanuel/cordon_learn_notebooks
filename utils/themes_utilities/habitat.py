'''
Description: This file contains a set of python functions for loading
the LW habitat map with WDC data.
'''

habitat_dict = {3:'SemiNatural grass',
4:'Juncus rushes',
5:'Molinia grassland',
9:'Young plantations/Felled/Coppice',
10:'Woodland and scrub',
12:'Broadleaved woodland',
16:'Coniferous woodland',
23:'Ulex dominated scrub',
35:'Acid grassland',
38:'Neutral grassland',
41:'Calcareous grassland',
44:'Improved grassland',
45:'Marsh/marshy grassland',
50:'Bracken',
58:'Dry dwarf shrub heath',
61:'Wet dwarf shrub heath',
70:'Blanket sphagnum bog',
71:'Raised sphagnum bog',
72:'Modified bog',
78:'Fen',
85:'Peat - bare',
86:'Swamp',
90:'Open Water',
106:'Intertidal vegetation Generic',
107:'Intertidal Bare Generic',
119:'Saltmarsh',
128:'Sand dune',
130:'Dune grassland',
131:'Dune heath',
132:'Dune scrub',
134:'Maritime cliff and slope (unvegetated)',
135:'Maritime cliff and slope (vegetated)',
142:'Natural rock exposure and waste',
143:'Inland cliff',
146:'Scree',
150:'Other rock exposure',
155:'Quarry',
159:'Arable crops',
200:'Artificial bare surfaces',
201:'Natural bare surfaces',
202:'Semi-natural herbaceous vegetation (Unclassified)'}


def load_habitat_map(date, geom_extent):
    """
    Load habitat map for specified extent and date
    Last modified: Sept 2023
    """
    import datacube
    import datetime as dt
    dc = datacube.Datacube()
    
    # Habitat map only avaialable from 2020
    year = dt.datetime.strptime(date, "%Y-%m-%d").strftime("%Y")
    if int(year) < 2020:
        year = '2020'
    elif int(year) > int(dt.datetime.now().strftime("%Y"))-1:
        year = str(int(dt.datetime.now().strftime("%Y"))-1)
    
    query = {'product': 'lw_habitats_lw',
             'geopolygon': geom_extent,
             'time': (year+"-01-01",year+"-12-31"),
             'output_crs': 'epsg:27700',
             'resolution': (-10,10)}
    habitat_map = dc.load(**query)
    habitat_map = habitat_map.where(habitat_map != 0)
    # # When using epsg other than 4326, latitude and longitude are renames y and x.
    # # Let's correct that then the notebook run more smoothly
    habitat_map = habitat_map.rename({'x': 'longitude', 'y': 'latitude'})
    habitat_map = habitat_map.squeeze(dim='time')
    return habitat_map
