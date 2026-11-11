# Privacy

Use synthetic records on the public demo. For personal records, the local app processes inputs on the computer running Streamlit. A hosted app sends grades, uploads, and prediction inputs from the browser to the app server for processing.

| Data | How the app handles it |
| --- | --- |
| Workspace, grade scenarios, and GPA | Streamlit keeps records in the current session. A restart, refresh, or disconnect can clear them. |
| Uploaded JSON and CSV | The backend holds uploads in memory. Files are limited to 1 MB and are checked before workspace data changes. |
| Prediction inputs | The app computes results from the submitted profile. The shared model cache holds public data and model resources. |
| JSON, CSV, and Markdown downloads | The app creates downloads in memory and sends them to the browser. Downloaded reports can include marks or profile details. |

The application has no accounts, grade database, or analytics tracker. Streamlit usage statistics are disabled. The app is designed to avoid writing personal course records or prediction inputs to disk or logging their contents. Server operators and hosting providers may still have infrastructure access and their own logs, backups, or retention policies. There is no application-enforced deletion schedule.

A JSON import or demo load replaces the session workspace. CSV imports add courses or replace assessments for the named courses. Export your JSON before replacing records you want to keep. Keep downloaded records and their download links private.

The app keeps Streamlit's normal XSRF and CORS protections, hides raw exceptions in the browser, and validates uploads. Workspace files cannot load models or change model recipes. See [Streamlit's upload handling](https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted) and [shared cache documentation](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource).
