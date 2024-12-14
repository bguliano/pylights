import json
from dataclasses import asdict

from flask import request, jsonify, Response, Flask

from common import VIXEN_DIR
from pylightscontroller import PylightsController


# ---- Setup -------------------------------------------------------------------------------------

class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__dataclass_fields__'):
            return asdict(obj)
        return super().default(obj)


app = Flask(__name__)
app.json_encoder = DataclassJSONEncoder

controller = PylightsController(VIXEN_DIR)

# ------------------------------------------------------------------------------------------------


# ---- Endpoints ---------------------------------------------------------------------------------

BASE_ENDPOINT = '/pylights-api'


@app.route(f'{BASE_ENDPOINT}/songs/play')
def songs_play() -> tuple[Response, int]:
    name = request.args.get('name')

    if not name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.songs.play(name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/songs/pause')
def songs_pause() -> tuple[Response, int]:
    descriptor = controller.songs.pause()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/songs/resume')
def songs_resume() -> tuple[Response, int]:
    descriptor = controller.songs.resume()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/songs/stop')
def songs_stop() -> tuple[Response, int]:
    descriptor = controller.songs.stop()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/lights/all-on')
def lights_all_on() -> tuple[Response, int]:
    descriptor = controller.lights.all_on()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/lights/all-off')
def lights_all_off() -> tuple[Response, int]:
    descriptor = controller.lights.all_off()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/lights/turn-on')
def lights_turn_on() -> tuple[Response, int]:
    light_name = request.args.get('name')

    if not light_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.lights.turn_on(light_name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/lights/turn-off')
def lights_turn_off() -> tuple[Response, int]:
    light_name = request.args.get('name')

    if not light_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.lights.turn_off(light_name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/lights/toggle')
def lights_toggle() -> tuple[Response, int]:
    light_name = request.args.get('name')

    if not light_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.lights.toggle(light_name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/presets/activate')
def presets_activate() -> tuple[Response, int]:
    preset_name = request.args.get('name')

    if not preset_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.presets.activate(preset_name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/presets/add')
def presets_add() -> tuple[Response, int]:
    preset_name = request.args.get('name')
    light_names = request.args.get('lights', type=lambda x: x.split(','))

    if not preset_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400
    if not light_names:
        return jsonify({'error': 'The "lights" query parameter is required.'}), 400

    descriptor = controller.presets.add(preset_name, light_names)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/remap/start')
def remap_start() -> tuple[Response, int]:
    descriptor = controller.remap.start()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/remap/next')
def remap_next() -> tuple[Response, int]:
    light_name = request.args.get('name')

    if not light_name:
        return jsonify({'error': 'The "name" query parameter is required.'}), 400

    descriptor = controller.remap.next(light_name)
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/remap/cancel')
def remap_cancel() -> tuple[Response, int]:
    descriptor = controller.remap.cancel()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/developer/recompile-shows')
def developer_recompile_shows() -> tuple[Response, int]:
    descriptor = controller.developer.recompile_shows()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/developer/info')
def developer_info() -> tuple[Response, int]:
    descriptor = controller.developer.info()
    return jsonify(descriptor), 200


@app.route(f'{BASE_ENDPOINT}/info')
def info() -> tuple[Response, int]:
    return jsonify({
        'songs': controller.songs.get_info(),
        'lights': controller.lights.get_info(),
        'presets': controller.presets.get_info(),
    }), 200


# ------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run()
