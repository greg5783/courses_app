from flask import Flask, request, render_template, jsonify, session, redirect, url_for, send_file
from functools import wraps
import os
import json
import time
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.environ.get('SWSA_SCORE_SECRET_KEY', 'swsa-score-dev-secret-change-in-prod')
SWSA_SCORE_PASSWORD = os.environ.get('SWSA_SCORE_PASSWORD', 'swsa-score@85142')

COURSES_DIR = os.environ.get(
    'COURSES_DIR',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'courses_data')
)
os.makedirs(COURSES_DIR, exist_ok=True)

WAYPOINTS_FILE   = os.path.join(COURSES_DIR, 'waypoints.json')
SERIES_FILE      = os.path.join(COURSES_DIR, 'series_types.json')
SERIES_DATA_FILE = os.path.join(COURSES_DIR, 'series.json')
COURSES_FILE     = os.path.join(COURSES_DIR, 'courses.json')
OBS_FILE         = os.path.join(COURSES_DIR, 'out_of_bounds.json')


def _load(path, default=None):
    if default is None:
        default = []
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default


def _save(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def new_id():
    return str(int(time.time() * 1000))


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('courses.html', logged_in=session.get('logged_in', False))


@app.route('/login', methods=['POST'])
def login():
    if request.form.get('password', '') == SWSA_SCORE_PASSWORD:
        session['logged_in'] = True
    return redirect(url_for('index'))


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))


# ── Data API ──────────────────────────────────────────────────────────────────

@app.route('/api/data')
def api_data():
    return jsonify({
        'waypoints':      _load(WAYPOINTS_FILE),
        'series_types':   _load(SERIES_FILE),
        'series':         _load(SERIES_DATA_FILE),
        'courses':        _load(COURSES_FILE),
        'out_of_bounds':  _load(OBS_FILE),
    })


@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'service': 'courses-app'}), 200


# ── Waypoints ─────────────────────────────────────────────────────────────────

@app.route('/api/waypoints', methods=['POST'])
@login_required
def create_waypoint():
    d = request.get_json() or {}
    waypoints = _load(WAYPOINTS_FILE)
    wp = {
        'id':    new_id(),
        'code':  d.get('code', '').strip(),
        'name':  d.get('name', '').strip(),
        'color': d.get('color', '').strip(),
        'lat':   float(d['lat']),
        'lon':   float(d['lon']),
    }
    waypoints.append(wp)
    _save(WAYPOINTS_FILE, waypoints)
    return jsonify(wp), 201


@app.route('/api/waypoints/<wid>', methods=['PUT'])
@login_required
def update_waypoint(wid):
    d = request.get_json() or {}
    waypoints = _load(WAYPOINTS_FILE)
    for wp in waypoints:
        if wp['id'] == wid:
            wp['code']  = d.get('code',  wp.get('code', '')).strip()
            wp['name']  = d.get('name',  wp['name']).strip()
            wp['color'] = d.get('color', wp.get('color', '')).strip()
            wp['lat']   = float(d.get('lat', wp['lat']))
            wp['lon']   = float(d.get('lon', wp['lon']))
            _save(WAYPOINTS_FILE, waypoints)
            return jsonify(wp)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/waypoints/<wid>', methods=['DELETE'])
@login_required
def delete_waypoint(wid):
    waypoints = _load(WAYPOINTS_FILE)
    _save(WAYPOINTS_FILE, [w for w in waypoints if w['id'] != wid])
    return jsonify({'ok': True})


# ── Series types ──────────────────────────────────────────────────────────────

@app.route('/api/series_types', methods=['POST'])
@login_required
def create_series_type():
    d = request.get_json() or {}
    series = _load(SERIES_FILE)
    st = {'id': new_id(), 'name': d.get('name', '').strip()}
    series.append(st)
    _save(SERIES_FILE, series)
    return jsonify(st), 201


@app.route('/api/series_types/<stid>', methods=['PUT'])
@login_required
def update_series_type(stid):
    d = request.get_json() or {}
    series = _load(SERIES_FILE)
    for st in series:
        if st['id'] == stid:
            st['name'] = d.get('name', st['name']).strip()
            _save(SERIES_FILE, series)
            return jsonify(st)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/series_types/<stid>', methods=['DELETE'])
@login_required
def delete_series_type(stid):
    series = _load(SERIES_FILE)
    _save(SERIES_FILE, [s for s in series if s['id'] != stid])
    courses = _load(COURSES_FILE)
    _save(COURSES_FILE, [c for c in courses if c.get('series_type_id') != stid])
    return jsonify({'ok': True})


# ── Series ────────────────────────────────────────────────────────────────────

@app.route('/api/series', methods=['POST'])
@login_required
def create_series():
    d = request.get_json() or {}
    series_list = _load(SERIES_DATA_FILE)
    series = {
        'id':          new_id(),
        'name':        d.get('name', '').strip(),
        'description': d.get('description', '').strip(),
        'course_ids':  d.get('course_ids', []),
    }
    series_list.append(series)
    _save(SERIES_DATA_FILE, series_list)
    return jsonify(series), 201


@app.route('/api/series/<sid>', methods=['PUT'])
@login_required
def update_series(sid):
    d = request.get_json() or {}
    series_list = _load(SERIES_DATA_FILE)
    for series in series_list:
        if series['id'] == sid:
            series['name']        = d.get('name', series['name']).strip()
            series['description'] = d.get('description', series.get('description', '')).strip()
            series['course_ids']  = d.get('course_ids', series.get('course_ids', []))
            _save(SERIES_DATA_FILE, series_list)
            return jsonify(series)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/series/<sid>', methods=['DELETE'])
@login_required
def delete_series(sid):
    series_list = _load(SERIES_DATA_FILE)
    _save(SERIES_DATA_FILE, [s for s in series_list if s['id'] != sid])
    return jsonify({'ok': True})


# ── Courses ───────────────────────────────────────────────────────────────────

@app.route('/api/courses', methods=['POST'])
@login_required
def create_course():
    d = request.get_json() or {}
    courses = _load(COURSES_FILE)
    course = {
        'id':             new_id(),
        'name':           d.get('name', '').strip(),
        'series_type_id': d.get('series_type_id', ''),
        'marks':          d.get('marks', []),
        'committee_boat': d.get('committee_boat', None),
        'wind_bearing_min': d.get('wind_bearing_min', None),
        'wind_bearing_max': d.get('wind_bearing_max', None),
        'boat_speed':  d.get('boat_speed', 5),
        'beat_factor': d.get('beat_factor', 0.7),
    }
    courses.append(course)
    _save(COURSES_FILE, courses)
    return jsonify(course), 201


@app.route('/api/courses/<cid>', methods=['PUT'])
@login_required
def update_course(cid):
    d = request.get_json() or {}
    courses = _load(COURSES_FILE)
    for course in courses:
        if course['id'] == cid:
            course['name']           = d.get('name',           course['name']).strip()
            course['series_type_id'] = d.get('series_type_id', course['series_type_id'])
            course['marks']          = d.get('marks',          course['marks'])
            course['committee_boat'] = d.get('committee_boat', course.get('committee_boat'))
            course['wind_bearing_min'] = d.get('wind_bearing_min', course.get('wind_bearing_min'))
            course['wind_bearing_max'] = d.get('wind_bearing_max', course.get('wind_bearing_max'))
            course['boat_speed']  = d.get('boat_speed',  course.get('boat_speed',  5))
            course['beat_factor'] = d.get('beat_factor', course.get('beat_factor', 0.7))
            _save(COURSES_FILE, courses)
            return jsonify(course)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/courses/<cid>', methods=['DELETE'])
@login_required
def delete_course(cid):
    courses = _load(COURSES_FILE)
    _save(COURSES_FILE, [c for c in courses if c['id'] != cid])
    return jsonify({'ok': True})


# ── Out-of-bounds polygons ────────────────────────────────────────────────────

@app.route('/api/out_of_bounds', methods=['POST'])
@login_required
def create_obs():
    d = request.get_json() or {}
    obs = _load(OBS_FILE)
    item = {
        'id':     new_id(),
        'name':   d.get('name', 'Restricted area').strip(),
        'coords': d.get('coords', []),  # [[lat, lon], ...]
    }
    obs.append(item)
    _save(OBS_FILE, obs)
    return jsonify(item), 201


@app.route('/api/out_of_bounds/<oid>', methods=['PUT'])
@login_required
def update_obs(oid):
    d = request.get_json() or {}
    obs = _load(OBS_FILE)
    for item in obs:
        if item['id'] == oid:
            item['name']   = d.get('name',   item['name']).strip()
            item['coords'] = d.get('coords', item['coords'])
            _save(OBS_FILE, obs)
            return jsonify(item)
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/out_of_bounds/<oid>', methods=['DELETE'])
@login_required
def delete_obs(oid):
    obs = _load(OBS_FILE)
    _save(OBS_FILE, [o for o in obs if o['id'] != oid])
    return jsonify({'ok': True})


# ── Import/Export ─────────────────────────────────────────────────────────────

@app.route('/api/export/waypoints')
@login_required
def export_waypoints():
    include_obs = request.args.get('include_obs', '').lower() in ('1', 'true', 'yes')
    package = {
        'format_version': '1.0',
        'exported_at': time.time(),
        'waypoints': _load(WAYPOINTS_FILE),
    }
    if include_obs:
        package['out_of_bounds'] = _load(OBS_FILE)
    file_data = BytesIO(json.dumps(package, indent=2).encode('utf-8'))
    return send_file(file_data, mimetype='application/json', as_attachment=True,
                     download_name=f'waypoints_{int(time.time())}.json')


@app.route('/api/import/waypoints', methods=['POST'])
@login_required
def import_waypoints():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be JSON'}), 400
    try:
        package = json.load(file)
        if 'waypoints' not in package:
            return jsonify({'error': 'Invalid file: missing waypoints'}), 400
        existing_wp = _load(WAYPOINTS_FILE)
        existing_ids = {w['id'] for w in existing_wp}
        new_wp = [w for w in package['waypoints'] if w['id'] not in existing_ids]
        _save(WAYPOINTS_FILE, existing_wp + new_wp)
        imported_obs = 0
        if 'out_of_bounds' in package:
            existing_obs = _load(OBS_FILE)
            existing_obs_ids = {o['id'] for o in existing_obs}
            new_obs = [o for o in package['out_of_bounds'] if o['id'] not in existing_obs_ids]
            _save(OBS_FILE, existing_obs + new_obs)
            imported_obs = len(new_obs)
        return jsonify({
            'ok': True,
            'imported_waypoints': len(new_wp),
            'total_waypoints': len(existing_wp) + len(new_wp),
            'imported_obs': imported_obs,
        }), 201
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/series')
@login_required
def export_series():
    package = {
        'format_version': '1.0',
        'exported_at': time.time(),
        'series_types': _load(SERIES_FILE),
        'series': _load(SERIES_DATA_FILE),
        'courses': _load(COURSES_FILE),
    }
    file_data = BytesIO(json.dumps(package, indent=2).encode('utf-8'))
    return send_file(file_data, mimetype='application/json', as_attachment=True,
                     download_name=f'series_{int(time.time())}.json')


@app.route('/api/import/series', methods=['POST'])
@login_required
def import_series():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if not file.filename.endswith('.json'):
        return jsonify({'error': 'File must be JSON'}), 400
    try:
        package = json.load(file)
        result = {}
        if 'series_types' in package:
            existing = _load(SERIES_FILE)
            existing_ids = {s['id'] for s in existing}
            new_items = [s for s in package['series_types'] if s['id'] not in existing_ids]
            _save(SERIES_FILE, existing + new_items)
            result['imported_series_types'] = len(new_items)
        if 'series' in package:
            existing = _load(SERIES_DATA_FILE)
            existing_ids = {s['id'] for s in existing}
            new_items = [s for s in package['series'] if s['id'] not in existing_ids]
            _save(SERIES_DATA_FILE, existing + new_items)
            result['imported_series'] = len(new_items)
        if 'courses' in package:
            existing = _load(COURSES_FILE)
            existing_ids = {c['id'] for c in existing}
            new_items = [c for c in package['courses'] if c['id'] not in existing_ids]
            _save(COURSES_FILE, existing + new_items)
            result['imported_courses'] = len(new_items)
        if not result:
            return jsonify({'error': 'Invalid file: no recognized data found'}), 400
        result['ok'] = True
        return jsonify(result), 201
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('COURSES_PORT', 8081))
    app.run(debug=True, port=port)
