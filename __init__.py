import os
from flask import Flask, render_template, request
from jinja2 import Template

app = Flask(__name__)

data = {
    "breakpad": {
        "commit1": ("schematic1", "layout1", "bom1"), 
        "commit2": ("schematic2", "layout2", "bom2")
    },
    "hitl" : {
        "commit1": ("schematic1", "layout1", "bom1"), 
        "commit2": ("schematic2", "layout2", "bom2"), 
        "commit3": ("schematic3", "layout3", "bom3")
    }
}

@app.route('/')
def TableOfContents():
    return render_template('tableofcontents.html', data=data)
@app.route('/<board_name>/')
def board_name(board_name):
    commits = []
    for key in data[board_name]:
        commits.append(key)
    return render_template('board.html', board_name=board_name, commits=commits)
@app.route('/<board_name>/<commit>', methods = ['POST', 'GET'])
def board_name_commit(board_name,commit):
    if request.method == 'POST':
        postRequest = request.get_json()
        if board_name in data.keys():
            data[board_name].update({commit : (postRequest['schematic'], postRequest['layout'], postRequest['bom'])})
        else:
            data.update({board_name: {commit : (postRequest['schematic'], postRequest['layout'], postRequest['bom'])}})
        return render_template('tableofcontents.html', data=data)
    if request.method == 'GET':
        schematic = data[board_name][commit][0]
        layout = data[board_name][commit][1]
        bom = data[board_name][commit][2]
        return render_template('board_commit.html', board_name=board_name, commit=commit, schematic = schematic, layout = layout, bom = bom)

if __name__ == "__main__":
    app.run(debug=True)