import wget
import os

image_url = 'https://oem-outline.nyc3.digitaloceanspaces.com/kicad-artifacts/vehicle/mkv/hardware/lvbox/bspd/bspd_brakelight.csv'
image_filename = wget.download(image_url, 'artifacts_site/')

#os.mkdir('bspd')
#os.mkdir('bspd/commit2/')
wget.download(image_url, 'bspd/commit1/bla.csv')

print(os.path.isdir('bspd'))