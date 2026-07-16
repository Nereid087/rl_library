# -*- coding: utf-8 -*-
"""
Created on Thu Dec 21 10:03:01 2023

@author: bhendrikx
"""
import geopandas as gpd
import pandas as pd
import rasterio
import os
import numpy as np
import math
import contextily as cx
import matplotlib.pyplot as plt
from matplotlib_scalebar.scalebar import ScaleBar
from rasterio.plot import show
import matplotlib.colors as colors
import statistics
#Naam locatie 
folder_name = "Ziendeweg"
#Maak folders aan
absolute_path = os.path.dirname(__file__)
input_folder = absolute_path + "\\input\\" + folder_name
output_folder = absolute_path + "\\output\\"
if os.path.exists(output_folder + folder_name):
    output_folder = absolute_path + "\\output\\" + folder_name
else:
    output_folder = os.mkdir(output_folder + folder_name)
#Maak lijsten aan
Zs = []
Xs = [] 
Ys = []
Names = []
ZsDEM = []
difs = []
#fig en ax aanmaken voor de te maken kaart
fig, ax = plt.subplots()
#header definiëren voor gcp.txt
header = ['Naam', 'X', 'Y', 'Z', '']
#inlezen van gcp.txt
gcp_file = pd.read_csv(input_folder + "\\gcp.txt", sep = ";")
gcp_file.columns = header
print(gcp_file)
#Enkel de controlepunten beginnend met "CP" in de naam opslaan
for index, row in gcp_file.iterrows():
    if gcp_file["Naam"].loc[index][:2] == 'CP':
        #TODO header check doen
        print(gcp_file["Naam"].loc[index][:2])
        Zs.append(gcp_file["Z"].loc[index])
        Ys.append(gcp_file["Y"].loc[index])
        Xs.append(gcp_file["X"].loc[index])
        Names.append(gcp_file["Naam"].loc[index])
#CSV met de te gebruiken gcp-data opslaan
points_data = pd.DataFrame({"Name": Names, "X": Xs, "Y": Ys, "Z": Zs})
points_data.to_csv(output_folder + "\\points_data.csv")    
#Inlezen van de te gebruiken puntendata
points_csv = pd.read_csv(output_folder + "\\points_data.csv", sep = ",")

#Puntendata omzetten in een shapefile
points = gpd.GeoDataFrame(
    geometry=gpd.points_from_xy(points_csv.X, points_csv.Y, crs = 'epsg:28992'), data=points_csv
)
points.to_file(output_folder + "\\points.shp")
print(points)

#Inlezen van het dtm.tif bestand
dem = rasterio.open(input_folder + '\\dtm.tif' , mode = 'r+')
#Waaedes uit het dtm.tif bestand opslaan in een array
dem_data = dem.read(1)

#Definitie om een kaart te maken 
def generate_map(ax, raster, shapefile, dataframe, cmap, label, title, ticklabels, norm, row, col, tick_var):
    #inlezen van het raster
    src = rasterio.open(raster, mode = 'r')
    #raster omzetten in een array
    arr = src.read(1)#.astype(np.int)
    #Nodata values definiëren
    arr = np.where(arr==-9999.0,np.nan,arr)
    arr1 = arr[~np.isnan(arr)]
    
    #De minimale, maximale en verscheidene statistische waardes bepalen
    arr_min = np.min(arr1)
    arr_max = np.max(arr1)
    arr_q05 = np.quantile(a=arr1, q=0.05)
    arr_q25 = np.quantile(a=arr1, q=0.25)
    arr_q50 = np.quantile(a=arr1, q=0.50)
    arr_q75 = np.quantile(a=arr1, q=0.75)
    arr_q95 = np.quantile(a=arr1, q=0.95)
    
    #Opmaak axes
    ax.patch.set_edgecolor('black')  
    ax.patch.set_linewidth('5')  
    
    #Hidden image maken t.b.v. de colorbar
    image_hidden = ax.imshow(arr, cmap = cmap)
    #begrenzing voor de colorbar
    image_hidden.set_clim(arr_q05, arr_q95)
    #Definiëren van de te plotten image
    image = rasterio.plot.show(arr, transform= src.transform, ax = ax, cmap = cmap, vmin = arr_q05, vmax = arr_q95)
    
    #Instellingen colorbar
    cbar = fig.colorbar(image_hidden, ax=ax, extend = "both")
    cbar.ax.tick_params(labelsize = 8)
    cbar.set_label(label, rotation = 270, fontsize= 12, labelpad = 40)
    
    #Inzoomen op de puntenlaag
    minx, miny, maxx, maxy = points.total_bounds
    
    #Limiet voor het inzoomen op de puntenlaag
    ax.set_xlim(minx - 100, maxx + 100)
    ax.set_ylim(miny - 100, maxy + 100)
    
    #Plotten van de puntenlaag boven het raster
    points.plot(ax=ax, color = 'black', edgecolor = 'black', legend = True, linewidth = 0.5)
    
    #Axes uitzetten
    ax.set_axis_off()
    
    #Scalebar toevoegen
    ax.add_artist(ScaleBar(
        dx=1,
        units = "m",
        dimension = "si-length",
        length_fraction = 0.25,
        font_properties = {'size': 12 },
        location = "lower left")
        )
    #Totel voor de kaart toevoegen
    ax.set_title(title, fontsize = 42, color='black', weight = "bold") 

#Definitie aanroepen om een kaart te maken
generate_map(ax, input_folder + '\\dtm.tif', points, points_csv, "terrain", "Hoogte (m)", "", None, None, 0,0, None) 
#Kaart opslaan   
plt.savefig(output_folder + "\\dtm_map.png")   

#Op de locatie van de punten uit de puntenlaag de rasterwaardes inlezen
for ind, row in points.iterrows():
    start_coords = list([row.geometry][0].coords)[0]
    print(start_coords)
    for val in dem.sample([(start_coords[0], start_coords[1])]):
        print(float(val))
        ZsDEM.append(float(val))

#rasterwaardes toevoegen aan de puntenlaag
points["Z_DSM"] = ZsDEM
print(points)

#Verschil tussen de z-waardes uit de de puntenlaag (gcp.txt oorspronkelijk) en de het raster bepalen
for index, row in points.iterrows():
    print(points["Z_DSM"].loc[index])
    difs.append(points["Z_DSM"].loc[index]-points["Z"].loc[index]) 

#Verschil opslaan in de puntenlaag
points["Difference_Z"] = difs
print(difs)
#De mean en standard deviatiom bepalen
mean_val = statistics.mean(difs)
std_val = statistics.stdev(difs)

#Ststistische data opslaan in tekstbestand 
with open(output_folder + "\\stats.txt", "w+") as f:
    text = "Mean: " + str(mean_val) + "\n" + "Standard deviation: " + str(std_val)
    f.write(text)
    f.close()

#rasterwaardes aanpassen aan de hand van de hiervoor berekende mean-waarde
dem_data = np.where(dem_data==-9999.0,np.nan,dem_data)
dem_data = dem_data - mean_val

#Nieuw raster aanmaken met de aangepaste waardes
with rasterio.open(
         output_folder + '/dtm_transformed.tif',
         'w',
         driver = 'GTiff',
         height = dem_data.shape[0],
         width = dem_data.shape[1],
         count = 1,
         dtype = dem_data.dtype,
         crs = 'epsg:28992',
         transform = dem.transform,
         force_cellsize = True,
         ) as dst:
         dst.write(dem_data, 1)
         
#Nieuwe kaart maken van het nieuwe raster
filename = output_folder + '/dtm_transformed.tif'
fig, ax = plt.subplots()
generate_map(ax, filename, points, points_csv, "terrain", "Hoogte (m NAP)", "", None, None, 0,0, None)   
plt.savefig(output_folder + "\\dtm_transformed_map.png")          
