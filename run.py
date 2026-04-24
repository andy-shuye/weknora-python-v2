import os

from dotenv import load_dotenv

from app import create_app


load_dotenv()

config_name = os.getenv('FLASK_ENV', 'default')
app = create_app(config_name)


if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_RUN_PORT', '5000'))
    app.run(host=host, port=port)