import os
from gevent import monkey

monkey.patch_all()
import logging
from flask_socketio import SocketIO
from zou.app import app

FORMAT = "%(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
socketio = SocketIO(app, cors_allowed_origins=[], cors_credentials=False)

if __name__ == "__main__":
    port = int(os.getenv("DEBUG_PORT", 5000))
    print("The Kitsu API server is listening on port %s..." % port)
    socketio.run(app, port=port, debug=True)
