# Privacy: local and hosted use

Student Success AI is a demonstration application, not a confidential student-record service. Use the **Load Demo Workspace** action and synthetic inputs when visiting a public deployment.

## Data flow

| Data | Local application | Remotely hosted application |
| --- | --- | --- |
| Course marks, targets and grading boundaries | Processed by the local Python process | Sent from the browser to the app server and processed in that server process |
| Uploaded workspace JSON | Copied into the local Streamlit backend memory | Transmitted to the hosted backend and held in upload/session memory |
| Prediction inputs and outputs | Processed on the local machine | Sent to and computed on the app server |
| Downloadable JSON/CSV/Markdown | Created in server memory, then saved by the browser on request | Created in hosted server memory and transferred back to the browser on request |
| Training dataset/models | Public licensed UCI resources, shared within the process | The same public resources may be shared across sessions; they contain no visitor input |

A hosted app's data do **not** remain solely on the visitor's device. TLS and provider handling depend on the deployment environment. The operator and hosting provider may have infrastructure access, operational logs, backups or retention policies outside this application's control. The application does not promise immediate deletion, end-to-end confidentiality or confidential download URLs.

## Application behavior

- Workspaces are kept in Streamlit session state. One session's edits and demo loading are not intentionally shared with another session.
- The application does not intentionally write personal course records or prediction inputs to server disk or log their contents. It introduces no accounts, cloud database, analytics tracker or third-party collection service. Streamlit usage statistics are disabled.
- Shared initialization caches contain **public training/model resources only**. User inputs/results are not added to them. Prepared resources returned to callers are isolated from the shared originals.
- Uploads accept JSON workspaces only. A 1 MB size limit and structural/range validation apply before replacement of the current workspace. Old version 1 saves are migrated to version 2; malformed input does not partially replace a valid workspace. Model artifacts cannot be uploaded or loaded.
- Imports and **Load Demo Workspace** replace the current session's workspace. Export first if the existing records should be retained.
- Downloads can include educational records and submitted profiles. Store them privately and do not share a generated download link as though it were a protected account-based document.
- Session state is temporary, not a durable save. Browser refreshes, disconnects, server restarts or provider lifecycle changes can remove it. Export a workspace and restore it on a later visit. Runtime buffers may remain until Streamlit/provider lifecycle cleanup; there is no application-enforced erasure deadline.

## Operational safeguards and limits

Client exception details are hidden, public errors avoid host paths/upload contents, and Streamlit's normal XSRF/CORS protections remain enabled. Upload names, oversized/deeply nested JSON and invalid values are treated as untrusted input. These measures do not make an anonymous demo a suitable place for sensitive student records.

The app may show links to UCI, GitHub and documentation. Following those links leaves the application and is subject to those sites' policies. No externally hosted tracking pixels, fonts or analytics components are introduced by this release.

Official Streamlit documentation explains [upload memory handling](https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted), [upload limits](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader), and [shared resource caching](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource). These explain framework behavior; provider policies still need review before publishing a hosted URL.
