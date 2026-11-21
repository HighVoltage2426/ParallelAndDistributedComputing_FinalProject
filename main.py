from supabase_client import supabase
from webapp import createApp

app = createApp()

if __name__ == "__main__":
    app.run(debug=True, threaded=True)