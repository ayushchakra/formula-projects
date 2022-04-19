from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def blah():
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("select * from kicad_artifacts")
    rows = cur.fetchall()
    artifacts = {}
    for row in rows:
        if row[0] not in artifacts.keys():
            artifacts[row[0]] = [{row[1]: [row[2], row[3], row[4]]}]
        else:
            artifacts[row[0]].insert(0, {row[1]: [row[2], row[3], row[4]]})
    return render_template('tableofcontents.html', artifacts=artifacts)

if __name__ == "__main__":
    app.run()