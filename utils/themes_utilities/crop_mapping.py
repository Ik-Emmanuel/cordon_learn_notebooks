'''
Description: This file contains a set of python functions for computing
remote sensing crop mapping in WDC.
'''

import pymannkendall as mk

def grass_level1(year, VH):
    minVH_feb_aug = VH.sel(time=slice(str(year)+'-02-01', str(year)+'-08-31')).min()
    maxVH_feb_aug = VH.sel(time=slice(str(year)+'-02-01', str(year)+'-08-31')).max()
    diffVH = maxVH_feb_aug-minVH_feb_aug
    
    if( diffVH <= 5 ):
        types="Grass"
        step="grass_level1"
        crop="Grass"
    else:
        types=None
        step=None
        crop=None
    
    #print(crop, step)
    return crop, step


def grass_level2(year, VHVV, VH):
    medVHVV_may = VHVV.sel(time=slice(str(year)+'-05-01', str(year)+'-05-31')).median()
    minVHVV_may = VHVV.sel(time=slice(str(year)+'-05-01', str(year)+'-05-31')).min()
    medVHVV_jul = VHVV.sel(time=slice(str(year)+'-07-01', str(year)+'-07-31')).median()
    minVHVV_jul = VHVV.sel(time=slice(str(year)+'-07-01', str(year)+'-07-31')).min()

    diffVHVVwinter = medVHVV_may-minVHVV_jul
    diffVHVVspring = medVHVV_jul-minVHVV_may
    
    print(diffVHVVwinter)
    print(diffVHVVspring)
    
#     minVH = VH.sel(time=slice(str(year)+'-05-01', str(year)+'-07-31')).min()
#     maxVH = VH.sel(time=slice(str(year)+'-05-01', str(year)+'-07-31')).max()
    minVH = VH.sel(time=slice(str(year)+'-05-01', str(year)+'-08-31')).min()
    maxVH = VH.sel(time=slice(str(year)+'-05-01', str(year)+'-08-31')).max()
    diffVH = maxVH-minVH
    print(diffVH)
    
    minVHVV = VHVV.sel(time=slice(str(year)+'-03-01', str(year)+'-08-31')).min()
    maxVHVV = VHVV.sel(time=slice(str(year)+'-03-01', str(year)+'-08-31')).max()
    diffVHVV = maxVHVV-minVHVV
    print(diffVHVV)
    
    # changed 6 for 8
    #if( (diffVH < 8) & (diffVHVVspring < 2) & (diffVHVVwinter < 2) ):
    if( (diffVH < 8) | ((diffVHVV < 7) & (diffVH < 9)) ):
        types="Grass"
        step="grass_level2"
        crop="Grass"
    else:
        types=None
        step=None
        crop=None
    
    print(crop, step)
    return crop, step


def winter_spring(MK_decFeb, MK_febApr, MK_aprJun, MK_junAug):
    if( (MK_decFeb.p<0.01) & (MK_decFeb.slope>0) & (MK_febApr.p<0.01) & (MK_febApr.slope>0) &
       (MK_aprJun.p<0.01) & (MK_aprJun.slope>0)): # if positive trend between 1st Dec and mid May
        if ((MK_junAug.p<0.01) & (MK_junAug.slope>0)):
            step="ws_level1"
            crop="Spring" 
            types=None
        else:
            step="ws_level1"
            crop="Winter" 
            types=None

    if( (MK_decFeb.p<0.01) & (MK_decFeb.slope<0) & (MK_febApr.p<0.01) & (MK_febApr.slope<0) &
       (MK_aprJun.p<0.01) & (MK_aprJun.slope<0)): 
        # if negative trend between 1st Dec and mid May
        step="ws_level2"
        crop="Spring" 
        types=None

    if( (MK_decFeb.p < 0.01) & (MK_decFeb.slope<0) & (MK_febApr.p < 0.01) & (MK_febApr.slope< 0) &
       (MK_aprJun.p < 0.01) & (MK_aprJun.slope>0)): 
        # if negative trend between 1st Dec and 1st April and increase from april to mid May
        crop="Spring"
        step="ws_level3"
        types=None

    if( (MK_decFeb.p < 0.01) & (MK_decFeb.slope>0) & (MK_febApr.p < 0.01) & (MK_febApr.slope>0) &
       (MK_aprJun.p < 0.01) & (MK_aprJun.slope<0)): 
        # if positive trend between 1st Dec and 1st April and decrease from 1st April to mid May
        crop="Spring"
        step="ws_level4"
        types=None
        
    else:
        crop=None
        step=None
        types=None
    
    print(crop, step)
    return crop, step


def winter1(year, MK_aprJun, MK_febApr, VHVV):
    if( (MK_aprJun.p < 0.01) & (MK_aprJun.slope>0) & (MK_febApr.p < 0.01) & 
       ((MK_febApr.slope>0) | (MK_febApr.slope<0))):

        period_full=slice(str(year)+'-03-01', str(year)+'-10-31')
        dateMax_VHVV = VHVV.sel(time=period_full).time[VHVV.sel(time=period_full).argmax()].values

        period_midApr=slice(str(year)+'-03-01', str(year)+'-04-15')
        dateMin_VHVV = VHVV.sel(time=period_midApr).time[VHVV.sel(time=period_midApr).argmin()].values

        if( (dateMin_VHVV < str(year)+'-04-01') & (dateMax_VHVV<= str(year)+'-07-31')):
            crop="Winter"
            step="ws_level10"
            types=None
        else:
            crop=None
            step=None
            types=None

    else:
            crop=None
            step=None
            types=None
    
    #print(crop, step)
    return crop, step


def winter2(MK_mayJun, MK_decJun, MK_aprJun, MK_junAug, MK_janJun, MK_junJul):
    if( (MK_mayJun.p != None) & (MK_decJun.p < 1e-5) & (MK_decJun.slope>0.01) & (MK_mayJun.p < 1e-5) &
       (MK_mayJun.slope > (-0.1)) ): 
        # if positive trend between 1st Dec and mid May and no sudden decrease in May
        crop="Winter"
        step="ws_level26"
        types=None

    elif( (MK_aprJun.p != None) & (MK_decJun.p < 1e-5) & (MK_decJun.slope >0) & (MK_aprJun.p < 1e-5) &
         (MK_aprJun.slope >0) & (MK_junAug.p < 1e-5) & (MK_junAug.slope < 0) ):
        crop="Winter"
        step="ws_level27"
        types=None

    elif( (MK_aprJun.p != None) & (MK_decJun.p < 1e-3) & (MK_decJun.slope >0) & (MK_aprJun.p < 1e-3) &
         (MK_aprJun.slope >0) & (MK_junAug.p < 1e-3) & (MK_junAug.slope < 0)):
        crop="Winter"
        step="ws_level28"
        types=None
    
    elif( (MK_aprJun.p != None) & (MK_decJun.p < 1e-3) & (MK_decJun.slope >0) & (MK_aprJun.p < 1e-3) &
         (MK_aprJun.slope >0) & (MK_junJul.p < 0.01) & (MK_junJul.slope < 0)):
        crop="Winter"
        step="ws_level28b"
        types=None
    
#     elif( (MK_aprJun.p != None) & (MK_decJun.p < 1e-3) & (MK_decJun.slope >0) & (MK_junAug.p < 1e-3) & 
#          (MK_junAug.slope < 0)):
    elif( (MK_aprJun.p != None) & (MK_janJun.p < 1e-5) & (MK_janJun.slope >0) & (MK_junAug.p < 0.05) & 
         (MK_junAug.slope < 0)):
        crop="Winter"
        step="ws_level29"
        types=None

    elif(MK_mayJun.p != None):
        crop="Spring"
        step="ws_level29"
        types=None
    else:
        crop=None
        step=None
        types=None
    
    #print(crop, step)
    return crop, step


def crop_seasonality(median_VH, median_VHVV):
    year = int(median_VH.time[100].values.item()[0:4])
    print('Processing '+str(year)+' crop season...')
    
    crop=None
    step=None

    crop, step = grass_level1(year, median_VH)

    if (crop==None):
        crop, step = grass_level2(year, median_VHVV, median_VH)

    if (crop==None):
        MK_decFeb = mk.original_test(median_VHVV.sel(time=slice(str(year-1)+'-12-01', str(year)+'-01-31')).values)
        MK_febApr = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-02-01', str(year)+'-03-31')).values)
        MK_aprJun = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-04-01', str(year)+'-05-15')).values)
        MK_junAug = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-06-01', str(year)+'-07-31')).values)
        
        print("MK_decFeb :", MK_decFeb)
        print("MK_febApr :", MK_febApr)
        print("MK_aprJun :", MK_aprJun)
        print("MK_junAug :", MK_junAug)
        
        crop, step = winter_spring(MK_decFeb, MK_febApr, MK_aprJun, MK_junAug)

    if (crop==None):
        crop, step = winter1(year, MK_aprJun, MK_febApr, median_VHVV)

    if (crop==None):
        MK_decJun = mk.original_test(median_VHVV.sel(time=slice(str(year-1)+'-12-01', str(year)+'-05-15')).values)
        MK_mayJun = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-05-01', str(year)+'-05-31')).values)
        MK_janJun = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-01-01', str(year)+'-05-15')).values)
        MK_junJul = mk.original_test(median_VHVV.sel(time=slice(str(year)+'-06-01', str(year)+'-06-30')).values)
        
        print("MK_decJun :", MK_decJun)
        print("MK_mayJun :", MK_mayJun)
        print("MK_janJun :", MK_janJun)
        print("MK_junJul :", MK_junJul)
        
        crop, step = winter2(MK_mayJun, MK_decJun, MK_aprJun, MK_junAug, MK_janJun, MK_junJul)
    
    print(crop, step)
    return crop, step
