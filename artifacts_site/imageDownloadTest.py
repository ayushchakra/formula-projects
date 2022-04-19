import requests
import shutil

image_url = "https://oem-outline.nyc3.digitaloceanspaces.com/kicad-artifacts/vehicle/mkv/hardware/lvbox/bspd/bspd_brakelight_a_top_pcb.svg"
filename = image_url.split('/')[-1]

r = requests.get(image_url, stream = True)

if r.status_code == 200:
    r.raw.decode_content = True

    with open(f"artifacts_site/{filename}", 'wb') as f:
        shutil.copyfileobj(r.raw, f)