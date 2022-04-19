import os
from flask import Flask, request
import re

app = Flask(__name__)

@app.route('/', methods = ['POST', 'GET'])
def test():
    if request.method == 'POST':
        print("post request received")
        postRequest = request.get_json()
        buildable_list = postRequest['buildable_list']
        buildable_list.sort()
        current_board_counter = 0
        while current_board_counter < len(buildable_list):
            current_board_name = re.split('//|/|:', buildable_list[current_board_counter])[-2]
            layout_link = "https://oem-outline.nyc3.digitaloceanspaces.com/kicad-artifacts/" + buildable_list[current_board_counter+2].replace(":", "/")[2:]
            schematic_link = "https://oem-outline.nyc3.digitaloceanspaces.com/kicad-artifacts/" + buildable_list[current_board_counter+1].replace(":", "/")[2:]
            bom_link = "https://oem-outline.nyc3.digitaloceanspaces.com/kicad-artifacts/" + buildable_list[current_board_counter].replace(":", "/")[2:]
            
            print(current_board_name, layout_link, schematic_link, bom_link)
            current_board_counter += 5

        #print(buildable_list)            
        return "BlahBlah"
    if request.method == 'GET':
        print("getting")
        return "Blah"
    
if __name__=="__main__":
    app.run(debug=True)
